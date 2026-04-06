#!/usr/bin/env python3
"""
Agent Documentation Generator CLI

TICKET-ARCH-AGENT: Architecture Agentique - Solution propre, stable et extensible

This script generates documentation for all discovered agents and their actions.

Usage:
    python -m janus.capabilities.agents.generate_docs [--output FILE]
    
    # Or via CLI
    janus --agents-doc
    janus --agents-doc --output docs/agents.md
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from janus.capabilities.agents.discovery import get_agent_discovery


def main():
    """Main entry point for documentation generation."""
    parser = argparse.ArgumentParser(
        description="Generate documentation for Janus agents and their actions"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: print to stdout)"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    
    args = parser.parse_args()
    
    # Discover agents
    discovery = get_agent_discovery()
    discovery.discover_agents()
    
    # Generate documentation
    if args.format == "markdown":
        doc_content = discovery.generate_documentation()
    else:
        # JSON format
        import json
        metadata = discovery.get_all_metadata()
        doc_content = json.dumps(
            {
                agent: [action.to_dict() for action in actions]
                for agent, actions in metadata.items()
            },
            indent=2
        )
    
    # Output documentation
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(doc_content)
        print(f"✓ Documentation written to: {output_path}")
    else:
        print(doc_content)


if __name__ == "__main__":
    main()
