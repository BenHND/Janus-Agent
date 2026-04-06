"""
V3 Execution Agents for Janus

This package contains the specialized agents for the multi-agent architecture.

TICKET-303: Unified agents and suppression of legacy adapters.
All adapters have been moved to janus/agents/adapters/ as internal implementation details.

TICKET-REFACTOR-002: PlannerAgent removed (static planning deprecated).
Use ActionCoordinator for dynamic OODA loop execution instead.

TICKET-ARCH-AGENT: Architecture Agentique - Solution propre, stable et extensible
- @agent_action decorator for boilerplate reduction
- Auto-discovery mechanism for agents
- Provider parameter support for multi-provider scenarios

TICKET-P1-E2E: Pipeline Extract→Process→Output + Vision + Multi-Provider
- EmailAgent added for email operations

Validation Agent (TICKET 103):
- ValidatorAgent: Validates and corrects JSON V3 plans before execution

Execution Agents (10 specialized agents):
- SystemAgent: macOS system interactions (apps, keyboard, shortcuts)
- BrowserAgent: Web browser automation (Safari/Chrome)
- MessagingAgent: Messaging platforms (Teams, Slack, Discord)
- FilesAgent: File system operations (Finder, file management)
- CodeAgent: Code editor automation (VSCode)
- UIAgent: Generic UI interactions and feedback
- LLMAgent: LLM-based text transformations
- SchedulerAgent: Task scheduling and delayed actions (TICKET-FEAT-002)
- CRMAgent: Salesforce CRM operations (TICKET-BIZ-001)
- EmailAgent: Email operations and management (TICKET-P1-E2E)
"""

from .base_agent import BaseAgent, AgentExecutionError
from .validator_agent import ValidatorAgent
from .system_agent import SystemAgent
from .browser_agent import BrowserAgent
from .messaging_agent import MessagingAgent
from .files_agent import FilesAgent
from .code_agent import CodeAgent
from .ui_agent import UIAgent
from .llm_agent import LLMAgent
from .scheduler_agent import SchedulerAgent
from .crm_agent import CRMAgent
from .email_agent import EmailAgent

# TICKET-ARCH-AGENT: New architecture components
from .decorators import agent_action, ActionMetadata, get_action_metadata, list_agent_actions
from .discovery import AgentDiscovery, get_agent_discovery, auto_setup_agents

__all__ = [
    "BaseAgent",
    "AgentExecutionError",
    "ValidatorAgent",
    "SystemAgent",
    "BrowserAgent",
    "MessagingAgent",
    "FilesAgent",
    "CodeAgent",
    "UIAgent",
    "LLMAgent",
    "SchedulerAgent",
    "CRMAgent",
    "EmailAgent",
    # TICKET-ARCH-AGENT
    "agent_action",
    "ActionMetadata",
    "get_action_metadata",
    "list_agent_actions",
    "AgentDiscovery",
    "get_agent_discovery",
    "auto_setup_agents",
]
