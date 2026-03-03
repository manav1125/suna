import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4
from cryptography.fernet import Fernet
import os

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
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable is required")
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

    def _row_to_profile(self, row: Dict[str, Any]) -> ComposioProfile:
        config = self._decrypt_config(row['encrypted_config'])
        return ComposioProfile(
            profile_id=row['profile_id'],
            account_id=row['account_id'],
            mcp_qualified_name=row['mcp_qualified_name'],
            profile_name=row['profile_name'],
            display_name=row['display_name'],
            encrypted_config=row['encrypted_config'],
            config_hash=row['config_hash'],
            toolkit_slug=config.get('toolkit_slug', ''),
            toolkit_name=config.get('toolkit_name', ''),
            mcp_url=config.get('mcp_url', ''),
            redirect_url=config.get('redirect_url'),
            connected_account_id=config.get('connected_account_id'),
            is_active=row.get('is_active', True),
            is_default=row.get('is_default', False),
            is_connected=bool(config.get('mcp_url')),
            created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row.get('created_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row.get('updated_at') else None,
        )

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
            
            profile_data = result.data[0]

            config = self._decrypt_config(profile_data['encrypted_config'])
            
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

            profile_data = result.data[0]

            config = self._decrypt_config(profile_data['encrypted_config'])

            if config.get('type') != 'composio':
                raise ValueError(f"Profile {profile_id} is not a Composio profile")

            mcp_url = config.get('mcp_url')
            if not mcp_url:
                raise ValueError(f"Profile {profile_id} has no MCP URL")

            connected_account_id = config.get('connected_account_id')

            # Upgrade legacy user_id-based URLs to connected_account-based URLs for deterministic routing
            if connected_account_id and 'user_id=' in mcp_url and 'connected_account_id=' not in mcp_url:
                from urllib.parse import urlparse
                parsed = urlparse(mcp_url)
                upgraded_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?connected_account_id={connected_account_id}"
                logger.info(f"[MCP URL] Upgraded for profile {profile_id}: {upgraded_url}")
                return upgraded_url

            logger.info(f"[MCP URL] Using stored URL for profile {profile_id}: {mcp_url}")
            return mcp_url

        except Exception as e:
            logger.error(f"Failed to get MCP URL for profile {profile_id}: {e}", exc_info=True)
            raise

    async def get_profile_config(self, profile_id: str, account_id: str) -> Dict[str, Any]:
        try:
            client = await self.db.client

            query = client.table('user_mcp_credential_profiles').select('encrypted_config').eq(
                'profile_id', profile_id
            ).eq('account_id', account_id)

            result = await query.execute()

            if not result.data:
                raise ValueError(f"Profile {profile_id} not found or does not belong to account {account_id}")

            return self._decrypt_config(result.data[0]['encrypted_config'])

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

            return self._row_to_profile(result.data[0])
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
                profiles.append(self._row_to_profile(row))
            
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
