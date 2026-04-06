"""
Example demonstrating TICKET 3 - Structured Reasoning with LLM

This example shows:
1. Structured plan generation with multiple modules
2. Native LLM actions (summarize, rewrite, extract_keywords, analyze_error, answer_question)
3. Re-planning capability when actions fail
4. Short-term memory integration

Run with: python examples/example_ticket3_structured_reasoning.py
"""
import sys
from pathlib import Path

# Add parent directory to path to import janus
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.modules.llm_module import LLMModule
from janus.ai.reasoning.reasoner_llm import ReasonerLLM


def example_structured_plan_generation():
    """Example 1: Generate structured plans with multiple modules"""
    print("=" * 60)
    print("Example 1: Structured Plan Generation")
    print("=" * 60)

    reasoner = ReasonerLLM(backend="mock")

    # Simple command
    print("\n1. Simple command: 'ouvre Chrome'")
    plan = reasoner.generate_structured_plan("ouvre Chrome", language="fr")
    print(f"Plan: {plan}")
    print(f"Steps: {len(plan['steps'])}")

    # Complex multi-module command
    print("\n2. Complex command: 'ouvre Chrome et résume la page'")
    plan = reasoner.generate_structured_plan("ouvre Chrome et résume la page", language="fr")
    print(f"Plan: {plan}")
    print(f"Steps: {len(plan['steps'])}")

    # Command with memory context
    print("\n3. Command with memory context")
    context = {
        "vision_output": {"screen": "Chrome browser is open"},
        "previous_outputs": ["Chrome opened successfully"],
        "user_context": {"preferred_browser": "Chrome"},
    }
    plan = reasoner.generate_structured_plan(
        "cherche Python tutorial", context=context, language="fr"
    )
    print(f"Plan: {plan}")
    print(f"Context used: vision_output={bool(context.get('vision_output'))}")


def example_llm_actions():
    """Example 2: Native LLM actions"""
    print("\n" + "=" * 60)
    print("Example 2: Native LLM Actions")
    print("=" * 60)

    llm_module = LLMModule()
    llm_module.initialize()

    # 1. Summarize
    print("\n1. Summarize action:")
    result = llm_module.execute(
        {
            "action": "summarize",
            "args": {
                "text": "Python is a high-level programming language. It is known for its simplicity and readability. Python is used in web development, data science, automation, and machine learning. It has a large ecosystem of libraries and frameworks."
            },
        }
    )
    print(f"Status: {result['status']}")
    print(f"Summary: {result.get('summary', 'N/A')[:100]}...")

    # 2. Extract keywords
    print("\n2. Extract keywords action:")
    result = llm_module.execute(
        {
            "action": "extract_keywords",
            "args": {
                "text": "Python programming language data science machine learning automation web development frameworks libraries",
                "max_keywords": 5,
            },
        }
    )
    print(f"Status: {result['status']}")
    print(f"Keywords: {result.get('keywords', [])}")

    # 3. Analyze error
    print("\n3. Analyze error action:")
    result = llm_module.execute(
        {
            "action": "analyze_error",
            "args": {
                "error": "PermissionError: [Errno 13] Permission denied: '/etc/hosts'",
                "context": "Trying to modify system file",
            },
        }
    )
    print(f"Status: {result['status']}")
    print(f"Analysis: {result.get('analysis', 'N/A')[:150]}...")

    # 4. Rewrite
    print("\n4. Rewrite action:")
    result = llm_module.execute(
        {"action": "rewrite", "args": {"text": "Hey, what's up?", "style": "formal"}}
    )
    print(f"Status: {result['status']}")
    print(f"Rewritten: {result.get('rewritten_text', 'N/A')}")

    # 5. Answer question
    print("\n5. Answer question action:")
    result = llm_module.execute(
        {
            "action": "answer_question",
            "args": {
                "question": "What is Python?",
                "context": "Python is a high-level programming language",
            },
        }
    )
    print(f"Status: {result['status']}")
    print(f"Answer: {result.get('answer', 'N/A')[:100]}...")


def example_replanning():
    """Example 3: Re-planning after failures"""
    print("\n" + "=" * 60)
    print("Example 3: Re-planning After Failures")
    print("=" * 60)

    reasoner = ReasonerLLM(backend="mock")

    # Simulate a failed action
    failed_action = {
        "module": "chrome",
        "action": "open_url",
        "args": {"url": "https://example.com"},
    }

    # 1. Network timeout error
    print("\n1. Re-plan after network timeout:")
    error = "Network timeout after 30 seconds"
    replan = reasoner.replan(failed_action, error, language="en")
    print(f"New plan: {replan}")
    print(f"Explanation: {replan.get('explanation', 'N/A')}")

    # 2. 404 error with execution context
    print("\n2. Re-plan after 404 error with context:")
    error = "Page not found (404)"
    execution_context = {
        "completed_steps": [{"module": "default", "action": "open_application"}],
        "original_command": "ouvre Chrome et va sur test.com",
    }
    replan = reasoner.replan(
        failed_action, error, execution_context=execution_context, language="fr"
    )
    print(f"New plan: {replan}")
    print(f"Steps: {len(replan['steps'])}")
    print(f"Explanation: {replan.get('explanation', 'N/A')[:100]}...")

    # 3. Permission error
    print("\n3. Re-plan after permission error:")
    failed_action = {
        "module": "vscode",
        "action": "open_file",
        "args": {"path": "/system/protected.conf"},
    }
    error = "Permission denied: access to /system/protected.conf"
    replan = reasoner.replan(failed_action, error, language="en")
    print(f"New plan: {replan}")
    print(f"Explanation: {replan.get('explanation', 'N/A')[:100]}...")


def example_chaining_actions():
    """Example 4: Chaining LLM actions with last_result"""
    print("\n" + "=" * 60)
    print("Example 4: Chaining LLM Actions")
    print("=" * 60)

    llm_module = LLMModule()
    llm_module.initialize()

    # Step 1: Summarize
    print("\n1. Summarize original text:")
    text = "Python is a versatile programming language. It supports multiple programming paradigms including procedural, object-oriented, and functional programming. Python is dynamically typed and garbage-collected. It was created by Guido van Rossum and first released in 1991."
    result = llm_module.execute({"action": "summarize", "args": {"text": text}})
    print(f"Summary: {result.get('summary', 'N/A')[:100]}...")

    # Step 2: Extract keywords from the summary (uses last_result)
    print("\n2. Extract keywords from summary:")
    result = llm_module.execute({"action": "extract_keywords", "args": {"max_keywords": 5}})
    print(f"Keywords: {result.get('keywords', [])}")

    # Step 3: Rewrite using last result
    print("\n3. Rewrite with formal style:")
    result = llm_module.execute({"action": "rewrite", "args": {"style": "technical"}})
    print(f"Rewritten: {result.get('rewritten_text', 'N/A')[:100]}...")


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + " TICKET 3 - Structured Reasoning with LLM Examples ".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")

    try:
        example_structured_plan_generation()
        example_llm_actions()
        example_replanning()
        example_chaining_actions()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
