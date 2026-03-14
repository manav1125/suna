from typing import Any, Dict, Optional, Literal, List
import json

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field

from core.endpoints.vapi_webhooks import VapiWebhookHandler
from core.services.http_client import get_http_client
from core.utils.auth_utils import AuthorizedThreadAccess, require_thread_write_access
from core.utils.config import config
from core.utils.logger import logger

router = APIRouter(tags=["vapi"])

webhook_handler = VapiWebhookHandler()


class VapiWebSessionRequest(BaseModel):
    agent_id: Optional[str] = None


class VapiWebTranscriptRequest(BaseModel):
    role: Literal["user", "assistant"]
    transcript: str = Field(min_length=1, max_length=20000)
    call_id: Optional[str] = None
    dedupe_key: Optional[str] = None
    timestamp: Optional[float] = None
    agent_id: Optional[str] = None


class VapiWebTranscriptTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=20000)
    timestamp: Optional[float] = None


class VapiWebHandoffRequest(BaseModel):
    turns: List[VapiWebTranscriptTurn] = Field(default_factory=list)
    call_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None


def _message_text(content: Any) -> str:
    if isinstance(content, dict):
        return str(content.get("content") or content.get("text") or "").strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                item_text = item.get("text") or item.get("content") or ""
                if item_text:
                    parts.append(str(item_text).strip())
            elif item:
                parts.append(str(item).strip())
        return " ".join(part for part in parts if part)
    return str(content or "").strip()


def _normalize_transcript_turns(turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized_turns: List[Dict[str, Any]] = []
    seen = set()

    for turn in turns:
        role = str(turn.get("role") or "").lower().strip()
        if role in ("bot", "agent", "model", "system"):
            role = "assistant"
        if role not in ("user", "assistant"):
            continue

        text = (
            str(turn.get("text") or turn.get("message") or turn.get("content") or turn.get("transcript") or "")
            .strip()
        )
        if not text:
            continue

        timestamp = turn.get("timestamp")
        dedupe_key = f"{role}::{timestamp or ''}::{text}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        normalized_turns.append(
            {
                "role": role,
                "text": text,
                "timestamp": timestamp,
            }
        )

    return normalized_turns


def _format_transcript_for_prompt(turns: List[Dict[str, Any]], agent_name: str) -> str:
    lines = []
    for turn in turns:
        speaker = "User" if turn["role"] == "user" else agent_name
        lines.append(f"{speaker}: {turn['text']}")
    return "\n".join(lines)


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("\n", 1)[0]
    return cleaned.strip()


def _normalize_bullet_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


async def _fetch_vapi_call_transcript(call_id: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    if not call_id or not config.VAPI_PRIVATE_KEY:
        return None

    try:
        async with get_http_client() as http_client:
            response = await http_client.get(
                f"https://api.vapi.ai/call/{call_id}",
                headers={"Authorization": f"Bearer {config.VAPI_PRIVATE_KEY}"},
                timeout=20.0,
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning(f"Failed to fetch final Vapi call transcript for {call_id}: {exc}")
        return None

    transcript = payload.get("transcript")
    if isinstance(transcript, list):
        normalized = _normalize_transcript_turns(transcript)
        return normalized or None

    return None


async def _generate_voice_handoff_sections(
    turns: List[Dict[str, Any]],
    agent_name: str,
) -> Dict[str, List[str]]:
    if not turns:
        return {
            "summary": [],
            "decisions": [],
            "action_items": [],
            "open_questions": [],
            "follow_ups": [],
        }

    transcript_text = _format_transcript_for_prompt(turns, agent_name)

    if not config.OPENAI_API_KEY:
        return {
            "summary": ["Voice conversation completed. Review the transcript below and continue in chat for execution-oriented work."],
            "decisions": [],
            "action_items": [],
            "open_questions": [],
            "follow_ups": [],
        }

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You turn completed live voice conversations into a high-signal post-call handoff for a text thread. "
                        "Return strict JSON only with keys: summary, decisions, action_items, open_questions, follow_ups. "
                        "Each value must be an array of concise bullet strings. "
                        "Use empty arrays when not applicable. "
                        "Capture the user's requested follow-up work in follow_ups."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Assistant name: {agent_name}\n"
                        "Create a post-call handoff from this transcript.\n\n"
                        f"{transcript_text[:30000]}"
                    ),
                },
            ],
        )
        raw_content = response.choices[0].message.content or "{}"
        parsed = json.loads(_strip_code_fences(raw_content))
        return {
            "summary": _normalize_bullet_list(parsed.get("summary")),
            "decisions": _normalize_bullet_list(parsed.get("decisions")),
            "action_items": _normalize_bullet_list(parsed.get("action_items")),
            "open_questions": _normalize_bullet_list(parsed.get("open_questions")),
            "follow_ups": _normalize_bullet_list(parsed.get("follow_ups")),
        }
    except Exception as exc:
        logger.warning(f"Failed to generate structured voice handoff summary: {exc}")
        return {
            "summary": ["Voice conversation completed. Review the transcript below and continue in chat for execution-oriented work."],
            "decisions": [],
            "action_items": [],
            "open_questions": [],
            "follow_ups": [],
        }


