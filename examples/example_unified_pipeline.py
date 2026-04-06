"""
Example: Unified Pipeline Workflows

Demonstrates the Extract → Process → Output pipeline with practical examples.

This example shows how to:
1. Extract content from web pages with trafilatura
2. Extract text from native applications
3. Process content with LLM
4. Send results to various destinations

Requirements:
- pip install trafilatura (optional, for better web extraction)
- LLM service configured (local or API)
- O365 credentials (for email workflows)
- Slack token (for Slack workflows)
"""

import asyncio
from janus.capabilities.agents.browser_agent import BrowserAgent
from janus.capabilities.agents.llm_agent import LLMAgent
from janus.capabilities.agents.ui_agent import UIAgent
from janus.capabilities.agents.messaging_agent import MessagingAgent
from janus.runtime.core.contracts import ExecutionContext
from janus.memory.email_provider import EmailProvider


async def example_web_to_summary():
    """
    Example 1: Web → LLM → Clipboard
    
    Extract content from a web page, summarize it, and paste to clipboard.
    """
    print("\n" + "="*80)
    print("Example 1: Web → LLM → Clipboard")
    print("="*80)
    
    # Initialize agents
    browser = BrowserAgent(provider="safari")
    llm = LLMAgent(provider="local")
    ui = UIAgent()
    
    # Create execution context for chaining
    context = ExecutionContext(
        active_app="Safari",
        surface="browser",
        url="https://example.com"
    )
    
    try:
        # Step 1: Extract web content
        print("\n📄 Step 1: Extracting web page content...")
        result = await browser.execute("get_page_content", {}, context.get_current_context())
        
        if result["status"] == "success":
            content = result.get("data", {})
            if isinstance(content, dict):
                text = content.get("content", str(content))
            else:
                text = str(content)
            
            print(f"✅ Extracted {len(text)} characters")
            context.store_output(text, "web_content")
            
            # Step 2: Summarize with LLM
            print("\n🤖 Step 2: Summarizing content with LLM...")
            
            # Resolve input_from reference
            args = context.resolve_args({"input_from": "web_content"})
            summary_result = await llm.execute(
                "summarize",
                {"text": args.get("input", text), "max_length": 200},
                {}
            )
            
            if summary_result["status"] == "success":
                summary = summary_result["data"]["summary"]
                print(f"✅ Summary: {summary[:100]}...")
                context.store_output(summary, "summary")
                
                # Step 3: Paste to clipboard
                print("\n📋 Step 3: Pasting to clipboard...")
                paste_result = await ui.execute("paste", {}, {})
                
                if paste_result["status"] == "success":
                    print("✅ Workflow completed successfully!")
                else:
                    print(f"❌ Paste failed: {paste_result.get('error')}")
            else:
                print(f"❌ Summarization failed: {summary_result.get('error')}")
        else:
            print(f"❌ Content extraction failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_app_to_summary():
    """
    Example 2: Native App → LLM → Clipboard
    
    Extract text from active application window, summarize, and paste.
    """
    print("\n" + "="*80)
    print("Example 2: Native App → LLM → Clipboard")
    print("="*80)
    
    # Initialize agents
    ui = UIAgent()
    llm = LLMAgent(provider="local")
    
    context = ExecutionContext(active_app="Notes")
    
    try:
        # Step 1: Extract text from app
        print("\n📱 Step 1: Extracting text from active app...")
        result = await ui.execute("extract_text", {}, context.get_current_context())
        
        if result["status"] == "success":
            text = result["data"]["text"]
            app_name = result["data"].get("app", "Unknown")
            
            print(f"✅ Extracted {len(text)} characters from {app_name}")
            context.store_output(text, "app_text")
            
            # Step 2: Summarize
            print("\n🤖 Step 2: Summarizing text...")
            args = context.resolve_args({"input_from": "app_text"})
            summary_result = await llm.execute(
                "summarize",
                {"text": args.get("input", text), "max_length": 150},
                {}
            )
            
            if summary_result["status"] == "success":
                summary = summary_result["data"]["summary"]
                print(f"✅ Summary: {summary[:100]}...")
                
                # Step 3: Paste
                print("\n📋 Step 3: Pasting summary...")
                paste_result = await ui.execute("paste", {}, {})
                
                if paste_result["status"] == "success":
                    print("✅ Workflow completed successfully!")
                else:
                    print(f"❌ Paste failed: {paste_result.get('error')}")
            else:
                print(f"❌ Summarization failed: {summary_result.get('error')}")
        else:
            print(f"❌ Text extraction failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_teams_to_email():
    """
    Example 3: Teams → LLM → Email
    
    Summarize Teams conversation and send via email.
    
    Note: Requires Teams and O365 authentication configured.
    """
    print("\n" + "="*80)
    print("Example 3: Teams → LLM → Email")
    print("="*80)
    
    # Check if credentials are configured
    import os
    if not os.environ.get("TEAMS_CLIENT_ID"):
        print("⚠️  Teams credentials not configured. Set TEAMS_CLIENT_ID, TEAMS_CLIENT_SECRET, TEAMS_TENANT_ID")
        return
    
    if not os.environ.get("O365_CLIENT_ID"):
        print("⚠️  O365 credentials not configured. Set O365_CLIENT_ID, O365_CLIENT_SECRET")
        return
    
    # Initialize agents
    messaging = MessagingAgent(provider="teams")
    email_provider = EmailProvider()
    
    context = ExecutionContext()
    
    try:
        # Step 1: Summarize Teams thread
        print("\n💬 Step 1: Summarizing Teams conversation...")
        result = await messaging.execute(
            "summarize_thread",
            {
                "platform": "teams",
                "channel": "general",
                "team_id": "YOUR_TEAM_ID",  # Replace with actual team ID
                "limit": 50
            },
            {}
        )
        
        if result["status"] == "success":
            summary = result["data"]["summary"]
            message_count = result["data"]["message_count"]
            
            print(f"✅ Summarized {message_count} messages")
            print(f"   Summary: {summary[:100]}...")
            context.store_output(summary, "teams_summary")
            
            # Step 2: Send email
            print("\n📧 Step 2: Sending summary via email...")
            
            args = context.resolve_args({"input_from": "teams_summary"})
            email_sent = email_provider.send_email(
                to="manager@example.com",  # Replace with actual email
                subject="Teams Discussion Summary",
                body=args.get("input", summary)
            )
            
            if email_sent:
                print("✅ Email sent successfully!")
            else:
                print("❌ Email sending failed")
        else:
            print(f"❌ Teams summarization failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_email_to_slack():
    """
    Example 4: Email → LLM → Slack
    
    Fetch recent emails, summarize, and post to Slack.
    
    Note: Requires O365 and Slack credentials configured.
    """
    print("\n" + "="*80)
    print("Example 4: Email → LLM → Slack")
    print("="*80)
    
    # Check credentials
    import os
    if not os.environ.get("O365_CLIENT_ID"):
        print("⚠️  O365 credentials not configured")
        return
    
    if not os.environ.get("SLACK_BOT_TOKEN"):
        print("⚠️  Slack credentials not configured. Set SLACK_BOT_TOKEN")
        return
    
    # Initialize
    email_provider = EmailProvider()
    llm = LLMAgent(provider="local")
    messaging = MessagingAgent(provider="slack")
    
    context = ExecutionContext()
    
    try:
        # Step 1: Fetch recent emails
        print("\n📨 Step 1: Fetching recent emails...")
        email_provider.enable()
        
        emails = email_provider.get_recent_emails(limit=5)
        
        if emails:
            print(f"✅ Fetched {len(emails)} emails")
            
            # Format emails for summarization
            email_text = "\n\n".join([
                f"From: {e['sender']}\nSubject: {e['subject']}\n{e['body'][:200]}"
                for e in emails
            ])
            
            context.store_output(email_text, "emails")
            
            # Step 2: Summarize
            print("\n🤖 Step 2: Summarizing emails...")
            args = context.resolve_args({"input_from": "emails"})
            summary_result = await llm.execute(
                "summarize",
                {"text": args.get("input", email_text), "max_length": 250},
                {}
            )
            
            if summary_result["status"] == "success":
                summary = summary_result["data"]["summary"]
                print(f"✅ Summary: {summary[:100]}...")
                context.store_output(summary, "email_summary")
                
                # Step 3: Post to Slack
                print("\n💬 Step 3: Posting to Slack...")
                args = context.resolve_args({"input_from": "email_summary"})
                
                post_result = await messaging.execute(
                    "post_message",
                    {
                        "platform": "slack",
                        "channel": "#general",  # Replace with actual channel
                        "text": args.get("input", summary)
                    },
                    {}
                )
                
                if post_result["status"] == "success":
                    print("✅ Posted to Slack successfully!")
                else:
                    print(f"❌ Slack posting failed: {post_result.get('error')}")
            else:
                print(f"❌ Summarization failed: {summary_result.get('error')}")
        else:
            print("⚠️  No emails found")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all examples."""
    print("=" * 80)
    print("Unified Pipeline Workflow Examples")
    print("=" * 80)
    
    # Run examples
    await example_web_to_summary()
    await example_app_to_summary()
    await example_teams_to_email()
    await example_email_to_slack()
    
    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
