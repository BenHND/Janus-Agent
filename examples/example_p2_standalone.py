"""
Standalone Example: P2 Features (Rate Limiting and Offline Queue)

This is a minimal standalone example that demonstrates rate limiting
and offline queue features without requiring the full Janus installation.

Run with: python example_p2_standalone.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from janus.safety.rate_limiter import RateLimiter
from janus.safety.safe_queue import SafeQueue


def example_rate_limiting():
    """Example: Configure and use rate limiting"""
    print("\n" + "="*80)
    print("RATE LIMITING EXAMPLE")
    print("="*80 + "\n")
    
    # Initialize rate limiter
    limiter = RateLimiter(db_path="/tmp/test_rate_limiter.db")
    
    # Configure rate limits
    limiter.configure("email", max_requests=10, time_window_seconds=60, burst_allowance=3)
    
    print("✓ Rate limit configured: 10 emails/minute (+ 3 burst)\n")
    
    # Simulate sending emails
    print("Simulating email sending...")
    sent_count = 0
    rejected_count = 0
    
    for i in range(15):
        if limiter.check_and_consume("email"):
            sent_count += 1
            remaining = limiter.get_remaining("email")
            print(f"  ✓ Email {i+1}: Sent ({remaining:.1f} tokens remaining)")
        else:
            rejected_count += 1
            print(f"  ✗ Email {i+1}: Rate limit exceeded - queued for later")
    
    print(f"\n✓ Results: {sent_count} sent, {rejected_count} rate-limited")
    
    # View statistics
    stats = limiter.get_stats("email", hours=1)
    print(f"\nEmail rate limit stats:")
    print(f"  - Total events: {stats['total_events']}")
    print(f"  - Exceeded count: {stats['exceeded_count']}")
    print(f"  - Current tokens: {stats['current_tokens']:.1f}")


def example_offline_queue():
    """Example: Use SafeQueue for offline action queueing"""
    print("\n" + "="*80)
    print("OFFLINE QUEUE EXAMPLE")
    print("="*80 + "\n")
    
    # Initialize queue
    queue = SafeQueue(db_path="/tmp/test_queue.db")
    
    # Simulate service being offline - queue actions for later
    print("Scenario: Service is offline, queueing actions...\n")
    
    # Queue several actions
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
        print(f"  ✓ Queued action {i+1} (ID: {action_id})")
    
    print(f"\n✓ {queue.get_pending_count()} actions queued for processing\n")
    
    # Register processor (simulates service coming back online)
    print("Scenario: Service is back online, processing queue...\n")
    
    def send_email(data):
        """Simulated email sending"""
        print(f"  → Sending email to {data['to']}: {data['subject']}")
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
    print(f"\nQueue statistics:")
    print(f"  - Pending: {queue_stats['pending']}")
    print(f"  - Completed: {queue_stats['completed']}")


def example_combined():
    """Example: Combine rate limiting and offline queue"""
    print("\n" + "="*80)
    print("COMBINED EXAMPLE: Rate Limiting + Offline Queue")
    print("="*80 + "\n")
    
    limiter = RateLimiter(db_path="/tmp/test_combined_limiter.db")
    queue = SafeQueue(db_path="/tmp/test_combined_queue.db")
    
    # Configure rate limits
    limiter.configure("slack", max_requests=5, time_window_seconds=10)
    
    print("Scenario: Sending 10 messages with 5/10s rate limit...\n")
    
    # Register processor for queued messages
    def send_message(data):
        print(f"  → Sending: {data['message']}")
        return True
    
    queue.register_processor("slack.send", send_message)
    
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
                delay_seconds=2  # Wait 2 seconds before retry
            )
            print(f"  ⏱ Message {i+1}: Rate limited - queued")
            queued += 1
    
    print(f"\n✓ Immediate results: {sent_immediately} sent, {queued} queued")
    print(f"\nQueued messages can be processed later with queue.process_pending()")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("P2 FEATURES: RATE LIMITING AND OFFLINE QUEUE")
    print("="*80)
    
    try:
        example_rate_limiting()
        example_offline_queue()
        example_combined()
        
        print("\n" + "="*80)
        print("ALL EXAMPLES COMPLETE")
        print("="*80 + "\n")
        
        print("Key features demonstrated:")
        print("  ✓ Rate limiting with token bucket algorithm")
        print("  ✓ Persistent rate limit state (survives restarts)")
        print("  ✓ Offline action queueing with SQLite")
        print("  ✓ Automatic retry with exponential backoff")
        print("  ✓ Combined usage for resilient automation")
        
        print("\nFor more info, see:")
        print("  - janus/safety/rate_limiter.py")
        print("  - janus/safety/safe_queue.py")
        print("  - tests/test_rate_limiter.py")
        print("  - tests/test_safe_queue.py\n")
        
    finally:
        # Cleanup temp databases
        import os
        for db in ["/tmp/test_rate_limiter.db", "/tmp/test_queue.db", 
                   "/tmp/test_combined_limiter.db", "/tmp/test_combined_queue.db"]:
            if os.path.exists(db):
                os.unlink(db)


if __name__ == "__main__":
    main()
