import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4
from cryptography.fernet import Fernet
import os
from urllib.parse import urlparse
from urllib.parse import parse_qs
from urllib.parse import urlencode

from core.services.supabase import DBConnection
from core.utils.logger import logger


@dataclass
class ComposioProfile:
    profile_id: str
    account_id: str
    mcp_qualified_name: str
    profile_name: str
    display_name: str
    encrypted_config: str
    config_hash: str
    toolkit_slug: str
    toolkit_name: str
    mcp_url: str
    redirect_url: Optional[str] = None
    connected_account_id: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
    is_connected: bool = False
    created_at: datetime = None
    updated_at: datetime = None


class ComposioProfileService:
    def __init__(self, db_connection: Optional[DBConnection] = None):
        self.db = db_connection or DBConnection()
        
    def _get_encryption_key(self) -> bytes:
        key = os.getenv("ENCRYPTION_KEY") or os.getenv("MCP_CREDENTIAL_ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY or MCP_CREDENTIAL_ENCRYPTION_KEY environment variable is required")
        return key.encode()

    def _encrypt_config(self, config_json: str) -> str:
        fernet = Fernet(self._get_encryption_key())
        return fernet.encrypt(config_json.encode()).decode()

    def _decrypt_config(self, encrypted_config: str) -> Dict[str, Any]:
        fernet = Fernet(self._get_encryption_key())
        decrypted = fernet.decrypt(encrypted_config.encode()).decode()
        return json.loads(decrypted)

    def _generate_config_hash(self, config_json: str) -> str:
        return hashlib.sha256(config_json.encode()).hexdigest()

    def _parse_timestamp(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))

    def _toolkit_slug_from_qualified_name(self, qualified_name: Optional[str]) -> str:
        value = (qualified_name or "").strip().lower()
        if value.startswith("composio."):
            return value.split(".", 1)[1]
        return value

    def _fallback_toolkit_name(self, toolkit_slug: str) -> str:
        normalized = (toolkit_slug or "composio").replace("_", " ").replace("-", " ").strip()
        return normalized.title() if normalized else "Composio"

    def _build_profile_from_config(self, row: Dict[str, Any], config: Dict[str, Any]) -> ComposioProfile:
        return ComposioProfile(
            profile_id=row['profile_id'],
            account_id=row['account_id'],
            mcp_qualified_name=row['mcp_qualified_name'],
            profile_name=row['profile_name'],
            display_name=row['display_name'],
            encrypted_config=row['encrypted_config'],
            config_hash=row['config_hash'],
            toolkit_slug=config.get('toolkit_slug', ''),
            toolkit_name=config.get('toolkit_name', self._fallback_toolkit_name(config.get('toolkit_slug', ''))),
            mcp_url=config.get('mcp_url', ''),
            redirect_url=config.get('redirect_url'),
            connected_account_id=config.get('connected_account_id'),
            is_active=row.get('is_active', True),
            is_default=row.get('is_default', False),
            is_connected=bool(config.get('mcp_url')),
            created_at=self._parse_timestamp(row.get('created_at')),
            updated_at=self._parse_timestamp(row.get('updated_at')),
        )

    def _build_degraded_profile(self, row: Dict[str, Any]) -> ComposioProfile:
        toolkit_slug = self._toolkit_slug_from_qualified_name(row.get('mcp_qualified_name'))
        return ComposioProfile(
            profile_id=row['profile_id'],
            account_id=row['account_id'],
            mcp_qualified_name=row['mcp_qualified_name'],
            profile_name=row['profile_name'],
            display_name=row['display_name'],
            encrypted_config=row['encrypted_config'],
            config_hash=row['config_hash'],
            toolkit_slug=toolkit_slug,
            toolkit_name=self._fallback_toolkit_name(toolkit_slug),
            mcp_url="",
            redirect_url=None,
            connected_account_id=None,
            is_active=row.get('is_active', True),
            is_default=row.get('is_default', False),
            is_connected=False,
            created_at=self._parse_timestamp(row.get('created_at')),
            updated_at=self._parse_timestamp(row.get('updated_at')),
        )

    def _normalize_runtime_mcp_url(
        self,
        mcp_url: str,
        connected_account_id: Optional[str] = None,
        user_id: Optional[str] = None,
        toolkit_slug: Optional[str] = None,
    ) -> str:
        """
        Normalize runtime URL routing.
        If connected_account_id is available, enforce connected-account routing only
        to avoid user_id/connected_account mismatches from stale legacy URLs.
        """
        if not mcp_url:
            return mcp_url
        parsed = urlparse(mcp_url)
        existing = parse_qs(parsed.query or "")

        normalized_toolkit = (toolkit_slug or "").strip().lower()

        # Gmail runtime is sensitive to Composio user context. Ensure a concrete
        # Composio user_id is present in URL query whenever we have one.
        if normalized_toolkit == "gmail" and user_id:
            if existing.get("user_id", [None])[0] != user_id:
                existing["user_id"] = [user_id]
                query = urlencode(existing, doseq=True)
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{query}"
            return mcp_url

        # Preserve Composio-generated context as-is when already pinned.
        # Some projects use connected_account_ids (plural) URLs.
        has_user_context = any(
            key in existing
            for key in ("user_id", "connected_account_id", "connected_account_ids")
        )
        if has_user_context:
            return mcp_url

        if not connected_account_id:
            return mcp_url

        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?connected_account_id={connected_account_id}"
        return normalized

    def _row_to_profile(self, row: Dict[str, Any]) -> ComposioProfile:
        config = self._decrypt_config(row['encrypted_config'])
        return self._build_profile_from_config(row, config)

    def _build_config(
        self,
        toolkit_slug: str,
        toolkit_name: str,
        mcp_url: str,
        redirect_url: Optional[str] = None,
        user_id: str = "default",
        connected_account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "type": "composio",
            "toolkit_slug": toolkit_slug,
            "toolkit_name": toolkit_name,
            "mcp_url": mcp_url,
            "redirect_url": redirect_url,
            "user_id": user_id,
            "connected_account_id": connected_account_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    def _select_runtime_mcp_url(
        self,
        toolkit_slug: str,
        response,
        connected_account_id: Optional[str],
        runtime_user_id: Optional[str],
    ) -> Optional[str]:
        requested_toolkit = (toolkit_slug or "").strip().lower()

        if requested_toolkit == "gmail":
            if getattr(response, "user_ids_url", None):
                refreshed_url = response.user_ids_url[0]
            elif getattr(response, "connected_account_urls", None):
                refreshed_url = response.connected_account_urls[0]
            else:
                refreshed_url = getattr(response, "mcp_url", None)
        elif getattr(response, "connected_account_urls", None):
            refreshed_url = response.connected_account_urls[0]
        elif getattr(response, "user_ids_url", None):
            refreshed_url = response.user_ids_url[0]
        else:
            refreshed_url = getattr(response, "mcp_url", None)

        if not refreshed_url:
            return None

        return self._normalize_runtime_mcp_url(
            refreshed_url,
            connected_account_id=connected_account_id,
            user_id=runtime_user_id,
            toolkit_slug=requested_toolkit,
        )

    async def _repair_profile_row_without_decrypt(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        toolkit_slug = self._toolkit_slug_from_qualified_name(row.get("mcp_qualified_name"))
        profile_id = row.get("profile_id")
        account_id = row.get("account_id")
        if not toolkit_slug or not profile_id or not account_id:
            return None

        try:
            from .auth_config_service import AuthConfigService
            from .connected_account_service import ConnectedAccountService
            from .mcp_server_service import MCPServerService

            auth_config_service = AuthConfigService()
            connected_account_service = ConnectedAccountService()
            mcp_server_service = MCPServerService()

            auth_configs = await auth_config_service.list_auth_configs(toolkit_slug)
            auth_config_ids = [config.id for config in auth_configs if config.id]
            if not auth_config_ids:
                logger.warning(
                    f"[COMPOSIO PROFILE RECOVERY] No auth configs found for {toolkit_slug}; "
                    f"cannot auto-repair profile {profile_id}"
                )
                return None

            connected_accounts = await connected_account_service.list_connected_accounts(
                auth_config_ids=auth_config_ids,
                statuses=["ACTIVE"],
            )
            if len(connected_accounts) != 1:
                logger.warning(
                    f"[COMPOSIO PROFILE RECOVERY] Expected exactly 1 active connected account for {toolkit_slug}, "
                    f"found {len(connected_accounts)}; cannot auto-repair profile {profile_id}"
                )
                return None

            connected_account = connected_accounts[0]
            auth_config_id = connected_account.auth_config_id
            if not auth_config_id:
                logger.warning(
                    f"[COMPOSIO PROFILE RECOVERY] Active connected account {connected_account.id} for {toolkit_slug} "
                    f"has no auth_config_id; cannot auto-repair profile {profile_id}"
                )
                return None

            servers = await mcp_server_service.list_mcp_servers()
            matching_servers = [
                server for server in servers
                if auth_config_id in (server.auth_config_ids or [])
            ]
            if not matching_servers:
                logger.warning(
                    f"[COMPOSIO PROFILE RECOVERY] No MCP server found for auth_config_id {auth_config_id}; "
                    f"cannot auto-repair profile {profile_id}"
                )
                return None

            matching_servers.sort(
                key=lambda server: (server.updated_at or server.created_at or ""),
                reverse=True,
            )
            selected_server = matching_servers[0]
            runtime_user_id = getattr(connected_account, "user_id", None)
            response = await mcp_server_service.generate_mcp_url(
                mcp_server_id=selected_server.id,
                connected_account_ids=[connected_account.id],
                user_ids=[runtime_user_id] if runtime_user_id else None,
            )
            runtime_url = self._select_runtime_mcp_url(
                toolkit_slug=toolkit_slug,
                response=response,
                connected_account_id=connected_account.id,
                runtime_user_id=runtime_user_id,
            )
            if not runtime_url:
                logger.warning(
                    f"[COMPOSIO PROFILE RECOVERY] MCP URL generation returned no runtime URL for "
                    f"profile {profile_id} ({toolkit_slug})"
                )
                return None

            config = self._build_config(
                toolkit_slug=toolkit_slug,
                toolkit_name=self._fallback_toolkit_name(toolkit_slug),
                mcp_url=runtime_url,
                redirect_url=connected_account.redirect_url,
                user_id=runtime_user_id or "default",
                connected_account_id=connected_account.id,
            )
            config_json = json.dumps(config, sort_keys=True)
            encrypted_config = self._encrypt_config(config_json)
            config_hash = self._generate_config_hash(config_json)
            now_iso = datetime.now(timezone.utc).isoformat()

            client = await self.db.client
            await client.table('user_mcp_credential_profiles').update({
                'encrypted_config': encrypted_config,
                'config_hash': config_hash,
                'updated_at': now_iso,
            }).eq('profile_id', profile_id).eq('account_id', account_id).execute()

            logger.info(
                f"[COMPOSIO PROFILE RECOVERY] Repaired stale encrypted profile {profile_id} "
                f"for toolkit {toolkit_slug} using connected account {connected_account.id}"
            )

            updated_row = dict(row)
            updated_row['encrypted_config'] = encrypted_config
            updated_row['config_hash'] = config_hash
            updated_row['updated_at'] = now_iso
            return updated_row
        except Exception as e:
            logger.warning(
                f"[COMPOSIO PROFILE RECOVERY] Failed to auto-repair profile {profile_id} "
                f"for toolkit {toolkit_slug}: {e}"
            )
            return None

    async def _resolve_row_and_config(
        self,
        row: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        try:
            return row, self._decrypt_config(row['encrypted_config'])
        except Exception as decrypt_error:
            repaired_row = await self._repair_profile_row_without_decrypt(row)
            if repaired_row:
                try:
                    return repaired_row, self._decrypt_config(repaired_row['encrypted_config'])
                except Exception as repaired_error:
                    logger.warning(
                        f"[COMPOSIO PROFILE RECOVERY] Repaired profile {row.get('profile_id')} still could not be "
                        f"decrypted: {repaired_error}"
                    )
            logger.warning(
                f"[COMPOSIO PROFILE RECOVERY] Profile {row.get('profile_id')} remains unreadable after recovery "
                f"attempt: {decrypt_error}"
            )
            return row, None

    async def _generate_unique_profile_name(self, base_name: str, account_id: str, mcp_qualified_name: str, client) -> str:
        original_name = base_name
        counter = 1
        current_name = base_name
        
        while True:
            existing = await client.table('user_mcp_credential_profiles').select('profile_id').eq(
                'account_id', account_id
            ).eq('mcp_qualified_name', mcp_qualified_name).eq('profile_name', current_name).execute()
            
            if not existing.data:
                return current_name
            
            counter += 1
            current_name = f"{original_name} ({counter})"

    async def create_profile(
        self,
        account_id: str,
        profile_name: str,
        toolkit_slug: str,
        toolkit_name: str,
        mcp_url: str,
        redirect_url: Optional[str] = None,
        user_id: str = "default",
        is_default: bool = False,
        connected_account_id: Optional[str] = None,
    ) -> ComposioProfile:
        try:
            logger.debug(f"Creating Composio profile for user: {account_id}, toolkit: {toolkit_slug}")
            logger.debug(f"MCP URL to store: {mcp_url}")
            
            config = self._build_config(
                toolkit_slug, toolkit_name, mcp_url, redirect_url, user_id, connected_account_id
            )
            config_json = json.dumps(config, sort_keys=True)
            encrypted_config = self._encrypt_config(config_json)
            config_hash = self._generate_config_hash(config_json)
            
            mcp_qualified_name = f"composio.{toolkit_slug}"
            profile_id = str(uuid4())
            now = datetime.now(timezone.utc)
            
            client = await self.db.client
            
            unique_profile_name = await self._generate_unique_profile_name(
                profile_name, account_id, mcp_qualified_name, client
            )
            
            if unique_profile_name != profile_name:
                logger.debug(f"Generated unique profile name: {unique_profile_name} (original: {profile_name})")
            
            if is_default:
                await client.table('user_mcp_credential_profiles').update({
                    'is_default': False
                }).eq('account_id', account_id).eq('mcp_qualified_name', mcp_qualified_name).execute()
            
            result = await client.table('user_mcp_credential_profiles').insert({
                'profile_id': profile_id,
                'account_id': account_id,
                'mcp_qualified_name': mcp_qualified_name,
                'profile_name': unique_profile_name,
                'display_name': unique_profile_name,
                'encrypted_config': encrypted_config,
                'config_hash': config_hash,
                'is_active': True,
                'is_default': is_default,
                'created_at': now.isoformat(),
                'updated_at': now.isoformat()
            }).execute()
            
            if not result.data:
                raise Exception("Failed to create profile in database")
            
            logger.debug(f"Successfully created Composio profile: {profile_id}")
            
            return ComposioProfile(
                profile_id=profile_id,
                account_id=account_id,
                mcp_qualified_name=mcp_qualified_name,
                profile_name=unique_profile_name,
                display_name=unique_profile_name,
                encrypted_config=encrypted_config,
                config_hash=config_hash,
                toolkit_slug=toolkit_slug,
                toolkit_name=toolkit_name,
                mcp_url=mcp_url,
                redirect_url=redirect_url,
                connected_account_id=connected_account_id,
                is_active=True,
                is_default=is_default,
                # A profile is usable when it has a runtime MCP URL.
                # redirect_url is only used for interactive OAuth handoff and may be absent afterward.
                is_connected=bool(mcp_url),
                created_at=now,
                updated_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create Composio profile: {e}", exc_info=True)
            raise

    async def get_mcp_config_for_agent(self, profile_id: str, account_id: str) -> Dict[str, Any]:
        try:
            client = await self.db.client
            query = client.table('user_mcp_credential_profiles').select('*').eq(
                'profile_id', profile_id
            ).eq('account_id', account_id)
            result = await query.execute()

            if not result.data:
                raise ValueError(f"Profile {profile_id} not found or does not belong to account {account_id}")
            
            profile_data, config = await self._resolve_row_and_config(result.data[0])
            if not config:
                raise ValueError(
                    f"Profile {profile_id} could not be decrypted and could not be auto-repaired. "
                    "Reconnect the integration and try again."
                )
            
            if config.get('type') != 'composio':
                raise ValueError(f"Profile {profile_id} is not a Composio profile")
            
            return {
                "name": config['toolkit_name'],
                "type": "composio",
                "mcp_qualified_name": profile_data['mcp_qualified_name'],
                "toolkit_slug": config.get('toolkit_slug', ''),
                "config": {
                    "profile_id": profile_id
                },
                "enabledTools": []
            }
            
        except Exception as e:
            logger.error(f"Failed to get MCP config for profile {profile_id}: {e}", exc_info=True)
            raise
    
    async def get_mcp_url_for_runtime(self, profile_id: str, account_id: str) -> str:
        try:
            client = await self.db.client

            query = client.table('user_mcp_credential_profiles').select('*').eq(
                'profile_id', profile_id
            ).eq('account_id', account_id)

            result = await query.execute()

            if not result.data:
                raise ValueError(f"Profile {profile_id} not found or does not belong to account {account_id}")

            profile_data, config = await self._resolve_row_and_config(result.data[0])
            if not config:
                raise ValueError(
                    f"Profile {profile_id} could not be decrypted and could not be auto-repaired. "
                    "Reconnect the integration and try again."
                )

            if config.get('type') != 'composio':
                raise ValueError(f"Profile {profile_id} is not a Composio profile")

            mcp_url = config.get('mcp_url')
            if not mcp_url:
                raise ValueError(f"Profile {profile_id} has no MCP URL")

            connected_account_id = config.get('connected_account_id')
            runtime_user_id = config.get('user_id')
            runtime_toolkit_slug = config.get('toolkit_slug')

            normalized_url = self._normalize_runtime_mcp_url(
                mcp_url,
                connected_account_id=connected_account_id,
                user_id=runtime_user_id,
                toolkit_slug=runtime_toolkit_slug,
            )
            if normalized_url != mcp_url:
                logger.info(f"[MCP URL] Normalized for profile {profile_id}: {normalized_url}")
            else:
                logger.info(f"[MCP URL] Using stored URL for profile {profile_id}: {mcp_url}")
            return normalized_url

        except Exception as e:
            logger.error(f"Failed to get MCP URL for profile {profile_id}: {e}", exc_info=True)
            raise

    async def refresh_runtime_mcp_url(
        self,
        profile_id: str,
        account_id: str,
        toolkit_slug: Optional[str] = None,
    ) -> Optional[str]:
        """
        Best-effort runtime URL refresh for stale Composio profile URLs.
        Re-generates an MCP URL from Composio using connected_account_id and stores it back in profile config.
        Returns refreshed URL if available, otherwise None.
        """
        try:
            client = await self.db.client
            result = await client.table('user_mcp_credential_profiles').select('*').eq(
                'profile_id', profile_id
            ).eq('account_id', account_id).execute()

            if not result.data:
                logger.warning(f"[MCP URL] refresh skipped: profile {profile_id} not found for account {account_id}")
                return None

            row = result.data[0]
            resolved_row, config = await self._resolve_row_and_config(row)
            if not config:
                return None
            connected_account_id = config.get('connected_account_id')
            runtime_user_id = config.get('user_id')
            requested_toolkit = (
                toolkit_slug
                or config.get('toolkit_slug')
                or ''
            ).strip().lower()
            if not connected_account_id:
                logger.warning(f"[MCP URL] refresh skipped: profile {profile_id} has no connected_account_id")
                return None

            from .connected_account_service import ConnectedAccountService
            from .mcp_server_service import MCPServerService

            connected_account_service = ConnectedAccountService()
            mcp_server_service = MCPServerService()

            connected_account = await connected_account_service.get_connected_account(connected_account_id)
            if not connected_account:
                logger.warning(
                    f"[MCP URL] refresh skipped: connected account {connected_account_id} not found"
                )
                return None

            account_status = (connected_account.status or "").upper()
            if account_status and account_status not in {"ACTIVE", "CONNECTED"}:
                logger.warning(
                    f"[MCP URL] refresh skipped: connected account {connected_account_id} status is {account_status}"
                )
                return None

            servers = await mcp_server_service.list_mcp_servers()
            auth_config_id = connected_account.auth_config_id
            matching_servers = [
                server for server in servers
                if auth_config_id and auth_config_id in (server.auth_config_ids or [])
            ]
            if not matching_servers:
                logger.warning(
                    f"[MCP URL] refresh skipped: no MCP server found for auth_config_id {auth_config_id}"
                )
                return None

            prioritized = []
            others = []
            for server in matching_servers:
                toolkits = [(tk or '').strip().lower() for tk in (server.toolkits or [])]
                if requested_toolkit and requested_toolkit in toolkits:
                    prioritized.append(server)
                else:
                    others.append(server)
            ordered_servers = prioritized + others

            # Prefer newest server first when timestamps are available.
            ordered_servers.sort(
                key=lambda s: (s.updated_at or s.created_at or ''),
                reverse=True
            )

            refresh_errors: List[str] = []
            for server in ordered_servers:
                try:
                    refresh_user_id = getattr(connected_account, "user_id", None) or runtime_user_id
                    response = await mcp_server_service.generate_mcp_url(
                        mcp_server_id=server.id,
                        connected_account_ids=[connected_account_id],
                        user_ids=[refresh_user_id] if refresh_user_id else None,
                    )

                    refreshed_url = self._select_runtime_mcp_url(
                        toolkit_slug=requested_toolkit,
                        response=response,
                        connected_account_id=connected_account_id,
                        runtime_user_id=refresh_user_id,
                    )

                    if not refreshed_url:
                        continue

                    config_changed = False
                    if refresh_user_id and config.get("user_id") != refresh_user_id:
                        config["user_id"] = refresh_user_id
                        config_changed = True

                    if config.get('mcp_url') != refreshed_url:
                        config['mcp_url'] = refreshed_url
                        config_changed = True

                    if config_changed:
                        config_json = json.dumps(config, sort_keys=True)
                        encrypted_config = self._encrypt_config(config_json)
                        config_hash = self._generate_config_hash(config_json)
                        now = datetime.now(timezone.utc).isoformat()

                        await client.table('user_mcp_credential_profiles').update({
                            'encrypted_config': encrypted_config,
                            'config_hash': config_hash,
                            'updated_at': now
                        }).eq('profile_id', profile_id).eq('account_id', account_id).execute()

                        logger.info(
                            f"[MCP URL] Refreshed Composio URL for profile {profile_id} using server {server.id}"
                        )
                    else:
                        logger.info(
                            f"[MCP URL] Refreshed Composio URL matched existing value for profile {profile_id}"
                        )

                    return refreshed_url
                except Exception as server_error:
                    refresh_errors.append(f"server_id={server.id}: {server_error}")
                    logger.warning(
                        f"[MCP URL] Failed URL refresh attempt for profile {profile_id} with server {server.id}: {server_error}"
                    )

            if refresh_errors:
                logger.warning(
                    f"[MCP URL] Unable to refresh profile {profile_id}. Errors: {' | '.join(refresh_errors)}"
                )
            return None

        except Exception as e:
            logger.error(f"Failed to refresh MCP URL for profile {profile_id}: {e}", exc_info=True)
            return None

    async def get_profile_config(self, profile_id: str, account_id: str) -> Dict[str, Any]:
        try:
            client = await self.db.client

            query = client.table('user_mcp_credential_profiles').select('encrypted_config').eq(
                'profile_id', profile_id
            ).eq('account_id', account_id)

            result = await query.execute()

            if not result.data:
                raise ValueError(f"Profile {profile_id} not found or does not belong to account {account_id}")

            _, config = await self._resolve_row_and_config(result.data[0])
            if not config:
                raise ValueError(
                    f"Profile {profile_id} could not be decrypted and could not be auto-repaired. "
                    "Reconnect the integration and try again."
                )

            return config

        except Exception as e:
            logger.error(f"Failed to get config for profile {profile_id}: {e}", exc_info=True)
            raise

    async def get_profile(self, profile_id: str, account_id: str) -> Optional[ComposioProfile]:
        try:
            client = await self.db.client
            result = await client.table('user_mcp_credential_profiles').select('*').eq(
                'profile_id', profile_id
            ).eq('account_id', account_id).execute()

            if not result.data:
                return None

            row, config = await self._resolve_row_and_config(result.data[0])
            if config:
                return self._build_profile_from_config(row, config)
            return self._build_degraded_profile(row)
        except Exception as e:
            logger.error(f"Failed to get Composio profile {profile_id}: {e}", exc_info=True)
            raise

    async def get_profiles(self, account_id: str, toolkit_slug: Optional[str] = None) -> List[ComposioProfile]:
        try:
            client = await self.db.client
            
            query = client.table('user_mcp_credential_profiles').select('*').eq('account_id', account_id)
            
            if toolkit_slug:
                query = query.eq('mcp_qualified_name', f"composio.{toolkit_slug}")
            else:
                query = query.like('mcp_qualified_name', 'composio.%')

            # Deterministic order: prefer default profiles, then newest activity.
            query = query.order('is_default', desc=True).order('updated_at', desc=True).order('created_at', desc=True)
            
            result = await query.execute()
            
            profiles = []
            for row in result.data:
                resolved_row, config = await self._resolve_row_and_config(row)
                if config:
                    profiles.append(self._build_profile_from_config(resolved_row, config))
                else:
                    profiles.append(self._build_degraded_profile(resolved_row))
            
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get Composio profiles: {e}", exc_info=True)
            raise 

    async def resolve_runtime_mcp_url(
        self,
        account_id: str,
        toolkit_slug: str,
        preferred_profile_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Resolve a working runtime MCP URL for a toolkit.
        Returns: (mcp_url, resolved_profile_id)
        """
        if preferred_profile_id:
            try:
                preferred_url = await self.get_mcp_url_for_runtime(preferred_profile_id, account_id=account_id)
                return preferred_url, preferred_profile_id
            except Exception as e:
                logger.warning(
                    f"Preferred Composio profile {preferred_profile_id} is not usable for {toolkit_slug}: {e}"
                )

        profiles = await self.get_profiles(account_id, toolkit_slug=toolkit_slug)
        if not profiles:
            raise ValueError(f"No Composio profiles found for toolkit '{toolkit_slug}'")

        connected_profiles = [p for p in profiles if p.is_active and p.mcp_url]
        if not connected_profiles:
            raise ValueError(
                f"No connected Composio profiles with MCP URL for toolkit '{toolkit_slug}'. "
                "Reconnect the integration and try again."
            )

        for profile in connected_profiles:
            try:
                mcp_url = await self.get_mcp_url_for_runtime(profile.profile_id, account_id=account_id)
                logger.info(
                    f"Resolved fallback Composio profile {profile.profile_id} for toolkit {toolkit_slug}"
                )
                return mcp_url, profile.profile_id
            except Exception as e:
                logger.warning(
                    f"Skipping unusable Composio profile {profile.profile_id} for {toolkit_slug}: {e}"
                )

        raise ValueError(
            f"Unable to resolve a usable Composio profile for toolkit '{toolkit_slug}' after trying "
            f"{len(connected_profiles)} connected profile(s)."
        )

    async def get_runtime_profile_candidates(
        self,
        account_id: str,
        toolkit_slug: str,
        preferred_profile_id: Optional[str] = None,
    ) -> List[Tuple[str, str]]:
        """
        Return ordered runtime candidates for a Composio toolkit as:
        [(profile_id, mcp_url), ...]
        Order: preferred profile first (if usable), then remaining connected profiles.
        """
        profiles = await self.get_profiles(account_id, toolkit_slug=toolkit_slug)
        if not profiles:
            raise ValueError(f"No Composio profiles found for toolkit '{toolkit_slug}'")

        connected_profiles = [p for p in profiles if p.is_active and p.mcp_url]
        if not connected_profiles:
            raise ValueError(
                f"No connected Composio profiles with MCP URL for toolkit '{toolkit_slug}'. "
                "Reconnect the integration and try again."
            )

        ordered_profiles: List[ComposioProfile] = []
        if preferred_profile_id:
            preferred = next((p for p in connected_profiles if p.profile_id == preferred_profile_id), None)
            if preferred:
                ordered_profiles.append(preferred)

        for profile in connected_profiles:
            if not any(existing.profile_id == profile.profile_id for existing in ordered_profiles):
                ordered_profiles.append(profile)

        candidates: List[Tuple[str, str]] = []
        errors: List[str] = []

        for profile in ordered_profiles:
            try:
                mcp_url = await self.get_mcp_url_for_runtime(profile.profile_id, account_id=account_id)
                candidates.append((profile.profile_id, mcp_url))
            except Exception as e:
                errors.append(f"{profile.profile_id}: {e}")
                logger.warning(
                    f"Skipping unusable Composio profile {profile.profile_id} for {toolkit_slug}: {e}"
                )

        if candidates:
            return candidates

        raise ValueError(
            f"Unable to resolve a usable Composio profile for toolkit '{toolkit_slug}' after trying "
            f"{len(ordered_profiles)} connected profile(s). Errors: {' | '.join(errors)}"
        )
