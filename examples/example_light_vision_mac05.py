"""
Vision Integration Example - ActionCoordinator

This example demonstrates vision-based UI automation using ActionCoordinator.

## Features
- Set-of-Marks vision for element detection
- OODA loop for adaptive execution
- Automatic error recovery with vision

## Requirements
- macOS with Accessibility permissions
- Vision model (Florence-2)

## Usage
    python examples/example_light_vision_mac05.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Run vision example with ActionCoordinator"""
    
    print("\n" + "=" * 60)
    print("Vision Integration - ActionCoordinator")
    print("=" * 60 + "\n")
    
    try:
        from janus.runtime.core import JanusAgent
        
        agent = JanusAgent(enable_vision=True, enable_llm=True)
        
        print("✅ JanusAgent initialized with vision")
        print("   - Vision Engine: Florence-2 Set-of-Marks")
        print("   - Runtime: ActionCoordinator (OODA)\n")
        
        result = await agent.execute("open Calculator")
        
        if result.success:
            print(f"✅ Success: {result.message}")
        else:
            print(f"❌ Failed: {result.message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