def _build_voice_handoff_markdown(
    turns: List[Dict[str, Any]],
    sections: Dict[str, List[str]],
    agent_name: str,
) -> str:
    lines = [
        f"## Live Voice Handoff with {agent_name}",
        "",
        "This call has been converted into a text handoff so you can keep going in chat.",
        "",
    ]

    section_map = [
        ("Summary", sections.get("summary", [])),
        ("Key Decisions", sections.get("decisions", [])),
        ("Action Items", sections.get("action_items", [])),
        ("Open Questions", sections.get("open_questions", [])),
        ("Suggested Follow-ups", sections.get("follow_ups", [])),
    ]

    for title, bullets in section_map:
        if not bullets:
            continue
        lines.append(f"### {title}")
        lines.extend([f"- {bullet}" for bullet in bullets])
        lines.append("")

    lines.append("### Full Transcript")
    for turn in turns:
        speaker = "User" if turn["role"] == "user" else agent_name
        lines.append(f"**{speaker}:** {turn['text']}")
        lines.append("")

    return "\n".join(lines).strip()


async def _format_recent_thread_context(thread_id: str, limit: int = 20) -> Optional[str]:
    from core.threads import repo as threads_repo

    try:
        raw_messages = await threads_repo.get_thread_messages(thread_id, order="asc")
    except Exception as exc:
        logger.warning(f"Failed to load recent thread context for Vapi session: {exc}")
        return None

    if not raw_messages:
        return None

    conversation_lines = []
    for message in raw_messages[-limit:]:
        role = "Assistant" if message.get("type") == "assistant" else "User"
        text = _message_text(message.get("content"))
        if not text:
            continue
        conversation_lines.append(f"{role}: {text[:800]}")

    if not conversation_lines:
        return None

    return "\n".join(conversation_lines)


async def _fetch_voice_memory_context(user_id: str, thread_id: str) -> Optional[str]:
    if not config.ENABLE_MEMORY:
        return None

    try:
        from core.billing import subscription_service
        from core.memory.retrieval_service import memory_retrieval_service
        from core.threads import repo as threads_repo

        user_memory_enabled = await threads_repo.get_user_memory_enabled(user_id)
        if not user_memory_enabled:
            return None

        thread_memory_enabled = await threads_repo.get_thread_memory_enabled(thread_id)
        if not thread_memory_enabled:
            return None

        recent_messages = await threads_repo.get_thread_messages(thread_id, order="asc")
        recent_user_text = [
            _message_text(message.get("content"))
            for message in recent_messages[-6:]
            if message.get("type") == "user"
        ]
        query_text = "\n".join(part for part in recent_user_text if part).strip()
        if len(query_text) < 10:
            return None

        tier_info = await subscription_service.get_user_subscription_tier(user_id)
        memories = await memory_retrieval_service.retrieve_memories(
            account_id=user_id,
            query_text=query_text,
            tier_name=tier_info["name"],
        )

        if not memories:
            return None

        return memory_retrieval_service.format_memories_for_prompt(memories)
    except Exception as exc:
        logger.warning(f"Failed to fetch memory context for Vapi session: {exc}")
        return None


