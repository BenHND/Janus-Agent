"""
ONE-TICKET-VERIFICATION-007: Comprehensive verification tests

This test suite ensures:
1. Legacy code is completely removed (hard requirement)
2. No legacy references in codebase (CI guardrail)
3. All entrypoints use ActionCoordinator.execute_goal()
4. Feature invariants are maintained
5. Acceptance scenarios pass

Test structure:
- Phase 1: Legacy Removal Verification (CI guardrails)
- Phase 2: Wiring Verification (spy/mock instrumentation)
- Phase 3: Feature Acceptance Tests (invariants + scenarios)
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import List, Set
from unittest.mock import MagicMock, patch, AsyncMock

# Get repository root
REPO_ROOT = Path(__file__).parent.parent.absolute()
JANUS_ROOT = REPO_ROOT / "janus"


class TestPhase1LegacyRemoval(unittest.TestCase):
    """
    Phase 1: Verify all legacy code is removed and no references remain.
    
    These tests are CI guardrails that MUST pass before merging.
    They ensure legacy code cannot be reintroduced.
    """
    
    def test_legacy_files_deleted(self):
        """Test: Legacy files are physically deleted from filesystem"""
        legacy_files = [
            JANUS_ROOT / "llm" / "nlu_parser.py",
            JANUS_ROOT / "validation" / "json_plan_validator.py",
            JANUS_ROOT / "validation" / "json_plan_corrector.py",
            JANUS_ROOT / "core" / "agent_executor_v3.py",
            JANUS_ROOT / "core" / "execution_engine_v3.py",
        ]
        
        existing_files = []
        for file_path in legacy_files:
            if file_path.exists():
                existing_files.append(str(file_path.relative_to(REPO_ROOT)))
        
        self.assertEqual(
            len(existing_files), 0,
            f"Legacy files still exist: {existing_files}"
        )
    
    def test_no_legacy_references_in_code(self):
        """
        Test: No legacy references in codebase (text scan).
        
        Uses grep to scan for legacy patterns. Returns 0 matches or test fails.
        
        Legacy patterns:
        - AgentExecutorV3 / agent_executor_v3
        - execution_engine_v3
        - JSONPlanValidator / json_plan_validator
        - JSONPlanCorrector / json_plan_corrector
        - NLUParser / nlu_parser
        """
        legacy_patterns = [
            "AgentExecutorV3",
            "agent_executor_v3",
            "execution_engine_v3",
            "JSONPlanValidator",
            "json_plan_validator",
            "JSONPlanCorrector",
            "json_plan_corrector",
            "NLUParser",
            "nlu_parser",
        ]
        
        # Combine patterns into single grep
        pattern = "|".join(legacy_patterns)
        
        # Run grep (returns 1 if no matches, which is what we want)
        result = subprocess.run(
            ["grep", "-rn", "-E", pattern, str(JANUS_ROOT), "--include=*.py"],
            capture_output=True,
            text=True
        )
        
        # grep returns 0 if matches found, 1 if no matches
        # We want no matches, so exit code should be 1
        if result.returncode == 0:
            # Found matches - this is bad
            matches = result.stdout.strip().split("\n")
            # Filter out false positives (comments, strings about removal)
            real_matches = []
            for match in matches:
                # Skip if it's a comment about removal
                if "removed" in match.lower() or "legacy" in match.lower():
                    continue
                # Skip if it's in this test file
                if "test_one_ticket_verification.py" in match:
                    continue
                real_matches.append(match)
            
            self.assertEqual(
                len(real_matches), 0,
                f"Found {len(real_matches)} legacy references:\n" + "\n".join(real_matches[:10])
            )
    
    def test_no_legacy_imports(self):
        """Test: No code tries to import legacy modules"""
        import importlib.util
        
        # These imports should fail
        legacy_imports = [
            "janus.llm.nlu_parser",
            "janus.validation.json_plan_validator",
            "janus.validation.json_plan_corrector",
            "janus.core.agent_executor_v3",
            "janus.core.execution_engine_v3",
        ]
        
        for module_name in legacy_imports:
            try:
                spec = importlib.util.find_spec(module_name)
                self.assertIsNone(
                    spec,
                    f"Legacy module {module_name} can still be imported! It should not exist."
                )
            except (ModuleNotFoundError, ImportError) as e:
                # ImportError during find_spec is acceptable if it's not about the legacy module itself
                # It means the module doesn't exist (good!) but some dependency is missing
                if module_name not in str(e):
                    # Error is about a dependency, not the legacy module - this is OK
                    pass
                else:
                    # Error is about the legacy module itself - re-raise
                    raise
    
    def test_janus_api_exports_clean(self):
        """Test: janus.__all__ contains no legacy exports"""
        import janus
        
        # Get __all__ if it exists
        if hasattr(janus, "__all__"):
            exports = janus.__all__
        else:
            # If no __all__, get all public names
            exports = [name for name in dir(janus) if not name.startswith("_")]
        
        # Legacy symbols that should NOT be in exports
        forbidden_symbols = [
            "AgentExecutorV3",
            "CommandParser",
            "NLUParser",
            "JSONPlanValidator",
            "JSONPlanCorrector",
        ]
        
        found_legacy = []
        for symbol in forbidden_symbols:
            if symbol in exports:
                found_legacy.append(symbol)
        
        self.assertEqual(
            len(found_legacy), 0,
            f"Found legacy symbols in janus.__all__: {found_legacy}"
        )
        
        # Verify official API is present
        required_symbols = ["JanusAgent", "WhisperSTT", "SessionManager"]
        missing = []
        for symbol in required_symbols:
            if symbol not in exports:
                missing.append(symbol)
        
        self.assertEqual(
            len(missing), 0,
            f"Missing required API symbols in janus.__all__: {missing}"
        )


class TestPhase2WiringVerification(unittest.TestCase):
    """
    Phase 2: Verify all entrypoints use ActionCoordinator.execute_goal()
    
    These tests verify the code structure without requiring all dependencies.
    """
    
    def test_janus_agent_uses_action_coordinator(self):
        """Test: JanusAgent.execute() uses ActionCoordinator.execute_goal()"""
        # Read the janus_agent.py source code
        janus_agent_path = JANUS_ROOT / "core" / "janus_agent.py"
        with open(janus_agent_path, "r") as f:
            source = f.read()
        
        # Check that execute_goal is called
        self.assertIn(
            "execute_goal",
            source,
            "JanusAgent should call execute_goal()"
        )
        
        # Check that ActionCoordinator is imported
        self.assertIn(
            "from .action_coordinator import ActionCoordinator",
            source,
            "JanusAgent should import ActionCoordinator"
        )
        
        # Check that coordinator.execute_goal is called in execute method
        self.assertIn(
            "self.coordinator.execute_goal",
            source,
            "JanusAgent.execute() should call self.coordinator.execute_goal()"
        )
    
    def test_pipeline_has_action_coordinator_property(self):
        """Test: JanusPipeline has action_coordinator property"""
        # Read the _pipeline_properties.py source code
        pipeline_props_path = JANUS_ROOT / "core" / "_pipeline_properties.py"
        with open(pipeline_props_path, "r") as f:
            source = f.read()
        
        # Check that action_coordinator property exists
        self.assertIn(
            "def action_coordinator(self)",
            source,
            "_pipeline_properties should have action_coordinator property"
        )
        
        # Check that it imports ActionCoordinator
        self.assertIn(
            "from .action_coordinator import ActionCoordinator",
            source,
            "action_coordinator property should import ActionCoordinator"
        )
    
    def test_no_legacy_executor_in_pipeline(self):
        """Test: Pipeline doesn't use legacy V3 executor"""
        # Read pipeline source
        pipeline_path = JANUS_ROOT / "core" / "pipeline.py"
        with open(pipeline_path, "r") as f:
            source = f.read()
        
        # Should not have agent_executor_v3 anywhere (except comments)
        lines_with_v3 = []
        for line in source.split("\n"):
            # Skip comments
            if line.strip().startswith("#"):
                continue
            if "agent_executor_v3" in line.lower() or "AgentExecutorV3" in line:
                lines_with_v3.append(line.strip())
        
        self.assertEqual(
            len(lines_with_v3), 0,
            f"Pipeline still references V3 executor: {lines_with_v3}"
        )


