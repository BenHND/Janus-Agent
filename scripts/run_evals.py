#!/usr/bin/env python3
"""
TICKET-304: Automated QA Evaluation Pipeline for ReasonerLLM

This script evaluates the ReasonerLLM against a "Golden Set" of test cases
to measure command comprehension accuracy and prevent regressions.

Usage:
    python scripts/run_evals.py [--backend mock|ollama] [--model MODEL] [--verbose]

Features:
    - Loads ReasonerLLM (mock backend for testing, ollama for production)
    - Iterates over dataset_v1.json test cases
    - Performs semantic comparison (not exact string matching)
    - Generates precision score and detailed failure logs
    - Completes in <2 minutes with mock backend
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class EvalResult:
    """Result of a single test case evaluation"""
    
    test_id: str
    passed: bool = False
    expected_module: Optional[str] = None
    actual_module: Optional[str] = None
    expected_action: Optional[str] = None
    actual_action: Optional[str] = None
    expected_steps_count: int = 0
    actual_steps_count: int = 0
    error_message: Optional[str] = None
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalReport:
    """Aggregated evaluation report"""
    
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    total_time_ms: float = 0.0
    avg_latency_ms: float = 0.0
    accuracy_percent: float = 0.0
    failures: List[EvalResult] = field(default_factory=list)
    results_by_category: Dict[str, Dict[str, int]] = field(default_factory=dict)


def normalize_url(url: Optional[str]) -> Optional[str]:
    """Normalize URL for comparison (handle www, trailing slashes, etc.)"""
    if url is None:
        return None
    
    url = url.lower().strip()
    
    # Remove trailing slashes
    url = url.rstrip("/")
    
    # Normalize www
    if "://www." in url:
        url = url.replace("://www.", "://")
    
    # Only add https:// if URL doesn't already have a protocol
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    
    return url


def normalize_string(s: Optional[str]) -> Optional[str]:
    """Normalize string for comparison (lowercase, strip whitespace)"""
    if s is None:
        return None
    return s.lower().strip()


def compare_args_semantic(
    expected_args: Dict[str, Any],
    actual_args: Dict[str, Any],
    action: str
) -> Tuple[bool, Optional[str]]:
    """
    Perform semantic comparison of action arguments.
    
    Returns:
        Tuple of (match, error_message)
    """
    # For URL arguments, use URL normalization
    if "url" in expected_args or "url" in actual_args:
        expected_url = normalize_url(expected_args.get("url"))
        actual_url = normalize_url(actual_args.get("url"))
        
        # Check if actual URL contains expected domain
        if expected_url and actual_url:
            # Extract domain from both
            expected_domain = expected_url.replace("https://", "").replace("http://", "").split("/")[0]
            actual_domain = actual_url.replace("https://", "").replace("http://", "").split("/")[0]
            
            if expected_domain != actual_domain:
                return False, f"URL domain mismatch: expected '{expected_domain}', got '{actual_domain}'"
    
    # For app_name, use normalized string comparison
    if "app_name" in expected_args or "app_name" in actual_args:
        expected_app = normalize_string(expected_args.get("app_name"))
        actual_app = normalize_string(actual_args.get("app_name"))
        
        if expected_app != actual_app:
            return False, f"App name mismatch: expected '{expected_app}', got '{actual_app}'"
    
    # For query/search, check if key terms are present
    if "query" in expected_args or "query" in actual_args:
        expected_query = normalize_string(expected_args.get("query"))
        actual_query = normalize_string(actual_args.get("query"))
        
        if expected_query and actual_query:
            # Check if actual contains key terms from expected
            expected_terms = set(expected_query.split())
            actual_terms = set(actual_query.split())
            
            # At least 50% of expected terms should be present
            if len(expected_terms) > 0:
                overlap = len(expected_terms & actual_terms)
                if overlap < len(expected_terms) * 0.5:
                    return False, f"Query mismatch: expected '{expected_query}', got '{actual_query}'"
    
    # For message, similar fuzzy matching
    if "message" in expected_args or "message" in actual_args:
        expected_msg = normalize_string(expected_args.get("message"))
        actual_msg = normalize_string(actual_args.get("message"))
        
        if expected_msg != actual_msg:
            return False, f"Message mismatch: expected '{expected_msg}', got '{actual_msg}'"
    
    # For name (thread name, etc.)
    if "name" in expected_args or "name" in actual_args:
        expected_name = normalize_string(expected_args.get("name"))
        actual_name = normalize_string(actual_args.get("name"))
        
        # Partial match is OK for names
        if expected_name and actual_name:
            if expected_name not in actual_name and actual_name not in expected_name:
                return False, f"Name mismatch: expected '{expected_name}', got '{actual_name}'"
    
    # For field_name and value in CRM
    if "field_name" in expected_args:
        expected_field = normalize_string(expected_args.get("field_name"))
        actual_field = normalize_string(actual_args.get("field_name"))
        
        if expected_field != actual_field:
            return False, f"Field name mismatch: expected '{expected_field}', got '{actual_field}'"
    
    if "value" in expected_args:
        expected_value = normalize_string(expected_args.get("value"))
        actual_value = normalize_string(actual_args.get("value"))
        
        if expected_value != actual_value:
            return False, f"Value mismatch: expected '{expected_value}', got '{actual_value}'"
    
    return True, None


def compare_step_semantic(
    expected_step: Dict[str, Any],
    actual_step: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Perform semantic comparison of a single step.
    
    Returns:
        Tuple of (match, error_message)
    """
    # Module must match
    expected_module = expected_step.get("module")
    actual_module = actual_step.get("module")
    
    if expected_module != actual_module:
        return False, f"Module mismatch: expected '{expected_module}', got '{actual_module}'"
    
    # Action must match (considering aliases)
    expected_action = expected_step.get("action")
    actual_action = actual_step.get("action")
    
    # Define action aliases for flexible matching
    action_aliases = {
        "open_application": ["open_app", "launch", "launch_app"],
        "open_url": ["navigate", "goto", "go_to_url"],
        "search": ["search_web", "google"],
    }
    
    # Check if actions match (directly or via alias)
    actions_match = expected_action == actual_action
    if not actions_match:
        # Check aliases
        for canonical, aliases in action_aliases.items():
            if expected_action == canonical and actual_action in aliases:
                actions_match = True
                break
            if actual_action == canonical and expected_action in aliases:
                actions_match = True
                break
    
    if not actions_match:
        return False, f"Action mismatch: expected '{expected_action}', got '{actual_action}'"
    
    # Compare args semantically
    expected_args = expected_step.get("args", {})
    actual_args = actual_step.get("args", {})
    
    args_match, args_error = compare_args_semantic(expected_args, actual_args, expected_action)
    if not args_match:
        return False, args_error
    
    return True, None


