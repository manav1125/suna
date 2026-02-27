from typing import Optional

from daytona_sdk import (
    AsyncDaytona,
    DaytonaConfig,
    CreateSandboxFromSnapshotParams,
    CreateSandboxFromImageParams,
    AsyncSandbox,
    SessionExecuteRequest,
    Resources,
    SandboxState,
    DaytonaError,
)
from dotenv import load_dotenv
from core.utils.logger import logger
from core.utils.config import config
from core.utils.config import Configuration
import asyncio

load_dotenv()

# logger.debug("Initializing Daytona sandbox configuration")
daytona_config = DaytonaConfig(
    api_key=config.DAYTONA_API_KEY,
    api_url=config.DAYTONA_SERVER_URL, 
    target=config.DAYTONA_TARGET,
)

if daytona_config.api_key:
    logger.debug("Daytona sandbox configured successfully")
else:
    logger.warning("No Daytona API key found in environment variables")

if daytona_config.api_url:
    logger.debug(f"Daytona API URL set to: {daytona_config.api_url}")
else:
    logger.warning("No Daytona API URL found in environment variables")

if daytona_config.target:
    logger.debug(f"Daytona target set to: {daytona_config.target}")
else:
    logger.warning("No Daytona target found in environment variables")

daytona: Optional[AsyncDaytona] = None
if daytona_config.api_key:
    daytona = AsyncDaytona(daytona_config)


def _get_daytona() -> AsyncDaytona:
    """
    Return configured Daytona client or raise a clear runtime error.

    This avoids crashing API boot for self-hosted deployments that do not
    provide Daytona credentials.
    """
    if daytona is None:
        raise RuntimeError(
            "Daytona is not configured. Set DAYTONA_API_KEY (and optional "
            "DAYTONA_SERVER_URL/DAYTONA_TARGET) to enable sandbox features."
        )
    return daytona

async def get_or_start_sandbox(sandbox_id: str) -> AsyncSandbox:
    """Retrieve a sandbox by ID, check its state, and start it if needed."""
    
    logger.info(f"Getting or starting sandbox with ID: {sandbox_id}")

    try:
        client = _get_daytona()
        sandbox = await client.get(sandbox_id)
        
        # Check if sandbox needs to be started
        if sandbox.state in [SandboxState.ARCHIVED, SandboxState.STOPPED, SandboxState.ARCHIVING]:
            logger.info(f"Sandbox is in {sandbox.state} state. Starting...")
            try:
                await client.start(sandbox)
                
                # Wait for sandbox to reach STARTED state
                for _ in range(30):
                    await asyncio.sleep(1)
                    sandbox = await client.get(sandbox_id)
                    if sandbox.state == SandboxState.STARTED:
                        break
                
                # Start supervisord in a session when restarting
                await start_supervisord_session(sandbox)
            except Exception as e:
                logger.error(f"Error starting sandbox: {e}")
                raise e
        
        logger.info(f"Sandbox {sandbox_id} is ready")
        return sandbox
        
    except Exception as e:
        logger.error(f"Error retrieving or starting sandbox: {str(e)}")
        raise e

async def start_supervisord_session(sandbox: AsyncSandbox):
    """Start supervisord in a session."""
    session_id = "supervisord-session"
    try:
        await sandbox.process.create_session(session_id)
        await sandbox.process.execute_session_command(session_id, SessionExecuteRequest(
            command="exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf",
            var_async=True
        ))
        logger.info("Supervisord started successfully")
    except Exception as e:
        # Don't fail if supervisord already running
        logger.warning(f"Could not start supervisord: {str(e)}")

async def create_sandbox(password: str, project_id: str = None) -> AsyncSandbox:
    """Create a new sandbox with all required services configured and running."""
    
    logger.info("Creating new Daytona sandbox environment")
    # logger.debug("Configuring sandbox with snapshot and environment variables")
    
    labels = None
    if project_id:
        # logger.debug(f"Using sandbox_id as label: {project_id}")
        labels = {'id': project_id}
        
    common_kwargs = dict(
        public=True,
        labels=labels,
        env_vars={
            "CHROME_PERSISTENT_SESSION": "true",
            "RESOLUTION": "1048x768x24",
            "RESOLUTION_WIDTH": "1048",
            "RESOLUTION_HEIGHT": "768",
            "VNC_PASSWORD": password,
            "ANONYMIZED_TELEMETRY": "false",
            "CHROME_PATH": "",
            "CHROME_USER_DATA": "",
            "CHROME_DEBUGGING_PORT": "9222",
            "CHROME_DEBUGGING_HOST": "localhost",
            "CHROME_CDP": ""
        },
        # resources=Resources(
        #     cpu=2,
        #     memory=4,
        #     disk=5,
        # ),
        auto_stop_interval=15,
        auto_archive_interval=30,
    )

    snapshot_params = CreateSandboxFromSnapshotParams(
        snapshot=Configuration.SANDBOX_SNAPSHOT_NAME,
        **common_kwargs,
    )

    image_params = CreateSandboxFromImageParams(
        image=Configuration.SANDBOX_IMAGE_NAME,
        **common_kwargs,
    )

    # Create the sandbox
    client = _get_daytona()
    try:
        sandbox = await client.create(snapshot_params)
    except DaytonaError as e:
        error_text = str(e).lower()
        if (
            "snapshot" in error_text and "not found" in error_text
        ) or (
            "snapshot" in error_text and "doesn't exist" in error_text
        ):
            logger.warning(
                "Snapshot '%s' not found. Falling back to image '%s'.",
                Configuration.SANDBOX_SNAPSHOT_NAME,
                Configuration.SANDBOX_IMAGE_NAME,
            )
            sandbox = await client.create(image_params)
        else:
            raise
    logger.info(f"Sandbox created with ID: {sandbox.id}")
    
    # Start supervisord in a session for new sandbox
    await start_supervisord_session(sandbox)
    
    logger.info(f"Sandbox environment successfully initialized")
    return sandbox

async def delete_sandbox(sandbox_id: str) -> bool:
    """Delete a sandbox by its ID."""
    logger.info(f"Deleting sandbox with ID: {sandbox_id}")

    try:
        # Get the sandbox
        client = _get_daytona()
        sandbox = await client.get(sandbox_id)
        
        # Delete the sandbox
        await client.delete(sandbox)
        
        logger.info(f"Successfully deleted sandbox {sandbox_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting sandbox {sandbox_id}: {str(e)}")
        raise e