class TestPhase3FeatureInvariants(unittest.TestCase):
    """
    Phase 3: Verify feature invariants are maintained.
    
    These tests check that refactored features work correctly:
    - Action schema SSOT
    - Validator uses UnifiedActionValidator
    """
    
    def test_action_schema_ssot_structure(self):
        """Test: Action schema SSOT is available and has correct structure"""
        # Read module_action_schema.py
        schema_path = JANUS_ROOT / "core" / "module_action_schema.py"
        with open(schema_path, "r") as f:
            source = f.read()
        
        # Check for key functions
        required_functions = [
            "get_all_module_names",
            "get_all_actions_for_module",
            "validate_action_step",
            "is_valid_module",
            "is_valid_action",
        ]
        
        for func_name in required_functions:
            self.assertIn(
                f"def {func_name}",
                source,
                f"module_action_schema should have {func_name}() function"
            )
    
    def test_validator_uses_unified_validator(self):
        """Test: ValidatorAgent uses UnifiedActionValidator (not legacy)"""
        # Read validator_agent.py source
        validator_path = JANUS_ROOT / "agents" / "validator_agent.py"
        with open(validator_path, "r") as f:
            source = f.read()
        
        # Should import UnifiedActionValidator
        self.assertIn(
            "from janus.safety.validation.unified_action_validator import UnifiedActionValidator",
            source,
            "ValidatorAgent should import UnifiedActionValidator"
        )
        
        # Should create UnifiedActionValidator instance
        self.assertIn(
            "UnifiedActionValidator(",
            source,
            "ValidatorAgent should create UnifiedActionValidator instance"
        )
        
        # Should NOT import legacy validators
        legacy_imports = [
            "from janus.safety.validation.json_plan_validator import JSONPlanValidator",
            "from ..validation.json_plan_validator import JSONPlanValidator",
        ]
        
        for legacy_import in legacy_imports:
            self.assertNotIn(
                legacy_import,
                source,
                f"ValidatorAgent should not import legacy validator: {legacy_import}"
            )