async def _build_voice_system_prompt(thread_id: str, user_id: str, agent_id: Optional[str]) -> Dict[str, Optional[str]]:
    from core.agents.agent_loader import AgentLoader

    agent_name = "Mira"
    base_prompt = (
        "You are Mira, an AI coach, guide, and operator for founders and investors. "
        "Be thoughtful, strategic, and collaborative. In live voice mode, sound natural and conversational. "
        "Give direct answers, ask clarifying questions when needed, and keep most spoken turns to one to three sentences. "
        "You are continuing the same thread the user is currently looking at, so use the existing thread context and memory below instead of acting like this is a brand-new conversation."
    )

    if agent_id:
        try:
            agent_data = await AgentLoader().load_agent(agent_id, user_id, load_config=True)
            agent_name = agent_data.name or agent_name
            if agent_data.system_prompt:
                base_prompt = agent_data.system_prompt.strip()
        except Exception as exc:
            logger.warning(f"Failed to load agent {agent_id} for Vapi session: {exc}")

    recent_context = await _format_recent_thread_context(thread_id)
    memory_context = await _fetch_voice_memory_context(user_id, thread_id)

    prompt_parts = [
        base_prompt,
        "",
        "LIVE VOICE MODE BEHAVIOR:",
        "- Speak like a supportive, highly capable teammate, not a chatbot reading a memo.",
        "- Treat the thread context and relevant memory below as active context for this live conversation.",
        "- Keep answers crisp unless the user explicitly asks you to go deeper.",
        "- If you do not know something yet, say so and suggest the next best step.",
        "- Do not claim that you searched, opened files, or completed actions unless that actually happened.",
        "- Do not promise background work, research runs, or thread actions after the call unless the product actually triggered them.",
        "- If the user wants a detailed report, strategy memo, deck, or proposal, explain that live voice is best for discussion and they should send or confirm the request in chat after the call for full execution.",
    ]

    if memory_context:
        prompt_parts.extend(["", "RELEVANT USER MEMORY:", memory_context])

    if recent_context:
        prompt_parts.extend(["", "RECENT THREAD CONTEXT:", recent_context])

    return {
        "agent_name": agent_name,
        "prompt": "\n".join(part for part in prompt_parts if part is not None).strip(),
    }


def _build_transient_assistant(prompt: str, agent_name: str) -> Dict[str, Any]:
    return {
        "firstMessageMode": "assistant-waits-for-user",
        "maxDurationSeconds": 1800,
        "backgroundSound": "off",
        "modelOutputInMessagesEnabled": True,
        "model": {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "messages": [
                {
                    "role": "system",
                    "content": prompt,
                }
            ],
        },
        "voice": {
            "provider": "vapi",
            "voiceId": "Hana",
        },
        "metadata": {
            "agentName": agent_name,
            "experience": "mira-live-voice",
        },
    }


@router.post("/webhooks/vapi", summary="Vapi Webhook Handler", operation_id="vapi_webhook")
async def handle_vapi_webhook(request: Request):
    try:
        if config.VAPI_WEBHOOK_SECRET:
            signature_valid = await webhook_handler.verify_signature(request, config.VAPI_WEBHOOK_SECRET)
            if not signature_valid:
                raise HTTPException(status_code=401, detail="Invalid Vapi webhook signature")

        payload = await request.json()

        event_type = (
            payload.get("message", {}).get("type") if "message" in payload
            else payload.get("type") or payload.get("event")
        )

        if not event_type:
            return {"status": "ok", "message": "Webhook received but event type not recognized"}

        return await webhook_handler.handle_webhook(event_type, payload)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error processing Vapi webhook: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/vapi/web/session/{thread_id}", summary="Create Vapi Web Session", operation_id="create_vapi_web_session")
