#!/usr/bin/env python3
"""
Example: Using JanusAgent - Single Entry Point

TICKET-AUDIT-003: This demonstrates the new unified API for Janus.
All functionality is accessed through a single JanusAgent class.

Usage:
    python examples/example_janus_agent.py
"""

import asyncio
import logging

from janus.runtime.core import JanusAgent, execute_command

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_basic_usage():
    """Example 1: Basic usage with context manager"""
    print("\n=== Example 1: Basic Usage ===")
    
    async with JanusAgent() as agent:
        print(f"Agent initialized: {agent}")
        print(f"Agent available: {agent.available}")
        
        # Execute a simple command
        result = await agent.execute("open Calculator")
        
        if result.success:
            print(f"✓ Success: {result.message}")
        else:
            print(f"✗ Failed: {result.message}")


async def example_custom_config():
    """Example 2: Custom configuration"""
    print("\n=== Example 2: Custom Configuration ===")
    
    # Initialize with specific features
    agent = JanusAgent(
        enable_voice=False,      # Text-only mode
        enable_llm=True,         # Use LLM for reasoning
        enable_vision=False,     # Disable vision for speed
        enable_learning=False,   # Disable learning
        enable_tts=False,        # No speech output
    )
    
    try:
        print(f"Agent: {agent}")
        
        # Execute command
        result = await agent.execute("open Safari and go to example.com")
        
        if result.success:
            print(f"✓ Success: {result.message}")
            print(f"  Duration: {result.total_duration_ms}ms")
        else:
            print(f"✗ Failed: {result.message}")
    
    finally:
        await agent.cleanup()


async def example_multiple_commands():
    """Example 3: Multiple commands in one session"""
    print("\n=== Example 3: Multiple Commands ===")
    
    async with JanusAgent() as agent:
        commands = [
            "open TextEdit",
            "write 'Hello from Janus'",
            "save as test.txt",
        ]
        
        for i, command in enumerate(commands, 1):
            print(f"\n[{i}/{len(commands)}] Executing: {command}")
            result = await agent.execute(command)
            
            if result.success:
                print(f"  ✓ {result.message}")
            else:
                print(f"  ✗ {result.message}")
                break  # Stop on first failure


async def example_with_context():
    """Example 4: Command with additional context"""
    print("\n=== Example 4: With Context ===")
    
    async with JanusAgent() as agent:
        # Execute with extra context
        result = await agent.execute(
            "send email",
            extra_context={
                "recipient": "user@example.com",
                "subject": "Test Email",
                "body": "This is a test email from Janus"
            }
        )
        
        if result.success:
            print(f"✓ Success: {result.message}")
        else:
            print(f"✗ Failed: {result.message}")


async def example_one_shot():
    """Example 5: One-shot execution"""
    print("\n=== Example 5: One-Shot Execution ===")
    
    # Execute a single command without managing agent lifecycle
    result = await execute_command(
        "open Calculator",
        enable_voice=False,
        enable_vision=False
    )
    
    print(f"Result: {'✓ Success' if result.success else '✗ Failed'}")
    print(f"Message: {result.message}")


async def example_error_handling():
    """Example 6: Error handling"""
    print("\n=== Example 6: Error Handling ===")
    
    async with JanusAgent() as agent:
        try:
            # Try an invalid command
            result = await agent.execute("")
        except ValueError as e:
            print(f"✓ Caught expected error: {e}")
        
        try:
            # Try a command that might fail
            result = await agent.execute("open NonExistentApp123")
            
            if not result.success:
                print(f"Command failed (expected): {result.message}")
        except Exception as e:
            print(f"Exception during execution: {e}")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("JanusAgent Examples - TICKET-AUDIT-003")
    print("=" * 60)
    
    examples = [
        example_basic_usage,
        example_custom_config,
        example_multiple_commands,
        example_with_context,
        example_one_shot,
        example_error_handling,
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            logger.error(f"Error in {example.__name__}: {e}", exc_info=True)
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