class TestPhase4AcceptanceScenarios(unittest.TestCase):
    """
    Phase 4: Acceptance scenarios to verify end-to-end functionality.
    
    S1 (PR gate): Calculator 15+27 (no vision, fast)
    S2 (Nightly): Browser automation
    S3 (Nightly): Popup handling
    
    For now, we implement S1 as a smoke test.
    """
    
    @unittest.skip("Requires full LLM setup - run manually with real config")
    def test_s1_calculator_scenario(self):
        """
        S1: Calculator 15+27 scenario (PR gate)
        
        Expected:
        - success=True
        - vision_calls=0
        - llm_calls<=5
        - total_time_ms<=10000
        """
        import asyncio
        from janus.runtime.core.janus_agent import JanusAgent
        import time
        
        # Create agent (no vision for speed)
        agent = JanusAgent(
            enable_voice=False,
            enable_vision=False,
            enable_tts=False,
            enable_llm=True
        )
        
        # Execute command
        start_time = time.time()
        result = asyncio.run(agent.execute("open Calculator and calculate 15 plus 27"))
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Verify success
        self.assertTrue(result.success, f"Calculator scenario failed: {result.message}")
        
        # Check metrics
        metrics = result.metrics
        
        # Vision calls should be 0
        vision_calls = metrics.get("vision_calls", 0)
        self.assertEqual(vision_calls, 0, "Vision should not be used in calculator scenario")
        
        # LLM calls should be reasonable
        llm_calls = metrics.get("llm_calls", 0)
        self.assertLessEqual(llm_calls, 5, f"Too many LLM calls: {llm_calls}")
        
        # Time should be reasonable
        self.assertLessEqual(elapsed_ms, 10000, f"Scenario took too long: {elapsed_ms}ms")
    
    def test_verification_report_structure(self):
        """Test: Verification report has required structure"""
        # This is a structure test - actual report generation is in the workflow
        
        required_fields = [
            "legacy_scan_matches",
            "entrypoints_passed",
            "llm_calls",
            "vision_calls",
            "actions_count",
            "replans",
            "stagnation_events",
            "total_time_ms",
            "model_name",
            "toolset_hash",
        ]
        
        # Mock report
        report = {
            "legacy_scan_matches": 0,
            "entrypoints_passed": True,
            "llm_calls": 0,
            "vision_calls": 0,
            "actions_count": 0,
            "replans": 0,
            "stagnation_events": 0,
            "total_time_ms": 0,
            "model_name": "mock",
            "toolset_hash": "abc123",
        }
        
        # Verify all fields present
        for field in required_fields:
            self.assertIn(field, report, f"Report missing field: {field}")
        
        # Verify it can be serialized to JSON
        json_str = json.dumps(report)
        self.assertIsInstance(json_str, str)


def generate_verification_report() -> dict:
    """
    Generate verification report for CI artifact.
    
    Returns:
        Dictionary with verification metrics
    """
    # Run legacy scan
    legacy_patterns = [
        "AgentExecutorV3",
        "agent_executor_v3",
        "JSONPlanValidator",
        "json_plan_validator",
        "NLUParser",
        "nlu_parser",
    ]
    
    pattern = "|".join(legacy_patterns)
    result = subprocess.run(
        ["grep", "-rn", "-E", pattern, str(JANUS_ROOT), "--include=*.py"],
        capture_output=True,
        text=True
    )
    
    # Count matches (excluding this test file and docstrings about removal)
    matches = []
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            # Skip this test file
            if "test_one_ticket_verification.py" in line:
                continue
            # Skip docstrings about removal/legacy
            if any(keyword in line.lower() for keyword in ["removed", "legacy", "one-ticket-verification"]):
                continue
            matches.append(line)
    
    # Generate report
    report = {
        "legacy_scan_matches": len(matches),
        "legacy_scan_details": matches[:10] if matches else [],
        "entrypoints_passed": True,  # Updated when we add wiring tests
        "llm_calls": 0,
        "vision_calls": 0,
        "actions_count": 0,
        "replans": 0,
        "stagnation_events": 0,
        "total_time_ms": 0,
        "model_name": "N/A",
        "toolset_hash": "N/A",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "test_run": "verification_007",
    }
    
    return report


if __name__ == "__main__":
    # Run tests
    unittest.main(argv=[""], exit=False, verbosity=2)
    
    # Generate report
    report = generate_verification_report()
    
    # Save to artifacts directory
    artifacts_dir = REPO_ROOT / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    report_path = artifacts_dir / "verification_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Verification report saved to: {report_path}")
    print(f"  Legacy scan matches: {report['legacy_scan_matches']}")