def compare_plan_semantic(
    expected_plan: Dict[str, Any],
    actual_plan: Dict[str, Any]
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Perform semantic comparison of entire plans.
    
    Strategy:
    - Number of steps must match (±1 for edge cases)
    - Each step's module and action must match
    - Args are compared semantically (not exact string match)
    
    Returns:
        Tuple of (match, error_message, details)
    """
    expected_steps = expected_plan.get("steps", [])
    actual_steps = actual_plan.get("steps", [])
    
    details = {
        "expected_steps": len(expected_steps),
        "actual_steps": len(actual_steps),
    }
    
    # Handle empty expected plans (edge cases)
    if len(expected_steps) == 0:
        # For edge cases, we expect either empty steps or a reasonable fallback
        # Allow empty or single-step fallback
        if len(actual_steps) <= 1:
            return True, None, details
        return False, f"Expected empty/minimal plan, got {len(actual_steps)} steps", details
    
    # Step count tolerance: allow ±1 step difference
    step_diff = abs(len(expected_steps) - len(actual_steps))
    if step_diff > 1:
        return False, f"Step count mismatch: expected {len(expected_steps)}, got {len(actual_steps)}", details
    
    # Compare each step up to the minimum count
    min_steps = min(len(expected_steps), len(actual_steps))
    
    for i in range(min_steps):
        expected_step = expected_steps[i]
        actual_step = actual_steps[i]
        
        step_match, step_error = compare_step_semantic(expected_step, actual_step)
        
        if not step_match:
            details["failing_step"] = i
            details["expected_step"] = expected_step
            details["actual_step"] = actual_step
            return False, f"Step {i}: {step_error}", details
    
    return True, None, details


def run_single_eval(
    llm,
    test_case: Dict[str, Any],
    verbose: bool = False
) -> EvalResult:
    """
    Run evaluation for a single test case.
    
    Args:
        llm: ReasonerLLM instance
        test_case: Test case dictionary from dataset
        verbose: Print detailed output
    
    Returns:
        EvalResult with pass/fail status and details
    """
    test_id = test_case.get("id", "unknown")
    language = test_case.get("language", "fr")
    input_command = test_case.get("input", "")
    expected_plan = test_case.get("expected_plan", {})
    
    result = EvalResult(test_id=test_id)
    
    try:
        start_time = time.time()
        
        # Generate plan using ReasonerLLM
        actual_plan = llm.generate_structured_plan(input_command, language=language)
        
        result.latency_ms = (time.time() - start_time) * 1000
        
        # Compare plans semantically
        passed, error_msg, details = compare_plan_semantic(expected_plan, actual_plan)
        
        result.passed = passed
        result.error_message = error_msg
        result.details = details
        
        # Extract key info for reporting
        result.expected_steps_count = len(expected_plan.get("steps", []))
        result.actual_steps_count = len(actual_plan.get("steps", []))
        
        if expected_plan.get("steps"):
            result.expected_module = expected_plan["steps"][0].get("module")
            result.expected_action = expected_plan["steps"][0].get("action")
        
        if actual_plan.get("steps"):
            result.actual_module = actual_plan["steps"][0].get("module")
            result.actual_action = actual_plan["steps"][0].get("action")
        
        if verbose:
            status = "✓" if passed else "✗"
            print(f"  {status} {test_id}: {input_command[:40]}...")
            if not passed:
                print(f"    Error: {error_msg}")
    
    except Exception as e:
        result.passed = False
        result.error_message = f"Exception: {str(e)}"
        
        if verbose:
            print(f"  ✗ {test_id}: Exception - {str(e)}")
    
    return result


def run_evaluation(
    backend: str = "mock",
    model: Optional[str] = None,
    dataset_path: Optional[str] = None,
    verbose: bool = False
) -> EvalReport:
    """
    Run full evaluation pipeline.
    
    Args:
        backend: LLM backend ("mock" or "ollama")
        model: Model name for ollama backend
        dataset_path: Path to dataset JSON file
        verbose: Print detailed output
    
    Returns:
        EvalReport with aggregated results
    """
    # Import here to avoid import errors before path setup
    from janus.ai.reasoning.reasoner_llm import ReasonerLLM
    
    # Initialize report
    report = EvalReport()
    
    # Load dataset
    if dataset_path is None:
        dataset_path = project_root / "tests" / "evals" / "dataset_v1.json"
    else:
        dataset_path = Path(dataset_path)
    
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        return report
    
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    test_cases = dataset.get("test_cases", [])
    report.total_tests = len(test_cases)
    
    print(f"🚀 Janus Evals Pipeline")
    print(f"   Dataset: {dataset_path.name} (v{dataset.get('version', '?')})")
    print(f"   Test cases: {report.total_tests}")
    print(f"   Backend: {backend}")
    if model:
        print(f"   Model: {model}")
    print()
    
    # Initialize ReasonerLLM
    if verbose:
        print("Initializing ReasonerLLM...")
    
    if backend == "ollama" and model:
        llm = ReasonerLLM(backend=backend, model_name=model)
    else:
        llm = ReasonerLLM(backend=backend)
    
    if not llm.available:
        print(f"❌ LLM not available (backend: {backend})")
        return report
    
    if verbose:
        print(f"✓ LLM initialized (available: {llm.available})")
        print()
    
    # Run evaluations
    start_time = time.time()
    
    print("Running evaluations...")
    if verbose:
        print()
    
    for test_case in test_cases:
        result = run_single_eval(llm, test_case, verbose=verbose)
        
        category = test_case.get("category", "unknown")
        
        # Update category stats
        if category not in report.results_by_category:
            report.results_by_category[category] = {"passed": 0, "failed": 0, "total": 0}
        
        report.results_by_category[category]["total"] += 1
        
        if result.passed:
            report.passed += 1
            report.results_by_category[category]["passed"] += 1
        else:
            report.failed += 1
            report.results_by_category[category]["failed"] += 1
            report.failures.append(result)
        
        report.total_time_ms += result.latency_ms
    
    # Calculate final stats
    report.avg_latency_ms = report.total_time_ms / report.total_tests if report.total_tests > 0 else 0
    report.accuracy_percent = (report.passed / report.total_tests * 100) if report.total_tests > 0 else 0
    
    elapsed_time = time.time() - start_time
    
    # Print report
    print()
    print("=" * 60)
    print(f"📊 EVALUATION REPORT")
    print("=" * 60)
    print()
    print(f"Score: {report.passed}/{report.total_tests} ({report.accuracy_percent:.1f}%)")
    print(f"Time: {elapsed_time:.2f}s (avg latency: {report.avg_latency_ms:.1f}ms)")
    print()
    
    print("Results by category:")
    for category, stats in sorted(report.results_by_category.items()):
        cat_percent = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {category}: {stats['passed']}/{stats['total']} ({cat_percent:.0f}%)")
    
    if report.failures:
        print()
        print(f"❌ Failed tests ({len(report.failures)}):")
        for failure in report.failures[:10]:  # Show first 10 failures
            print(f"  - {failure.test_id}")
            print(f"    Expected: {failure.expected_module}.{failure.expected_action}")
            print(f"    Actual:   {failure.actual_module}.{failure.actual_action}")
            if failure.error_message:
                print(f"    Error: {failure.error_message}")
        
        if len(report.failures) > 10:
            print(f"  ... and {len(report.failures) - 10} more failures")
    
    print()
    print("=" * 60)
    
    return report


def main():
    """Main entry point for the evaluation script."""
    parser = argparse.ArgumentParser(
        description="Janus Evals - Automated QA Pipeline for ReasonerLLM"
    )
    parser.add_argument(
        "--backend",
        choices=["mock", "ollama"],
        default="mock",
        help="LLM backend to use (default: mock)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name for ollama backend (e.g., llama3.2)"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to dataset JSON file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output"
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Output results to JSON file"
    )
    
    args = parser.parse_args()
    
    # Run evaluation
    report = run_evaluation(
        backend=args.backend,
        model=args.model,
        dataset_path=args.dataset,
        verbose=args.verbose
    )
    
    # Output JSON if requested
    if args.json_output:
        output_data = {
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "accuracy_percent": report.accuracy_percent,
            "total_time_ms": report.total_time_ms,
            "avg_latency_ms": report.avg_latency_ms,
            "results_by_category": report.results_by_category,
            "failures": [
                {
                    "test_id": f.test_id,
                    "expected_module": f.expected_module,
                    "expected_action": f.expected_action,
                    "actual_module": f.actual_module,
                    "actual_action": f.actual_action,
                    "error_message": f.error_message,
                }
                for f in report.failures
            ]
        }
        
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to: {args.json_output}")
    
    # Exit with appropriate code
    sys.exit(0 if report.accuracy_percent >= 80 else 1)


if __name__ == "__main__":
    main()
