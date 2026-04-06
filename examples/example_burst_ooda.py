#!/usr/bin/env python3
"""
Example: Burst OODA Mode Demo

Demonstrates the Burst OODA pattern with a simple task.

Usage:
    python examples/example_burst_ooda.py

Note: This requires a running Ollama server with a model installed.
"""

import asyncio
import logging
from janus.runtime.core.action_coordinator import ActionCoordinator
from janus.runtime.core.contracts import Intent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_burst_mode():
    """
    Demonstrate burst mode with a simple task.
    
    Task: "Ouvre Safari et va sur YouTube"
    
    Expected burst:
    1. open_app Safari
    2. navigate to youtube.com
    
    This should take only 1 LLM call instead of 2.
    """
    logger.info("=" * 60)
    logger.info("Burst OODA Mode Demo")
    logger.info("=" * 60)
    
    # Create coordinator with burst mode enabled
    coordinator = ActionCoordinator(
        enable_burst_mode=True,
        stagnation_threshold=3,
        max_iterations=10
    )
    
    # Create intent
    intent = Intent(
        action="navigate",
        confidence=1.0,
        raw_command="Ouvre Safari et va sur YouTube"
    )
    
    # Execute goal
    logger.info("\n🚀 Starting execution...")
    logger.info(f"Goal: {intent.raw_command}")
    logger.info(f"Burst Mode: {coordinator.enable_burst_mode}")
    
    try:
        result = await coordinator.execute_goal(
            user_goal=intent.raw_command,
            intent=intent,
            session_id="demo_session",
            request_id="demo_request",
            language="fr"
        )
        
        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("Execution Complete")
        logger.info("=" * 60)
        logger.info(f"Success: {result.success}")
        logger.info(f"Total Actions: {len(result.action_results)}")
        
        # Print burst metrics
        if result.burst_metrics:
            logger.info("\n📊 Burst Metrics:")
            logger.info(f"  LLM Calls: {result.burst_metrics.llm_calls}")
            logger.info(f"  Total Bursts: {result.burst_metrics.total_bursts}")
            logger.info(f"  Actions Executed: {result.burst_metrics.burst_actions_executed}")
            logger.info(f"  Avg Actions/Burst: {result.burst_metrics.avg_actions_per_burst:.2f}")
            logger.info(f"  Vision Calls: {result.burst_metrics.vision_calls}")
            logger.info(f"  Stagnation Events: {result.burst_metrics.stagnation_events}")
            logger.info(f"\n⏱️  Timings:")
            logger.info(f"  LLM Time: {result.burst_metrics.t_llm_ms:.2f}ms")
            logger.info(f"  Observe Time: {result.burst_metrics.t_observe_ms:.2f}ms")
            logger.info(f"  Action Time: {result.burst_metrics.t_act_ms:.2f}ms")
            logger.info(f"  Vision Time: {result.burst_metrics.t_vision_ms:.2f}ms")
            
            total_time = (
                result.burst_metrics.t_llm_ms +
                result.burst_metrics.t_observe_ms +
                result.burst_metrics.t_act_ms +
                result.burst_metrics.t_vision_ms
            )
            logger.info(f"  Total Time: {total_time:.2f}ms ({total_time/1000:.2f}s)")
            
            # Performance analysis
            if result.burst_metrics.llm_calls > 0:
                logger.info(f"\n📈 Performance Analysis:")
                estimated_standard_calls = result.burst_metrics.burst_actions_executed
                reduction = ((estimated_standard_calls - result.burst_metrics.llm_calls) / 
                            estimated_standard_calls * 100)
                logger.info(f"  Estimated Standard Mode LLM Calls: {estimated_standard_calls}")
                logger.info(f"  Actual Burst Mode LLM Calls: {result.burst_metrics.llm_calls}")
                logger.info(f"  Reduction: {reduction:.1f}%")
        
        # Print action history
        logger.info("\n📝 Action History:")
        for i, action_result in enumerate(result.action_results, 1):
            status = "✓" if action_result.success else "✗"
            logger.info(f"  {status} [{i}] {action_result.action_type}: {action_result.message}")
        
    except Exception as e:
        logger.error(f"❌ Execution failed: {e}", exc_info=True)


async def compare_modes():
    """
    Compare burst mode vs standard mode performance.
    
    Note: This is a simulation since we can't easily run both modes
    on the same task without interference.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Mode Comparison (Theoretical)")
    logger.info("=" * 60)
    
    task_examples = [
        {
            "task": "Open Safari → Navigate to YouTube → Search for song",
            "actions": 3,
            "standard_llm_calls": 3,
            "burst_llm_calls": 1,
            "burst_count": 1
        },
        {
            "task": "Open Chrome → Go to GitHub → Find repo → Clone it",
            "actions": 4,
            "standard_llm_calls": 4,
            "burst_llm_calls": 1,
            "burst_count": 1
        },
        {
            "task": "Open Safari → YouTube → Search → Play first → Verify playing",
            "actions": 5,
            "standard_llm_calls": 5,
            "burst_llm_calls": 2,
            "burst_count": 2
        }
    ]
    
    logger.info("\nTask Examples:")
    logger.info("-" * 60)
    
    for example in task_examples:
        logger.info(f"\n📋 {example['task']}")
        logger.info(f"   Actions: {example['actions']}")
        logger.info(f"   Standard Mode: {example['standard_llm_calls']} LLM calls")
        logger.info(f"   Burst Mode: {example['burst_llm_calls']} LLM calls ({example['burst_count']} burst(s))")
        
        reduction = ((example['standard_llm_calls'] - example['burst_llm_calls']) / 
                    example['standard_llm_calls'] * 100)
        logger.info(f"   Reduction: {reduction:.1f}%")
        
        # Estimate time savings (assuming 500ms per LLM call)
        standard_time = example['standard_llm_calls'] * 500
        burst_time = example['burst_llm_calls'] * 500
        time_saved = standard_time - burst_time
        logger.info(f"   Time Saved: ~{time_saved}ms ({time_saved/1000:.2f}s)")


def main():
    """Main entry point"""
    logger.info("Burst OODA Mode Example")
    logger.info("This demonstrates the performance improvements of burst mode.")
    logger.info("")
    logger.info("Note: This requires:")
    logger.info("  1. Running Ollama server")
    logger.info("  2. Installed model (e.g., qwen2.5:7b-instruct)")
    logger.info("  3. macOS (for AppleScript automation)")
    logger.info("")
    
    # Run theoretical comparison first
    asyncio.run(compare_modes())
    
    # Uncomment to run actual demo (requires Ollama + macOS)
    # logger.info("\n" + "=" * 60)
    # logger.info("Running Actual Demo")
    # logger.info("=" * 60)
    # asyncio.run(demo_burst_mode())


if __name__ == "__main__":
    main()
