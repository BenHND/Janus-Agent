"""
Vision-to-Action Mapping (VAM) Example - ActionCoordinator

This example demonstrates vision-based UI interaction using ActionCoordinator (OODA loop).

## Features
- Vision-based element detection via Set-of-Marks
- ActionCoordinator OODA loop execution
- Automatic retry and error recovery

## Requirements
- macOS with Accessibility permissions
- Supported browser (Safari, Chrome, Edge, Firefox)
- Vision model (Florence-2 recommended)

## Usage
    python examples/example_vam_end_to_end.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Run VAM example using ActionCoordinator"""
    
    print("\n" + "=" * 60)
    print("Vision-to-Action Mapping - ActionCoordinator (OODA)")
    print("=" * 60 + "\n")
    
    try:
        from janus.runtime.core import JanusAgent
        
        # Initialize with vision enabled
        agent = JanusAgent(
            enable_vision=True,
            enable_llm=True,
        )
        
        print("✅ JanusAgent initialized")
        print("   - Vision: Enabled (Florence-2 Set-of-Marks)")
        print("   - Runtime: ActionCoordinator (OODA)")
        print("\nExample: Vision-based button click")
        print("Command: 'click on the Submit button'")
        
        # Example vision-based command
        result = await agent.execute("open Safari and go to example.com")
        
        if result.success:
            print(f"\n✅ Success: {result.message}")
        else:
            print(f"\n❌ Failed: {result.message}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