async def create_vapi_web_session(
    thread_id: str,
    payload: VapiWebSessionRequest,
    auth: AuthorizedThreadAccess = Depends(require_thread_write_access),
):
    try:
        if not config.VAPI_PUBLIC_KEY:
            raise HTTPException(
                status_code=503,
                detail="Live voice is not configured yet. Missing VAPI_PUBLIC_KEY.",
            )

        prompt_data = await _build_voice_system_prompt(thread_id, auth.user_id, payload.agent_id)
        assistant = _build_transient_assistant(prompt_data["prompt"], prompt_data["agent_name"] or "Mira")

        return {
            "public_key": config.VAPI_PUBLIC_KEY,
            "assistant": assistant,
            "thread_id": thread_id,
            "agent_id": payload.agent_id,
            "agent_name": prompt_data["agent_name"] or "Mira",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to create Vapi web session for thread {thread_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to start live voice session")


@router.post("/vapi/web/transcript/{thread_id}", summary="Persist Vapi Web Transcript Turn", operation_id="persist_vapi_web_transcript")
async def persist_vapi_web_transcript(
    thread_id: str,
    payload: VapiWebTranscriptRequest,
    auth: AuthorizedThreadAccess = Depends(require_thread_write_access),
):
    from core.memory.background_jobs import queue_memory_extraction
    from core.services.db import execute_one
    from core.threads import repo as threads_repo

    transcript = payload.transcript.strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript content cannot be empty")

    dedupe_key = payload.dedupe_key or f"{payload.call_id or 'voice'}:{payload.role}:{payload.timestamp or ''}:{transcript[:200]}"

    existing = await execute_one(
        """
        SELECT message_id
        FROM messages
        WHERE thread_id = :thread_id
          AND metadata->>'voice_source' = 'vapi_web'
          AND metadata->>'voice_dedupe_key' = :dedupe_key
        LIMIT 1
        """,
        {
            "thread_id": thread_id,
            "dedupe_key": dedupe_key,
        },
    )

    if existing:
        return {
            "status": "duplicate",
            "message_id": str(existing["message_id"]),
        }

    message = await threads_repo.insert_message(
        thread_id=thread_id,
        message_type=payload.role,
        content={
            "role": payload.role,
            "content": transcript,
        },
        is_llm_message=payload.role == "assistant",
        metadata={
            "voice_source": "vapi_web",
            "voice_call_id": payload.call_id,
            "voice_dedupe_key": dedupe_key,
            "voice_timestamp": payload.timestamp,
        },
        agent_id=payload.agent_id if payload.role == "assistant" else None,
    )

    queue_memory_extraction(thread_id, auth.user_id, [message.get("message_id")])

    return {
        "status": "persisted",
        "message": message,
    }


@router.post("/vapi/web/handoff/{thread_id}", summary="Persist Vapi Web Post-Call Handoff", operation_id="persist_vapi_web_handoff")
async def persist_vapi_web_handoff(
    thread_id: str,
    payload: VapiWebHandoffRequest,
    auth: AuthorizedThreadAccess = Depends(require_thread_write_access),
):
    from core.memory.background_jobs import queue_memory_extraction
    from core.services.db import execute_one
    from core.threads import repo as threads_repo

    normalized_local_turns = _normalize_transcript_turns([turn.model_dump() for turn in payload.turns])
    final_vapi_turns = await _fetch_vapi_call_transcript(payload.call_id)

    turns = final_vapi_turns if final_vapi_turns and len(final_vapi_turns) >= len(normalized_local_turns) else normalized_local_turns
    if not turns:
        raise HTTPException(status_code=400, detail="No transcript turns available for post-call handoff")

    existing = await execute_one(
        """
        SELECT message_id
        FROM messages
        WHERE thread_id = :thread_id
          AND metadata->>'voice_source' = 'vapi_web_handoff'
          AND metadata->>'voice_call_id' = :call_id
        LIMIT 1
        """,
        {
            "thread_id": thread_id,
            "call_id": payload.call_id or "",
        },
    )

    if existing:
        return {
            "status": "duplicate",
            "message_id": str(existing["message_id"]),
        }

    agent_name = payload.agent_name or "Mira"
    sections = await _generate_voice_handoff_sections(turns, agent_name)
    handoff_markdown = _build_voice_handoff_markdown(turns, sections, agent_name)

    message = await threads_repo.insert_message(
        thread_id=thread_id,
        message_type="assistant",
        content={
            "role": "assistant",
            "content": handoff_markdown,
        },
        is_llm_message=True,
        metadata={
            "voice_source": "vapi_web_handoff",
            "voice_call_id": payload.call_id,
            "voice_turn_count": len(turns),
            "voice_transcript": turns,
            "voice_handoff_sections": sections,
        },
        agent_id=payload.agent_id,
    )

    queue_memory_extraction(thread_id, auth.user_id, [message.get("message_id")])

    return {
        "status": "persisted",
        "message": message,
    }


@router.get("/vapi/calls/{call_id}", summary="Get Call Details", operation_id="get_vapi_call")
async def get_call_details(call_id: str):
    try:
        from core.services.supabase import DBConnection

        db = DBConnection()
        client = await db.client

        result = await client.table("vapi_calls").select("*").eq("call_id", call_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Call not found")

        return result.data

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error retrieving call details: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/vapi/calls", summary="List Calls", operation_id="list_vapi_calls")
async def list_calls(limit: int = 10, thread_id: str = None):
    try:
        from core.services.supabase import DBConnection

        db = DBConnection()
        client = await db.client

        query = client.table("vapi_calls").select("*").order("created_at", desc=True).limit(limit)

        if thread_id:
            query = query.eq("thread_id", thread_id)

        result = await query.execute()

        return {
            "calls": result.data,
            "count": len(result.data),
        }

    except Exception as exc:
        logger.error(f"Error listing calls: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
