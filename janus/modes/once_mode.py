"""Once mode - Execute a single command and exit"""
import logging

from janus.logging.colored_console import (
    print_action,
    print_banner,
    print_command,
    print_error,
    print_separator,
    print_success,
    setup_colored_logging,
)

logger = logging.getLogger(__name__)


async def run_once_mode(pipeline, command: str):
    """Execute a single command and exit
    
    TICKET-330: Warmup is now called to avoid 1-minute delay on first command.
    """
    setup_colored_logging(logging.INFO)
    
    logger.info(f"Executing single command: {command}")
    
    print_banner("Janus Single Command Mode", f"Session: {pipeline.session_id[:8]}")
    
    # TICKET-330: Warmup LLM before first command to avoid 60s+ delay
    logger.info("Warming up LLM model (this may take a few seconds on first run)...")
    try:
        await pipeline.warmup_systems()
        logger.info("✓ LLM model ready")
    except Exception as e:
        logger.warning(f"Warmup warning: {e} - continuing anyway")
    
    print_command(command)
    print_separator()
    
    try:
        result = await pipeline.process_command_async(command, conversation_mode=False)
        
        if result.success:
            print_success("Command executed successfully")
            if getattr(result, "action_results", None):
                for action_result in result.action_results:
                    print_action(action_result.to_dict())
            return 0
        else:
            print_error(f"Command failed: {result.message}")
            return 1
            
    except Exception as e:
        logger.exception(f"Error executing command: {e}")
        print_error(f"Error: {e}")
        return 1
