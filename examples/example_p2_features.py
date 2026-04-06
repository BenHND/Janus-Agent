"""
Example: Using P2 Features (Dry-Run, Rollback, Rate Limiting, Offline Mode)

This example demonstrates how to use the new P2 features for safer,
more resilient automation.

Features:
1. Dry-Run Mode: Preview actions without executing them
2. Rate Limiting: Prevent overload on external providers
3. Offline Mode: Queue actions when services are unavailable
4. Rollback: Undo destructive actions (future)

Requirements:
- Janus configured with P2 features enabled in config.ini
"""

import asyncio
import logging
from datetime import datetime

from janus.runtime.core import Settings
from janus.safety.rate_limiter import RateLimiter
from janus.safety.safe_queue import SafeQueue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Dry-Run Mode - Preview Actions Without Executing
# ============================================================================

async def example_dry_run():
    """Example: Use dry-run mode to preview actions"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Dry-Run Mode - Preview Without Executing")
    print("="*80 + "\n")
    
    # Note: This example shows the API. Full agent integration is in progress.
    from janus.capabilities.agents.system_agent import SystemAgent
    
    agent = SystemAgent()
    
    # Execute action in dry-run mode (preview only)
    try:
        result = await agent.execute(
            action="open_application",
            args={"app_name": "Calculator"},
            context={},
            dry_run=True  # Preview mode - no side effects
        )
        
        print(f"Dry-run result: {result}")
        print("✓ Action previewed successfully - no actual execution occurred")
        
    except TypeError as e:
        if "dry_run" in str(e):
            print("⚠ Agent doesn't fully support dry_run yet (implementation in progress)")
            print("  This feature will be available once all agents are updated")
        else:
            raise


# ============================================================================
# Example 2: Rate Limiting - Prevent Overload on External Providers
# ============================================================================

def example_rate_limiting():
    """Example: Configure and use rate limiting"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Rate Limiting - Prevent Overload")
    print("="*80 + "\n")
    
    # Initialize rate limiter
    limiter = RateLimiter()
    
    # Configure rate limits
    # Global: 100 requests per minute
    limiter.configure("global", max_requests=100, time_window_seconds=60)
    
    # Email: 10 per minute (to avoid SMTP throttling)
    limiter.configure("email", max_requests=10, time_window_seconds=60, burst_allowance=3)
    
    # Slack: 20 per minute (respects Slack API limits)
    limiter.configure("slack", max_requests=20, time_window_seconds=60)
    
    print("✓ Rate limits configured:")
    print("  - Global: 100 req/min")
    print("  - Email: 10 req/min (+ 3 burst)")
    print("  - Slack: 20 req/min\n")
    
    # Simulate sending emails
    print("Simulating email sending...")
    sent_count = 0
    rejected_count = 0
    
    for i in range(15):
        # Check both global and email rate limits
        if limiter.check_and_consume("global") and limiter.check_and_consume("email"):
            sent_count += 1
            print(f"  ✓ Email {i+1}: Sent (global: {limiter.get_remaining('global'):.1f}, "
                  f"email: {limiter.get_remaining('email'):.1f} remaining)")
        else:
            rejected_count += 1
            print(f"  ✗ Email {i+1}: Rate limit exceeded - queued for later")
    
    print(f"\n✓ Results: {sent_count} sent, {rejected_count} rate-limited\n")
    
    # View statistics
    stats = limiter.get_stats("email", hours=1)
    print(f"Email rate limit stats:")
    print(f"  - Total events: {stats['total_events']}")
    print(f"  - Exceeded count: {stats['exceeded_count']}")
    print(f"  - Current tokens: {stats['current_tokens']:.1f}")


# ============================================================================
# Example 3: Offline Mode - Queue Actions When Services Unavailable
# ============================================================================

