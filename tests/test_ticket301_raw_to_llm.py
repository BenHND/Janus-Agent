"""
Test for TICKET-301: Raw-to-LLM Architecture
Verify that raw commands (with typos, fillers, etc.) are passed directly to ReasonerLLM
"""

import sys
import unittest
from unittest.mock import MagicMock

from janus.runtime.core import MemoryEngine
from janus.runtime.core.pipeline import JanusPipeline
from janus.runtime.core.settings import Settings


class TestTicket301RawToLLM(unittest.TestCase):
    """Test Raw-to-LLM architecture without ParserAgent preprocessing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = Settings()
        self.memory = MemoryEngine(self.settings.database)
    
    @staticmethod
    def _extract_command_arg(mock_reasoner):
        """
        Helper method to extract command argument from ReasonerLLM mock call.
        
        Args:
            mock_reasoner: Mock ReasonerLLM object
            
        Returns:
            str: The command argument passed to generate_structured_plan
            
        Raises:
            AssertionError: If the mock was not called, no call arguments were found,
                          or the command argument cannot be extracted from either
                          keyword or positional arguments
        """
        if not mock_reasoner.generate_structured_plan.called:
            raise AssertionError("ReasonerLLM.generate_structured_plan was not called")
        
        call_args = mock_reasoner.generate_structured_plan.call_args
        if not call_args:
            raise AssertionError("No call arguments found")
        
        # Try keyword argument first
        if len(call_args) > 1 and 'command' in call_args[1]:
            return call_args[1]['command']
        # Try positional argument
        elif len(call_args) > 0 and len(call_args[0]) > 0:
            return call_args[0][0]
        else:
            raise AssertionError("Could not extract command argument from call")
    
    @staticmethod
    def _extract_language_arg(mock_reasoner):
        """
        Helper method to extract language argument from ReasonerLLM mock call.
        
        Args:
            mock_reasoner: Mock ReasonerLLM object
            
        Returns:
            str or None: The language argument passed to generate_structured_plan.
                        Returns None if the mock wasn't called, no call arguments
                        were found, or no language argument was provided (which is
                        the expected behavior for LLM auto-detection).
        """
        if not mock_reasoner.generate_structured_plan.called:
            return None
        
        call_args = mock_reasoner.generate_structured_plan.call_args
        if not call_args:
            return None
        
        # Try keyword argument
        if len(call_args) > 1:
            return call_args[1].get('language')
        return None
        
    def test_raw_command_reaches_llm_unmodified(self):
        """Test that raw commands reach ReasonerLLM without preprocessing"""
        pipeline = JanusPipeline(
            settings=self.settings,
            memory=self.memory,
            enable_voice=False,
            enable_llm_reasoning=True,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # Mock the ReasonerLLM to capture what command it receives
        mock_reasoner = MagicMock()
        mock_reasoner.generate_structured_plan.return_value = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Safari"},
                    "context": {},
                }
            ]
        }
        pipeline._reasoner_llm = mock_reasoner
        
        # Mock the validator
        mock_validator = MagicMock()
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.warnings = []
        mock_validation_result.plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Safari"},
                    "context": {},
                }
            ]
        }
        mock_validator.validate_plan.return_value = mock_validation_result
        pipeline._validator_v3 = mock_validator
        
        # Mock the executor
        mock_executor = MagicMock()
        mock_exec_result = MagicMock()
        mock_exec_result.success = True
        mock_exec_result.action_results = []
        mock_exec_result.intent = None
        mock_executor.execute_plan.return_value = mock_exec_result
        pipeline._agent_executor_v3 = mock_executor
        
        # Test with raw command containing typos and fillers (as per issue example)
        raw_command = "Ouvrer safari et va sur youtube"
        
        try:
            result = pipeline.process_command(raw_command, mock_execution=False)
        except Exception as e:
            print(f"Exception during processing: {e}")
        
        # Verify ReasonerLLM was called
        self.assertTrue(mock_reasoner.generate_structured_plan.called)
        
        # Get the command that was passed to ReasonerLLM using helper
        command_arg = self._extract_command_arg(mock_reasoner)
        
        # CRITICAL: Command should be RAW, not preprocessed
        # Should contain the typo "Ouvrer" (not corrected to "Ouvre")
        # Should contain original text
        self.assertEqual(command_arg, raw_command, 
                        "Command was preprocessed! Should be passed raw to LLM.")
        
        print(f"✓ Raw command passed to LLM: '{command_arg}'")
    
    def test_complex_command_with_fillers(self):
        """Test complex command with fillers reaches LLM unmodified"""
        pipeline = JanusPipeline(
            settings=self.settings,
            memory=self.memory,
            enable_voice=False,
            enable_llm_reasoning=True,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # Mock components
        mock_reasoner = MagicMock()
        mock_reasoner.generate_structured_plan.return_value = {"steps": []}
        pipeline._reasoner_llm = mock_reasoner
        
        mock_validator = MagicMock()
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.warnings = []
        mock_validation_result.plan = {"steps": []}
        mock_validator.validate_plan.return_value = mock_validation_result
        pipeline._validator_v3 = mock_validator
        
        mock_executor = MagicMock()
        mock_exec_result = MagicMock()
        mock_exec_result.success = True
        mock_exec_result.action_results = []
        mock_exec_result.intent = None
        mock_executor.execute_plan.return_value = mock_exec_result
        pipeline._agent_executor_v3 = mock_executor
        
        # Test with complex command from issue (with fillers)
        raw_command = "Check mes mails et si y'a un truc de Paul dis le moi"
        
        try:
            pipeline.process_command(raw_command, mock_execution=False)
        except Exception:
            pass
        
        # Get command passed to LLM using helper
        command_arg = self._extract_command_arg(mock_reasoner)
        
        # Should be unchanged
        self.assertEqual(command_arg, raw_command)
        print(f"✓ Complex command passed raw to LLM: '{command_arg}'")
    
    def test_language_auto_detection_by_llm(self):
        """Test that language is auto-detected by LLM (not preprocessor)"""
        pipeline = JanusPipeline(
            settings=self.settings,
            memory=self.memory,
            enable_voice=False,
            enable_llm_reasoning=True,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # Mock components
        mock_reasoner = MagicMock()
        mock_reasoner.generate_structured_plan.return_value = {"steps": []}
        pipeline._reasoner_llm = mock_reasoner
        
        mock_validator = MagicMock()
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.warnings = []
        mock_validation_result.plan = {"steps": []}
        mock_validator.validate_plan.return_value = mock_validation_result
        pipeline._validator_v3 = mock_validator
        
        mock_executor = MagicMock()
        mock_exec_result = MagicMock()
        mock_exec_result.success = True
        mock_exec_result.action_results = []
        mock_exec_result.intent = None
        mock_executor.execute_plan.return_value = mock_exec_result
        pipeline._agent_executor_v3 = mock_executor
        
        try:
            pipeline.process_command("Ouvre Safari", mock_execution=False)
        except Exception:
            pass
        
        # Check language parameter using helper
        language_arg = self._extract_language_arg(mock_reasoner)
        
        # Language should be None (auto-detect by LLM)
        self.assertIsNone(language_arg, 
                         "Language should be None to allow LLM auto-detection")
        print(f"✓ Language set to None for LLM auto-detection")
    
    def test_parser_agent_removed(self):
        """Test that ParserAgent is no longer in pipeline"""
        pipeline = JanusPipeline(
            settings=self.settings,
            memory=self.memory,
            enable_voice=False,
            enable_llm_reasoning=True,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # ParserAgent should not exist
        self.assertFalse(hasattr(pipeline, '_parser_agent'),
                        "Pipeline should not have _parser_agent attribute")
        
        # parser_agent property should not exist
        self.assertFalse(hasattr(type(pipeline), 'parser_agent'),
                        "Pipeline should not have parser_agent property")
        
        print("✓ ParserAgent successfully removed from pipeline")


if __name__ == "__main__":
    unittest.main(verbosity=2)
