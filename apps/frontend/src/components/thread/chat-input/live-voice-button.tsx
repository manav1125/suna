'use client';

import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import {
  AudioLines,
  Loader2,
  MicOff,
  PhoneOff,
  PhoneOutgoing,
  Radio,
  Sparkles,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { backendApi } from '@/lib/api-client';
import { createThread } from '@/lib/api/threads';
import { threadKeys } from '@/hooks/threads/keys';
import { toast } from '@/lib/toast';

type ConnectionState = 'idle' | 'connecting' | 'connected' | 'ending' | 'error';

interface TranscriptPreview {
  role: 'user' | 'assistant';
  text: string;
}

interface PersistableTranscriptTurn {
  role: 'user' | 'assistant';
  text: string;
  timestamp?: number | null;
}

interface VapiSessionResponse {
  public_key: string;
  assistant: Record<string, unknown>;
  thread_id: string;
  agent_id?: string | null;
  agent_name?: string | null;
}

interface VapiHandoffResponse {
  status: string;
  message?: {
    message_id?: string;
  };
  message_id?: string;
}

interface LiveVoiceButtonProps {
  threadId?: string | null;
  projectId?: string;
  selectedAgentId?: string;
  disabled?: boolean;
  variant?: 'icon' | 'pill';
}

function normalizeWhitespace(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function canonicalizeText(text: string): string {
  return normalizeWhitespace(text)
    .toLowerCase()
    .replace(/[.,!?;:()[\]{}"']/g, '')
    .trim();
}

function looksLikeExpansion(previous: string, next: string): boolean {
  if (!previous || !next) return false;
  const a = canonicalizeText(previous);
  const b = canonicalizeText(next);
  if (!a || !b) return false;
  return a === b || b.startsWith(a) || a.startsWith(b);
}

function richerText(a: string, b: string): string {
  const left = normalizeWhitespace(a);
  const right = normalizeWhitespace(b);
  return right.length >= left.length ? right : left;
}

function formatVoiceError(value: unknown, fallback: string): string {
  if (!value) return fallback;

  if (typeof value === 'string') {
    const text = normalizeWhitespace(value);
    return text || fallback;
  }

  if (value instanceof Error) {
    return normalizeWhitespace(value.message) || fallback;
  }

  if (Array.isArray(value)) {
    const merged = value
      .map((item) => formatVoiceError(item, ''))
      .filter(Boolean)
      .join(' ');
    return normalizeWhitespace(merged) || fallback;
  }

  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const nestedCandidates = [
      record.message,
      record.detail,
      record.error,
      record.errorMsg,
      record.reason,
      record.context,
      record.data,
    ];

    for (const candidate of nestedCandidates) {
      const formatted = formatVoiceError(candidate, '');
      if (formatted) return formatted;
    }

    try {
      const serialized = JSON.stringify(value);
      return serialized === '{}' ? fallback : serialized;
    } catch {
      return fallback;
    }
  }

  return normalizeWhitespace(String(value)) || fallback;
}

function buildTranscriptPreview(turns: PersistableTranscriptTurn[]): TranscriptPreview[] {
  const preview: TranscriptPreview[] = [];
  const seenKeys = new Set<string>();

  for (let index = turns.length - 1; index >= 0; index -= 1) {
    const turn = turns[index];
    const canonical = canonicalizeText(turn.text);
    if (!canonical) continue;

    const key = `${turn.role}:${canonical}`;
    if (seenKeys.has(key)) {
      continue;
    }

    preview.unshift({
      role: turn.role,
      text: normalizeWhitespace(turn.text),
    });
    seenKeys.add(key);

    const roles = new Set(preview.map((item) => item.role));
    if (preview.length >= 4 || (preview.length >= 2 && roles.has('user') && roles.has('assistant'))) {
      break;
    }
  }

  return preview.slice(-4);
}

function mergeTranscriptTurns(
  currentTurns: PersistableTranscriptTurn[],
  incomingTurns: PersistableTranscriptTurn[],
): PersistableTranscriptTurn[] {
  const merged = [...currentTurns];

  for (const incoming of incomingTurns) {
    const text = normalizeWhitespace(incoming.text);
    if (!text) continue;

    const normalizedTurn: PersistableTranscriptTurn = {
      role: incoming.role,
      text,
      timestamp: incoming.timestamp ?? null,
    };

    const recentSameRoleIndexes: number[] = [];
    for (let index = merged.length - 1; index >= 0 && recentSameRoleIndexes.length < 4; index -= 1) {
      if (merged[index].role === normalizedTurn.role) {
        recentSameRoleIndexes.push(index);
      }
    }

    let mergedWithRecent = false;
    for (const index of recentSameRoleIndexes) {
      const candidate = merged[index];
      if (
        _looksLikeEquivalent(candidate.text, normalizedTurn.text)
      ) {
        merged[index] = {
          ...candidate,
          text: richerText(candidate.text, normalizedTurn.text),
          timestamp: normalizedTurn.timestamp ?? candidate.timestamp ?? null,
        };
        mergedWithRecent = true;
        break;
      }
    }

    if (mergedWithRecent) {
      continue;
    }

    const last = merged[merged.length - 1];
    if (
      last &&
      last.role === normalizedTurn.role &&
      looksLikeExpansion(last.text, normalizedTurn.text)
    ) {
      merged[merged.length - 1] = {
        ...last,
        text: richerText(last.text, normalizedTurn.text),
        timestamp: normalizedTurn.timestamp ?? last.timestamp ?? null,
      };
      continue;
    }

    const previous = merged[merged.length - 2];
    if (
      previous &&
      previous.role === normalizedTurn.role &&
      looksLikeExpansion(previous.text, normalizedTurn.text) &&
      last &&
      last.role !== normalizedTurn.role
    ) {
      merged[merged.length - 2] = {
        ...previous,
        text: richerText(previous.text, normalizedTurn.text),
        timestamp: normalizedTurn.timestamp ?? previous.timestamp ?? null,
      };
      continue;
    }

    if (last && last.role === normalizedTurn.role && canonicalizeText(last.text) === canonicalizeText(normalizedTurn.text)) {
      continue;
    }

    merged.push(normalizedTurn);
  }

  return merged;
}

function _looksLikeEquivalent(previous: string, next: string): boolean {
  return (
    looksLikeExpansion(previous, next) ||
    canonicalizeText(previous) === canonicalizeText(next)
  );
}

export const LiveVoiceButton: React.FC<LiveVoiceButtonProps> = memo(function LiveVoiceButton({
  threadId,
  projectId,
  selectedAgentId,
  disabled = false,
  variant = 'icon',
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const requestedAgentId = searchParams?.get('voiceAgentId') || selectedAgentId || undefined;

  const [open, setOpen] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusText, setStatusText] = useState('Ready to start a live conversation.');
  const [isMuted, setIsMuted] = useState(false);
  const [transcriptPreview, setTranscriptPreview] = useState<TranscriptPreview[]>([]);
  const [activeAgentName, setActiveAgentName] = useState('Mira');
  const [handoffSaved, setHandoffSaved] = useState(false);
  const [isPreparingThread, setIsPreparingThread] = useState(false);

  const vapiRef = useRef<any>(null);
  const transcriptTurnsRef = useRef<PersistableTranscriptTurn[]>([]);
  const handoffPersistedRef = useRef(false);
  const callIdRef = useRef<string | null>(null);
  const mountedRef = useRef(true);
  const pendingAutoStartRef = useRef(false);
  const autoStartConsumedRef = useRef(false);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (vapiRef.current) {
        try {
          vapiRef.current.stop();
        } catch (error) {
          console.warn('Failed to stop Vapi session on unmount', error);
        }
      }
    };
  }, []);

  const normalizeRole = useCallback((value: unknown): 'user' | 'assistant' | null => {
    const normalized = String(value || '').toLowerCase().trim();
    if (normalized === 'user') return 'user';
    if (['assistant', 'bot', 'agent', 'model', 'system'].includes(normalized)) return 'assistant';
    return null;
  }, []);

  const extractText = useCallback((value: unknown): string => {
    if (!value) return '';
    if (typeof value === 'string') return normalizeWhitespace(value);
    if (Array.isArray(value)) {
      return normalizeWhitespace(
        value
          .map((item) => extractText(item))
          .filter(Boolean)
          .join(' ')
      );
    }
    if (typeof value === 'object') {
      const record = value as Record<string, unknown>;
      return (
        extractText(record.transcript) ||
        extractText(record.text) ||
        extractText(record.message) ||
        extractText(record.content) ||
        ''
      );
    }
    return normalizeWhitespace(String(value));
  }, []);

  const extractTranscriptTurns = useCallback((message: any): PersistableTranscriptTurn[] => {
    const type = String(message?.type || '').toLowerCase();
    const transcriptType = String(
      message?.transcriptType ||
        message?.transcript?.type ||
        message?.message?.transcriptType ||
        ''
    ).toLowerCase();

    if (!type.includes('transcript')) {
      return [];
    }

    if (transcriptType && transcriptType !== 'final') {
      return [];
    }

    const role = normalizeRole(message?.role ?? message?.speaker ?? message?.from);
    const text = extractText(
      message?.transcript ??
        message?.message?.transcript ??
        message?.content ??
        message?.message
    );

    if (!role || !text) {
      return [];
    }

    return [
      {
        role,
        text,
        timestamp: message?.timestamp ?? null,
      },
    ];
  }, [extractText, normalizeRole]);

  const refreshPreview = useCallback(() => {
    setTranscriptPreview(buildTranscriptPreview(transcriptTurnsRef.current));
  }, []);

  const persistCallHandoff = useCallback(async () => {
    if (handoffPersistedRef.current || !threadId) {
      return true;
    }

    const turns = transcriptTurnsRef.current
      .map((turn) => ({
        role: turn.role,
        text: normalizeWhitespace(turn.text),
        timestamp: turn.timestamp ?? null,
      }))
      .filter((turn) => turn.text);

    if (turns.length === 0 && !callIdRef.current) {
      return false;
    }

    handoffPersistedRef.current = true;
    setStatusText('Saving your call handoff to chat...');

    const response = await backendApi.post<VapiHandoffResponse>(
      `/vapi/web/handoff/${threadId}`,
      {
        turns,
        call_id: callIdRef.current,
        agent_id: requestedAgentId ?? null,
        agent_name: activeAgentName,
      },
      {
        showErrors: false,
        timeout: 30000,
      }
    );

    if (response.error) {
      handoffPersistedRef.current = false;
      console.error('Failed to persist live voice handoff', response.error);
      setErrorMessage(response.error.message || 'Could not save the call handoff to chat.');
      setStatusText('Voice ended, but the handoff could not be saved.');
      return false;
    }

    setHandoffSaved(true);
    setStatusText('Call saved to chat. You can keep going in text below.');
    void queryClient.invalidateQueries({ queryKey: threadKeys.messages(threadId) });
    return true;
  }, [activeAgentName, queryClient, requestedAgentId, threadId]);

  const stopSession = useCallback(async () => {
    if (!vapiRef.current) {
      setConnectionState('idle');
      setIsMuted(false);
      return;
    }

    setConnectionState('ending');
    setStatusText('Ending voice conversation...');

    try {
      await vapiRef.current.stop();
    } catch (error) {
      console.warn('Failed to stop Vapi session cleanly', error);
    } finally {
      vapiRef.current = null;
      if (mountedRef.current) {
        setIsMuted(false);
      }
    }
  }, []);

  const handleVapiMessage = useCallback((message: any) => {
    const type = String(message?.type || '').toLowerCase();

    if (type === 'status-update' && message?.status) {
      setStatusText(`Status: ${message.status}`);
    }

    if (message?.call?.id) {
      callIdRef.current = message.call.id;
    }

    const turns = extractTranscriptTurns(message);
    if (turns.length === 0) {
      return;
    }

    transcriptTurnsRef.current = mergeTranscriptTurns(transcriptTurnsRef.current, turns);
    refreshPreview();
  }, [extractTranscriptTurns, refreshPreview]);

  const startSession = useCallback(async () => {
    if (!threadId) {
      return;
    }

    setConnectionState('connecting');
    setErrorMessage(null);
    setHandoffSaved(false);
    setStatusText('Preparing live voice...');
    setTranscriptPreview([]);
    transcriptTurnsRef.current = [];
    handoffPersistedRef.current = false;
    callIdRef.current = null;

    const sessionResponse = await backendApi.post<VapiSessionResponse>(
      `/vapi/web/session/${threadId}`,
      {
        agent_id: requestedAgentId ?? null,
      },
      {
        showErrors: false,
        timeout: 20000,
      }
    );

    if (sessionResponse.error || !sessionResponse.data) {
      const detail = sessionResponse.error?.message || 'Unable to start live voice right now.';
      setConnectionState('error');
      setErrorMessage(detail);
      setStatusText('Live voice could not start.');
      return;
    }

    setActiveAgentName(sessionResponse.data.agent_name || 'Mira');

    try {
      const { default: Vapi } = await import('@vapi-ai/web');
      const vapi = new Vapi(sessionResponse.data.public_key);
      vapiRef.current = vapi;

      vapi.on('call-start', () => {
        if (!mountedRef.current) return;
        setConnectionState('connected');
        setStatusText('Listening...');
      });

      vapi.on('call-end', () => {
        void (async () => {
          const persisted = await persistCallHandoff();
          if (!mountedRef.current) return;
          vapiRef.current = null;
          setConnectionState('idle');
          setIsMuted(false);
          if (!persisted) {
            setStatusText('Voice ended.');
          }
        })();
      });

      vapi.on('speech-start', () => {
        if (!mountedRef.current) return;
        setStatusText(`${sessionResponse.data?.agent_name || 'Mira'} is speaking...`);
      });

      vapi.on('speech-end', () => {
        if (!mountedRef.current) return;
        setStatusText(isMuted ? 'Muted' : 'Listening...');
      });

      vapi.on('message', (message: any) => {
        void handleVapiMessage(message);
      });

      vapi.on('call-start-failed', (event: any) => {
        console.error('Vapi live voice call-start-failed', event);
        if (!mountedRef.current) return;
        const detail = formatVoiceError(
          event?.error || event?.context || event,
          'Live voice failed to connect.'
        );
        setConnectionState('error');
        setErrorMessage(detail);
        setStatusText('Live voice could not connect.');
      });

      vapi.on('error', (error: any) => {
        console.error('Vapi live voice error', error);
        if (!mountedRef.current) return;
        const detail = formatVoiceError(error, 'Live voice hit an unexpected error.');
        setConnectionState('error');
        setErrorMessage(detail);
        setStatusText('Live voice encountered an error.');
      });

      await vapi.start(sessionResponse.data.assistant);
    } catch (error: any) {
      console.error('Failed to initialize Vapi live voice', error);
      setConnectionState('error');
      setErrorMessage(formatVoiceError(error, 'Live voice could not initialize.'));
      setStatusText('Live voice could not initialize.');
    }
  }, [handleVapiMessage, isMuted, persistCallHandoff, requestedAgentId, threadId]);

  useEffect(() => {
    if (!threadId || autoStartConsumedRef.current) {
      return;
    }

    if (searchParams?.get('voiceStart') !== '1') {
      return;
    }

    autoStartConsumedRef.current = true;
    pendingAutoStartRef.current = true;
    setOpen(true);

    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.delete('voiceStart');
    nextParams.delete('voiceAgentId');
    const nextUrl = nextParams.size ? `${pathname}?${nextParams.toString()}` : pathname;
    router.replace(nextUrl, { scroll: false });
  }, [pathname, router, searchParams, threadId]);

  useEffect(() => {
    if (!open || !pendingAutoStartRef.current || connectionState !== 'idle' || !threadId) {
      return;
    }

    pendingAutoStartRef.current = false;
    void startSession();
  }, [connectionState, open, startSession, threadId]);

  const handleToggleMute = useCallback(() => {
    if (!vapiRef.current || connectionState !== 'connected') {
      return;
    }

    const nextMuted = !isMuted;
    vapiRef.current.setMuted(nextMuted);
    setIsMuted(nextMuted);
    setStatusText(nextMuted ? 'Muted' : 'Listening...');
  }, [connectionState, isMuted]);

  const createVoiceThreadAndRoute = useCallback(async () => {
    try {
      setIsPreparingThread(true);
      setConnectionState('connecting');
      setStatusText('Creating your voice conversation...');
      const newThread = await createThread(projectId);
      const params = new URLSearchParams({ voiceStart: '1' });
      if (requestedAgentId) {
        params.set('voiceAgentId', requestedAgentId);
      }
      const nextUrl = newThread.project_id
        ? `/projects/${newThread.project_id}/thread/${newThread.thread_id}?${params.toString()}`
        : `/thread/${newThread.thread_id}?${params.toString()}`;
      toast.success('Opening your new voice conversation...');
      router.push(nextUrl);
    } catch (error: any) {
      console.error('Failed to create a voice thread', error);
      const detail = formatVoiceError(error, 'Could not create a new voice conversation.');
      setConnectionState('error');
      setErrorMessage(detail);
      setStatusText('Could not create a new voice conversation.');
      toast.error(detail);
    } finally {
      if (mountedRef.current) {
        setIsPreparingThread(false);
      }
    }
  }, [projectId, requestedAgentId, router]);

  const handleOpenVoice = useCallback(() => {
    if (disabled || isPreparingThread) {
      return;
    }

    setErrorMessage(null);
    setHandoffSaved(false);
    setTranscriptPreview([]);
    transcriptTurnsRef.current = [];
    handoffPersistedRef.current = false;
    callIdRef.current = null;
    setConnectionState('idle');
    setStatusText(
      threadId
        ? 'Ready to start a live conversation in this thread.'
        : 'Ready to start a new voice conversation.'
    );
    setOpen(true);
  }, [disabled, isPreparingThread, threadId]);

  const handleStartLiveVoice = useCallback(async () => {
    if (connectionState === 'connecting' || connectionState === 'ending' || isPreparingThread) {
      return;
    }

    setErrorMessage(null);

    if (threadId) {
      await startSession();
      return;
    }

    await createVoiceThreadAndRoute();
  }, [connectionState, createVoiceThreadAndRoute, isPreparingThread, startSession, threadId]);

  const renderButton = () => {
    const commonProps = {
      type: 'button' as const,
      disabled: disabled || isPreparingThread,
      onClick: () => void handleOpenVoice(),
    };

    if (variant === 'pill') {
      return (
        <Button
          {...commonProps}
          variant="outline"
          size="sm"
          className="h-10 rounded-2xl border-border/70 bg-background/90 px-4 text-sm font-medium text-foreground shadow-sm hover:bg-accent/60"
        >
          {isPreparingThread ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Radio className="mr-2 h-4 w-4" />
          )}
          Try voice mode
        </Button>
      );
    }

    return (
      <Button
        {...commonProps}
        variant="ghost"
        size="sm"
        className="h-10 rounded-2xl border-[1.5px] border-border bg-transparent px-2 py-2 text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
      >
        {isPreparingThread ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <AudioLines className="h-5 w-5" />
        )}
      </Button>
    );
  };

  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>{renderButton()}</TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          <p>{threadId ? 'Live voice with Mira' : 'Start a new voice conversation'}</p>
        </TooltipContent>
      </Tooltip>

      <Dialog
        open={open}
        onOpenChange={(nextOpen) => {
          setOpen(nextOpen);
          if (!nextOpen && (connectionState === 'connected' || connectionState === 'connecting' || connectionState === 'ending')) {
            void stopSession();
          }
        }}
      >
        <DialogContent className="overflow-hidden border-none bg-transparent p-0 shadow-none sm:max-w-2xl">
          <div className="relative overflow-hidden rounded-[32px] border border-white/10 bg-[#060913] text-white shadow-[0_40px_120px_rgba(6,9,19,0.55)]">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(109,114,255,0.20),transparent_38%),radial-gradient(circle_at_bottom,rgba(0,212,255,0.15),transparent_36%)]" />
            <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.05),transparent_40%,transparent_60%,rgba(255,255,255,0.03))]" />

            <DialogHeader className="relative px-8 pb-0 pt-8">
              <DialogTitle className="text-4xl font-semibold tracking-tight text-white">
                Live voice with {activeAgentName}
              </DialogTitle>
              <DialogDescription className="mt-3 max-w-2xl text-lg leading-8 text-white/72">
                {threadId
                  ? 'Talk through ideas in real time. When the call ends, Mira saves one clean handoff into chat so you can keep going in text without the transcript clutter.'
                  : 'Start a voice-first conversation. When the call ends, Mira opens a clean thread handoff so you can continue in text without losing the flow.'}
              </DialogDescription>
            </DialogHeader>

            <div className="relative px-8 pb-8 pt-6">
              <div className="mb-6 flex items-center justify-center">
                <div className="relative flex h-40 w-40 items-center justify-center">
                  <div
                    className={`absolute inset-0 rounded-full bg-cyan-400/20 blur-3xl ${
                      connectionState === 'connected' ? 'animate-pulse' : ''
                    }`}
                  />
                  <div className="absolute inset-2 rounded-full border border-cyan-300/20" />
                  <div className="absolute inset-6 rounded-full border border-cyan-200/15" />
                  <div className="absolute inset-10 rounded-full border border-white/10" />
                  <div className="absolute inset-[34px] rounded-full bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.18),rgba(84,111,255,0.12),rgba(6,9,19,0.9))]" />
                  <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-white/15 bg-white/6 backdrop-blur-md">
                    {connectionState === 'connecting' || isPreparingThread ? (
                      <Loader2 className="h-7 w-7 animate-spin text-cyan-200" />
                    ) : connectionState === 'connected' ? (
                      <AudioLines className="h-7 w-7 text-cyan-100" />
                    ) : handoffSaved ? (
                      <Sparkles className="h-7 w-7 text-cyan-100" />
                    ) : (
                      <Radio className="h-7 w-7 text-cyan-100" />
                    )}
                  </div>
                </div>
              </div>

              <div className="mb-6 rounded-[28px] border border-white/10 bg-white/[0.05] p-5 backdrop-blur-xl">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium uppercase tracking-[0.18em] text-white/45">Status</p>
                    <p className="mt-2 text-2xl font-medium text-white">{statusText}</p>
                  </div>
                  {connectionState === 'connecting' || connectionState === 'ending' ? (
                    <Loader2 className="h-6 w-6 animate-spin text-cyan-200" />
                  ) : (
                    <div
                      className={`h-4 w-4 rounded-full ${
                        connectionState === 'connected'
                          ? 'bg-emerald-400 shadow-[0_0_24px_rgba(74,222,128,0.8)]'
                          : connectionState === 'error'
                            ? 'bg-rose-400 shadow-[0_0_24px_rgba(251,113,133,0.75)]'
                            : handoffSaved
                              ? 'bg-cyan-300 shadow-[0_0_24px_rgba(125,211,252,0.8)]'
                              : 'bg-white/25'
                      }`}
                    />
                  )}
                </div>
                <div className="mt-4 flex items-end justify-center gap-2">
                  {Array.from({ length: 12 }).map((_, index) => {
                    const active = connectionState === 'connected';
                    const height = active ? 18 + ((index * 7) % 24) : 8 + ((index * 3) % 8);
                    return (
                      <div
                        key={index}
                        className={`w-1.5 rounded-full ${
                          active ? 'animate-pulse bg-cyan-300/85' : 'bg-white/20'
                        }`}
                        style={{
                          height,
                          animationDelay: `${index * 90}ms`,
                          animationDuration: `${900 + index * 30}ms`,
                        }}
                      />
                    );
                  })}
                </div>
              </div>

              {errorMessage && (
                <div className="mb-6 rounded-[24px] border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-100">
                  {errorMessage}
                </div>
              )}

              {handoffSaved && connectionState === 'idle' && (
                <div className="mb-6 rounded-[24px] border border-emerald-400/25 bg-emerald-400/10 p-5">
                  <p className="text-lg font-medium text-white">Call saved cleanly</p>
                  <p className="mt-2 text-sm leading-6 text-white/72">
                    Mira added one structured handoff into this thread. Continue typing below to turn the conversation into work.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button
                      type="button"
                      onClick={() => setOpen(false)}
                      className="rounded-2xl bg-white px-4 text-black hover:bg-white/90"
                    >
                      Continue in chat
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => void startSession()}
                      className="rounded-2xl border-white/15 bg-transparent text-white hover:bg-white/8"
                    >
                      Start another voice chat
                    </Button>
                  </div>
                </div>
              )}

              <div className="mb-6 flex flex-wrap items-center gap-3">
                {connectionState === 'connected' || connectionState === 'ending' ? (
                  <>
                    <Button
                      type="button"
                      onClick={() => void stopSession()}
                      disabled={connectionState === 'ending'}
                      className="gap-2 rounded-2xl bg-white px-5 text-black hover:bg-white/90"
                    >
                      <PhoneOff className="h-4 w-4" />
                      End voice
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleToggleMute}
                      className="gap-2 rounded-2xl border-white/15 bg-transparent px-5 text-white hover:bg-white/8"
                    >
                      <MicOff className="h-4 w-4" />
                      {isMuted ? 'Unmute' : 'Mute'}
                    </Button>
                  </>
                ) : (
                  <Button
                    type="button"
                    onClick={() => void handleStartLiveVoice()}
                    disabled={connectionState === 'connecting' || isPreparingThread}
                    className="gap-2 rounded-2xl bg-white px-5 text-black hover:bg-white/90"
                  >
                    <PhoneOutgoing className="h-4 w-4" />
                    {isPreparingThread
                      ? 'Creating thread…'
                      : connectionState === 'connecting'
                        ? 'Connecting…'
                        : 'Start live voice'}
                  </Button>
                )}
              </div>

              <div className="rounded-[28px] border border-white/10 bg-white/[0.04] p-5 backdrop-blur-xl">
                <p className="mb-3 text-sm font-medium uppercase tracking-[0.18em] text-white/45">
                  Recent transcript
                </p>
                {transcriptPreview.length === 0 ? (
                  <p className="text-sm leading-7 text-white/62">
                    The latest exchange shows up here while the call is active. The thread stays clean until the final handoff is saved.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {transcriptPreview.map((turn, index) => (
                      <div
                        key={`${turn.role}-${index}`}
                        className="rounded-2xl border border-white/8 bg-black/10 px-4 py-3 text-sm"
                      >
                        <span className="font-medium capitalize text-white">{turn.role}:</span>{' '}
                        <span className="text-white/72">{turn.text}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
});