def example_offline_queue():
    """Example: Use SafeQueue for offline action queueing"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Offline Mode - Queue Actions")
    print("="*80 + "\n")
    
    # Initialize queue
    queue = SafeQueue()
    
    # Simulate service being offline - queue actions for later
    print("Scenario: Email service is offline, queueing actions...\n")
    
    # Queue several email actions
    for i in range(3):
        action_id = queue.enqueue(
            action_type="email.send",
            action_data={
                "to": f"user{i}@example.com",
                "subject": f"Report {i+1}",
                "body": f"This is automated report {i+1}"
            },
            priority=1,
            max_retries=3,
            expires_in_hours=24
        )
        print(f"  ✓ Queued email {i+1} (ID: {action_id})")
    
    print(f"\n✓ {queue.get_pending_count()} actions queued for processing\n")
    
    # Register processor (simulates service coming back online)
    print("Scenario: Service is back online, processing queue...\n")
    
    def send_email(data):
        """Simulated email sending"""
        print(f"  → Sending email to {data['to']}: {data['subject']}")
        # Simulate success
        return True
    
    queue.register_processor("email.send", send_email)
    
    # Process queued actions
    stats = queue.process_pending()
    
    print(f"\n✓ Queue processing complete:")
    print(f"  - Processed: {stats['processed']}")
    print(f"  - Succeeded: {stats['succeeded']}")
    print(f"  - Failed: {stats['failed']}")
    
    # View queue statistics
    queue_stats = queue.get_stats()
    print(f"\n✓ Queue statistics:")
    print(f"  - Pending: {queue_stats['pending']}")
    print(f"  - Completed: {queue_stats['completed']}")
    print(f"  - Failed: {queue_stats['failed']}")


# ============================================================================
# Example 4: Combined Usage - Real-World Scenario
# ============================================================================

def example_combined_usage():
    """Example: Combine rate limiting and offline queue"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Combined Usage - Rate Limiting + Offline Queue")
    print("="*80 + "\n")
    
    limiter = RateLimiter()
    queue = SafeQueue()
    
    # Configure rate limits
    limiter.configure("slack", max_requests=5, time_window_seconds=10)
    
    print("Scenario: Sending 10 Slack messages with 5/10s rate limit...\n")
    
    # Register processor for queued messages
    def send_slack_message(data):
        print(f"  → Sending: {data['message']}")
        return True
    
    queue.register_processor("slack.send", send_slack_message)
    
    sent_immediately = 0
    queued = 0
    
    # Try to send 10 messages
    for i in range(10):
        if limiter.check_and_consume("slack"):
            # Rate limit allows - send immediately
            print(f"  ✓ Message {i+1}: Sent immediately (remaining: {limiter.get_remaining('slack'):.1f})")
            sent_immediately += 1
        else:
            # Rate limit exceeded - queue for later
            queue.enqueue(
                action_type="slack.send",
                action_data={"message": f"Queued message {i+1}"},
                priority=1,
                delay_seconds=5  # Wait 5 seconds before retry
            )
            print(f"  ⏱ Message {i+1}: Rate limited - queued for delayed send")
            queued += 1
    
    print(f"\n✓ Immediate results: {sent_immediately} sent, {queued} queued")
    print(f"  Queued messages will be processed automatically after delay\n")


# ============================================================================
# Example 5: Configuration from Settings
# ============================================================================

def example_settings():
    """Example: Load P2 settings from config.ini"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Load P2 Settings from config.ini")
    print("="*80 + "\n")
    
    # Load settings
    settings = Settings()
    
    # Check feature flags
    print("Feature flags:")
    print(f"  - Dry-run enabled: {settings.features.enable_dry_run}")
    print(f"  - Rollback enabled: {settings.features.enable_rollback}")
    print(f"  - Rate limiting enabled: {settings.features.enable_rate_limiting}")
    print(f"  - Offline mode enabled: {settings.features.enable_offline_mode}")
    
    # Rate limit settings
    print("\nRate limit settings:")
    print(f"  - Global: {settings.rate_limit.global_max_requests} req/{settings.rate_limit.global_time_window_seconds}s")
    print(f"  - Email: {settings.rate_limit.email_max_requests} req/{settings.rate_limit.email_time_window_seconds}s")
    print(f"  - Slack: {settings.rate_limit.slack_max_requests} req/{settings.rate_limit.slack_time_window_seconds}s")
    
    # Offline settings
    print("\nOffline mode settings:")
    print(f"  - Queue enabled: {settings.offline.queue_enabled}")
    print(f"  - Max queue size: {settings.offline.max_queue_size}")
    print(f"  - Default max retries: {settings.offline.default_max_retries}")
    print(f"  - Default expiration: {settings.offline.default_expiration_hours}h")
    
    print("\n✓ Settings loaded successfully from config.ini")


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("P2 FEATURES EXAMPLES")
    print("="*80)
    print("\nDemonstrating: Dry-Run, Rate Limiting, and Offline Mode")
    print("These features provide safer, more resilient automation\n")
    
    # Run sync examples
    example_rate_limiting()
    example_offline_queue()
    example_combined_usage()
    example_settings()
    
    # Run async example
    print("\n" + "="*80)
    asyncio.run(example_dry_run())
    
    print("\n" + "="*80)
    print("ALL EXAMPLES COMPLETE")
    print("="*80 + "\n")
    
    print("Next steps:")
    print("1. Enable features in config.ini (already configured)")
    print("2. Integrate rate limiting into ActionCoordinator")
    print("3. Implement dry-run mode in all agents")
    print("4. Add rollback/compensation handlers")
    print("5. Connect queue to automatic service health checking")
    print("\nFor more info, see:")
    print("  - janus/safety/rate_limiter.py")
    print("  - janus/safety/safe_queue.py")
    print("  - tests/test_rate_limiter.py")
    print("  - tests/test_safe_queue.py")
    print("  - tests/test_dry_run_mode.py\n")


if __name__ == "__main__":
    main()
