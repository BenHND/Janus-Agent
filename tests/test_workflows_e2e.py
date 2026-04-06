"""
E2E Workflow Tests - Unified Extract → Process → Output Pipeline

TICKET-P1-E2E: Complete pipeline validation for Extract→Process→Output

Tests the complete pipeline for extracting data from various sources,
processing it with LLM, and sending to different destinations.

Workflows tested:
1. Web → LLM → Clipboard: Extract web content, summarize, paste
2. Teams → LLM → Email: Summarize Teams conversation, send via email
3. App → LLM → Clipboard: Extract text from native app, summarize, paste
4. Email → LLM → Messaging: Summarize emails, post to Slack/Teams

NOTE: These tests are designed to validate the pipeline integration.
They use mocks where external services are required.
"""

import asyncio
import pytest
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from janus.capabilities.agents.browser_agent import BrowserAgent
from janus.capabilities.agents.messaging_agent import MessagingAgent
from janus.capabilities.agents.llm_agent import LLMAgent
from janus.capabilities.agents.ui_agent import UIAgent
from janus.capabilities.agents.email_agent import EmailAgent
from janus.runtime.core.contracts import ExecutionContext
from janus.memory.email_provider import EmailProvider


# ============================================================================
# Mock Setup
# ============================================================================

@pytest.fixture
def mock_system_bridge():
    """Mock SystemBridge for testing."""
    mock_bridge = MagicMock()
    mock_bridge.is_available.return_value = True
    mock_bridge.get_platform_name.return_value = "macOS"
    
    # Mock active window
    mock_window = MagicMock()
    mock_window.app_name = "Safari"
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.data = {"window": mock_window}
    mock_bridge.get_active_window.return_value = mock_result
    
    # Mock script execution
    script_result = MagicMock()
    script_result.success = True
    script_result.data = {"stdout": "Sample page content"}
    mock_bridge.run_script.return_value = script_result
    
    return mock_bridge


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing."""
    mock_service = MagicMock()
    mock_service.is_available.return_value = True
    
    async def mock_generate_async(prompt, max_tokens=150, temperature=0.3):
        return {
            "success": True,
            "content": "This is a test summary of the content."
        }
    
    mock_service.generate_async = mock_generate_async
    return mock_service


@pytest.fixture
def execution_context():
    """Create execution context for testing."""
    return ExecutionContext(
        active_app="Safari",
        surface="browser",
        url="https://example.com",
        domain="example.com"
    )


# ============================================================================
# Test 1: Web → LLM → Clipboard Pipeline
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_web_to_llm_to_clipboard(mock_system_bridge, mock_llm_service, execution_context):
    """
    Test workflow: Extract web content → Summarize with LLM → Copy to clipboard
    
    Steps:
    1. browser.get_page_content() - Extract content from web page (uses trafilatura)
    2. llm.summarize(input_from="last_output") - Summarize the content
    3. ui.paste() - Paste summary to active application
    
    TICKET-P1-E2E: Validates Extract→Process→Output pipeline with trafilatura
    """
    print("\n" + "=" * 80)
    print("TEST: Web → LLM → Clipboard Workflow")
    print("=" * 80)
    
    start_time = time.time()
    
    # Setup agents
    with patch("janus.capabilities.agents.browser_agent.get_system_bridge", return_value=mock_system_bridge):
        browser_agent = BrowserAgent(provider="safari")
        
        # Step 1: Extract page content (trafilatura already integrated)
        print("\n✓ Step 1: Extract web page content using trafilatura")
        result1 = await browser_agent.execute("get_page_content", {}, execution_context.get_current_context())
        
        assert result1["status"] == "success", f"Failed to extract content: {result1}"
        print(f"  Extracted content: {result1.get('message', 'N/A')}")
        
        # Verify trafilatura is being used or fallback
        content_data = result1.get("data", "Sample page content")
        if isinstance(content_data, dict):
            extracted_text = content_data.get("content", content_data)
            method = content_data.get("method", "unknown")
            print(f"  Extraction method: {method}")
        else:
            extracted_text = str(content_data)
            print(f"  Extraction method: fallback")
        
        execution_context.store_output(extracted_text, "step.0")
        
        # Step 2: Summarize with LLM
        print("\n✓ Step 2: Summarize content with LLM")
        with patch("janus.capabilities.agents.llm_agent.LLMAgent.llm_service", mock_llm_service):
            llm_agent = LLMAgent(provider="local")
            
            # Resolve input_from reference
            args = execution_context.resolve_args({"input_from": "last_output"})
            result2 = await llm_agent.execute("summarize", {"text": args.get("input", extracted_text)}, {})
            
            assert result2["status"] == "success", f"Failed to summarize: {result2}"
            summary = result2["data"]["summary"]
            print(f"  Summary: {summary}")
            
            execution_context.store_output(summary, "step.1")
        
        # Step 3: Paste to clipboard (simulated)
        print("\n✓ Step 3: Paste to clipboard")
        with patch("janus.capabilities.agents.ui_agent.get_system_bridge", return_value=mock_system_bridge):
            mock_system_bridge.press_key.return_value = MagicMock(success=True)
            
            ui_agent = UIAgent(system_bridge=mock_system_bridge)
            result3 = await ui_agent.execute("paste", {}, {})
            
            assert result3["status"] == "success", f"Failed to paste: {result3}"
            print(f"  Paste result: {result3.get('message', 'OK')}")
    
    duration = time.time() - start_time
    print(f"\n✅ Workflow completed successfully in {duration:.2f}s!")
    assert duration < 5.0, f"Workflow took too long: {duration:.2f}s (expected < 5s)"


# ============================================================================
# Test 2: App → LLM → Clipboard Pipeline
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_app_to_llm_to_clipboard(mock_system_bridge, mock_llm_service, execution_context):
    """
    Test workflow: Extract text from native app → Summarize → Paste
    
    Steps:
    1. ui.extract_text() - Extract text from active window (via Accessibility API)
    2. llm.summarize(input_from="last_output") - Summarize the text
    3. ui.paste() - Paste summary
    
    TICKET-P1-E2E: Validates native app text extraction via Accessibility
    """
    print("\n" + "=" * 80)
    print("TEST: App → LLM → Clipboard Workflow")
    print("=" * 80)
    
    start_time = time.time()
    
    with patch("janus.capabilities.agents.ui_agent.get_system_bridge", return_value=mock_system_bridge):
        # Mock clipboard operations
        mock_clipboard_result = MagicMock()
        mock_clipboard_result.success = True
        mock_clipboard_result.data = {"text": "Sample text from Notes app about project deadlines and team updates"}
        mock_system_bridge.get_clipboard_text.return_value = mock_clipboard_result
        mock_system_bridge.press_key.return_value = MagicMock(success=True)
        
        ui_agent = UIAgent(system_bridge=mock_system_bridge)
        
        # Step 1: Extract text from app (using Accessibility API)
        print("\n✓ Step 1: Extract text from active app via Accessibility API")
        result1 = await ui_agent.execute("extract_text", {}, {"app": "Notes"})
        
        assert result1["status"] == "success", f"Failed to extract text: {result1}"
        extracted_text = result1["data"]["text"]
        method = result1["data"].get("method", "unknown")
        print(f"  Extracted {len(extracted_text)} characters from app")
        print(f"  Extraction method: {method}")
        
        execution_context.store_output(extracted_text, "step.0")
        
        # Step 2: Summarize with LLM
        print("\n✓ Step 2: Summarize text with LLM")
        with patch("janus.capabilities.agents.llm_agent.LLMAgent.llm_service", mock_llm_service):
            llm_agent = LLMAgent(provider="local")
            
            args = execution_context.resolve_args({"input_from": "last_output"})
            result2 = await llm_agent.execute("summarize", {"text": args.get("input", extracted_text)}, {})
            
            assert result2["status"] == "success", f"Failed to summarize: {result2}"
            summary = result2["data"]["summary"]
            print(f"  Summary: {summary}")
            
            execution_context.store_output(summary, "step.1")
        
        # Step 3: Paste summary
        print("\n✓ Step 3: Paste summary to clipboard")
        result3 = await ui_agent.execute("paste", {}, {})
        
        assert result3["status"] == "success", f"Failed to paste: {result3}"
        print(f"  Paste result: {result3.get('message', 'OK')}")
    
    duration = time.time() - start_time
    print(f"\n✅ Workflow completed successfully in {duration:.2f}s!")
    assert duration < 5.0, f"Workflow took too long: {duration:.2f}s (expected < 5s)"


# ============================================================================
# Test 3: Teams → LLM → Email Pipeline
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_teams_to_llm_to_email(mock_llm_service, execution_context):
    """
    Test workflow: Summarize Teams conversation → Send via email
    
    Steps:
    1. messaging.summarize_thread(platform='teams') - Summarize Teams conversation
    2. email.send_email(input_from="last_output") - Send summary via email
    
    TICKET-P1-E2E: Validates Messaging→LLM→Email pipeline with multi-provider support
    """
    print("\n" + "=" * 80)
    print("TEST: Teams → LLM → Email Workflow")
    print("=" * 80)
    
    start_time = time.time()
    
    # Mock Teams client
    mock_teams_client = MagicMock()
    mock_teams_client.enabled = True
    mock_teams_client.read_channel_history.return_value = [
        {"sender": "Alice", "text": "Let's discuss the project timeline"},
        {"sender": "Bob", "text": "We need to deliver by Friday"},
        {"sender": "Alice", "text": "Agreed, I'll prepare the presentation"}
    ]
    mock_teams_client.format_messages_for_summary.return_value = """
    Alice: Let's discuss the project timeline
    Bob: We need to deliver by Friday
    Alice: Agreed, I'll prepare the presentation
    """
    
    # Step 1: Summarize Teams thread
    print("\n✓ Step 1: Summarize Teams conversation (provider='teams')")
    with patch.object(MessagingAgent, "_get_client", return_value=mock_teams_client):
        # Note: llm_client is required for summarize_thread action
        messaging_agent = MessagingAgent(llm_client=mock_llm_service, provider="teams")
        messaging_agent.llm_client = mock_llm_service
        
        result1 = await messaging_agent.execute(
            "summarize_thread",
            {
                "platform": "teams",
                "channel": "general",
                "team_id": "team123",
                "limit": 50
            },
            {}
        )
        
        assert result1["status"] == "success", f"Failed to summarize thread: {result1}"
        summary = result1["data"]["summary"]
        print(f"  Summary: {summary}")
        print(f"  Message count: {result1['data']['message_count']}")
        
        execution_context.store_output(summary, "step.0")
    
    # Step 2: Send email (mock)
    print("\n✓ Step 2: Send summary via email (provider='outlook')")
    mock_email_provider = MagicMock(spec=EmailProvider)
    mock_email_provider.enabled = True
    mock_email_provider.send_email.return_value = True
    
    with patch("janus.capabilities.agents.email_agent.EmailProvider", return_value=mock_email_provider):
        email_agent = EmailAgent(provider="outlook")
        email_agent.email_provider = mock_email_provider
        
        args = execution_context.resolve_args({"input_from": "last_output"})
        result2 = await email_agent.execute(
            "send_email",
            {
                "to": "manager@example.com",
                "subject": "Teams Discussion Summary",
                "body": args.get("input", summary)
            },
            {}
        )
        
        assert result2["status"] == "success", f"Failed to send email: {result2}"
        print(f"  Email sent to: {result2['data']['to']}")
        print(f"  Subject: {result2['data']['subject']}")
    
    duration = time.time() - start_time
    print(f"\n✅ Workflow completed successfully in {duration:.2f}s!")
    assert duration < 5.0, f"Workflow took too long: {duration:.2f}s (expected < 5s)"


# ============================================================================
# Test 4: Email → LLM → Messaging Pipeline
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_email_to_llm_to_messaging(mock_llm_service, execution_context):
    """
    Test workflow: Summarize emails → Post to Slack/Teams
    
    Steps:
    1. email.get_recent_emails() - Get recent emails from inbox
    2. llm.summarize(input_from="last_output") - Summarize emails
    3. messaging.post_message(input_from="last_output") - Post to Slack
    
    TICKET-P1-E2E: Validates Email→LLM→Messaging pipeline
    """
    print("\n" + "=" * 80)
    print("TEST: Email → LLM → Messaging Workflow")
    print("=" * 80)
    
    start_time = time.time()
    
    # Mock email provider
    mock_email_provider = MagicMock(spec=EmailProvider)
    mock_email_provider.enabled = True
    mock_email_provider.get_recent_emails.return_value = [
        {
            "subject": "Q4 Planning Meeting",
            "sender": "manager@example.com",
            "body": "We need to discuss Q4 goals and budget allocation",
            "timestamp": "2024-12-16T10:00:00"
        },
        {
            "subject": "Project Update",
            "sender": "team@example.com",
            "body": "The new feature is ready for testing",
            "timestamp": "2024-12-16T11:30:00"
        }
    ]
    
    # Step 1: Get recent emails
    print("\n✓ Step 1: Get recent emails (provider='outlook')")
    with patch("janus.capabilities.agents.email_agent.EmailProvider", return_value=mock_email_provider):
        email_agent = EmailAgent(provider="outlook")
        email_agent.email_provider = mock_email_provider
        
        result1 = await email_agent.execute("get_recent_emails", {"limit": 5}, {})
        
        assert result1["status"] == "success", f"Failed to get emails: {result1}"
        emails = result1["data"]["emails"]
        print(f"  Retrieved {len(emails)} emails")
        
        # Format emails for summarization
        email_text = "\n\n".join([
            f"From: {e['sender']}\nSubject: {e['subject']}\n{e['body']}"
            for e in emails
        ])
        execution_context.store_output(email_text, "step.0")
    
    # Step 2: Summarize emails with LLM
    print("\n✓ Step 2: Summarize emails with LLM")
    with patch("janus.capabilities.agents.llm_agent.LLMAgent.llm_service", mock_llm_service):
        llm_agent = LLMAgent(provider="local")
        
        args = execution_context.resolve_args({"input_from": "last_output"})
        result2 = await llm_agent.execute("summarize", {"text": args.get("input", email_text)}, {})
        
        assert result2["status"] == "success", f"Failed to summarize: {result2}"
        summary = result2["data"]["summary"]
        print(f"  Summary: {summary}")
        
        execution_context.store_output(summary, "step.1")
    
    # Step 3: Post to Slack
    print("\n✓ Step 3: Post summary to Slack (provider='slack')")
    mock_slack_client = MagicMock()
    mock_slack_client.enabled = True
    mock_slack_client.post_message.return_value = {"ok": True, "ts": "1234567890.123456"}
    
    with patch.object(MessagingAgent, "_get_client", return_value=mock_slack_client):
        # Note: llm_client not needed for post_message action
        messaging_agent = MessagingAgent(provider="slack")
        
        args = execution_context.resolve_args({"input_from": "last_output"})
        result3 = await messaging_agent.execute(
            "post_message",
            {
                "platform": "slack",
                "channel": "#general",
                "text": f"📧 Email Summary:\n{args.get('input', summary)}"
            },
            {}
        )
        
        assert result3["status"] == "success", f"Failed to post message: {result3}"
        print(f"  Message posted to Slack successfully")
    
    duration = time.time() - start_time
    print(f"\n✅ Workflow completed successfully in {duration:.2f}s!")
    assert duration < 5.0, f"Workflow took too long: {duration:.2f}s (expected < 5s)"


# ============================================================================
# Test 5: Input Context Chaining
# ============================================================================

@pytest.mark.asyncio
async def test_execution_context_input_chaining():
    """
    Test that ExecutionContext properly chains outputs using input_from.
    
    This validates the core chaining mechanism used across all workflows.
    """
    print("\n" + "=" * 80)
    print("TEST: ExecutionContext input_from Chaining")
    print("=" * 80)
    
    context = ExecutionContext()
    
    # Store sequential outputs
    context.store_output("First output", "step.0")
    context.store_output("Second output", "step.1")
    context.store_output("Third output", "custom_step")
    
    # Test resolution
    print("\n✓ Test last_output resolution")
    assert context.resolve_input("last_output") == "Third output"
    print(f"  last_output → {context.resolve_input('last_output')}")
    
    print("\n✓ Test step.0 resolution")
    assert context.resolve_input("step.0") == "First output"
    print(f"  step.0 → {context.resolve_input('step.0')}")
    
    print("\n✓ Test custom step resolution")
    assert context.resolve_input("custom_step") == "Third output"
    print(f"  custom_step → {context.resolve_input('custom_step')}")
    
    # Test resolve_args
    print("\n✓ Test resolve_args with input_from")
    args = context.resolve_args({"input_from": "step.1", "other_param": "value"})
    assert args.get("input") == "Second output"
    assert args.get("other_param") == "value"
    print(f"  Resolved args: {args}")
    
    print("\n✅ Input chaining validated!")


# ============================================================================
# Test 6: Multi-Provider Support Validation
# ============================================================================

@pytest.mark.asyncio
async def test_multi_provider_support():
    """
    Test that agents support multiple providers explicitly.
    
    TICKET-P1-E2E: Validates multi-provider support across agents
    
    Validates:
    - SchedulerAgent: outlook, google, apple, local, notion
    - FilesAgent: local, onedrive, dropbox, gdrive, icloud
    - MessagingAgent: slack, teams, discord, telegram
    - EmailAgent: outlook, gmail, apple, imap
    """
    print("\n" + "=" * 80)
    print("TEST: Multi-Provider Support Validation")
    print("=" * 80)
    
    # Test SchedulerAgent providers
    print("\n✓ Test 1: SchedulerAgent providers")
    from janus.capabilities.agents.scheduler_agent import SchedulerAgent
    
    for provider in ["local", "outlook", "google", "apple", "notion"]:
        agent = SchedulerAgent(provider=provider)
        assert agent.provider == provider, f"SchedulerAgent provider mismatch: {agent.provider} != {provider}"
        print(f"  ✓ SchedulerAgent(provider='{provider}')")
    
    # Test FilesAgent providers
    print("\n✓ Test 2: FilesAgent providers")
    from janus.capabilities.agents.files_agent import FilesAgent
    
    for provider in ["local", "onedrive", "dropbox", "gdrive", "icloud"]:
        agent = FilesAgent(provider=provider)
        assert agent.provider == provider, f"FilesAgent provider mismatch: {agent.provider} != {provider}"
        print(f"  ✓ FilesAgent(provider='{provider}')")
    
    # Test MessagingAgent providers
    print("\n✓ Test 3: MessagingAgent providers")
    for provider in ["slack", "teams", "discord", "telegram"]:
        agent = MessagingAgent(provider=provider)
        assert agent.provider == provider, f"MessagingAgent provider mismatch: {agent.provider} != {provider}"
        print(f"  ✓ MessagingAgent(provider='{provider}')")
    
    # Test EmailAgent providers
    print("\n✓ Test 4: EmailAgent providers")
    for provider in ["outlook", "gmail", "apple", "imap"]:
        agent = EmailAgent(provider=provider)
        assert agent.provider == provider, f"EmailAgent provider mismatch: {agent.provider} != {provider}"
        print(f"  ✓ EmailAgent(provider='{provider}')")
    
    print("\n✅ All providers validated successfully!")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    """Run tests manually for development."""
    print("Running E2E Workflow Tests...")
    
    # Run with asyncio
    async def run_all_tests():
        from unittest.mock import MagicMock
        
        # Create fixtures
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = True
        mock_bridge.get_platform_name.return_value = "macOS"
        mock_window = MagicMock()
        mock_window.app_name = "Safari"
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"window": mock_window}
        mock_bridge.get_active_window.return_value = mock_result
        script_result = MagicMock()
        script_result.success = True
        script_result.data = {"stdout": "Sample content"}
        mock_bridge.run_script.return_value = script_result
        
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        
        async def mock_gen(prompt, max_tokens=150, temperature=0.3):
            return {"success": True, "content": "Test summary"}
        
        mock_llm.generate_async = mock_gen
        
        context = ExecutionContext()
        
        # Run tests
        await test_workflow_web_to_llm_to_clipboard(mock_bridge, mock_llm, context)
        await test_workflow_app_to_llm_to_clipboard(mock_bridge, mock_llm, context)
        await test_workflow_teams_to_llm_to_email(mock_llm, context)
        await test_workflow_email_to_llm_to_messaging(mock_llm, context)
        await test_execution_context_input_chaining()
        await test_multi_provider_support()
    
    asyncio.run(run_all_tests())
    print("\n✅ All tests completed!")
