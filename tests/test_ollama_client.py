"""
Tests for Ollama Client
Tests model management, streaming, GPU detection, and API interactions
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

from janus.ai.llm.ollama_client import OllamaClient


class TestOllamaClientInitialization(unittest.TestCase):
    """Test Ollama client initialization"""

    def test_initialization_with_defaults(self):
        """Test client initialization with default parameters"""
        client = OllamaClient()
        self.assertIsNotNone(client.base_url)
        self.assertIsNotNone(client.timeout)

    def test_initialization_with_custom_params(self):
        """Test client initialization with custom parameters"""
        client = OllamaClient(
            base_url="http://custom:11434",
            timeout=60,
        )
        self.assertEqual(client.base_url, "http://custom:11434")
        self.assertEqual(client.timeout, 60)


class TestOllamaServerAvailability(unittest.TestCase):
    """Test Ollama server availability checking"""

    @patch("requests.get")
    def test_is_available_success(self, mock_get):
        """Test successful server availability check"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = OllamaClient()
        self.assertTrue(client.is_available())

    @patch("requests.get")
    def test_is_available_failure(self, mock_get):
        """Test failed server availability check"""
        mock_get.side_effect = Exception("Connection refused")

        client = OllamaClient()
        self.assertFalse(client.is_available())

    @patch("requests.get")
    def test_is_available_caching(self, mock_get):
        """Test that availability is cached"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = OllamaClient()
        # First call
        self.assertTrue(client.is_available())
        # Second call should use cached value
        self.assertTrue(client.is_available())
        # Should only call once due to caching
        self.assertEqual(mock_get.call_count, 1)


class TestModelManagement(unittest.TestCase):
    """Test model management operations"""

    @patch("requests.get")
    def test_list_models_success(self, mock_get):
        """Test successful model listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "mistral:7b", "size": 4700000000},
                {"name": "llama2:7b", "size": 3800000000},
            ]
        }
        mock_get.return_value = mock_response

        client = OllamaClient()
        models = client.list_models()

        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["name"], "mistral:7b")

    @patch("requests.get")
    def test_list_models_empty(self, mock_get):
        """Test listing models when none are available"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_get.return_value = mock_response

        client = OllamaClient()
        models = client.list_models()

        self.assertEqual(len(models), 0)

    @patch("requests.get")
    def test_model_exists_true(self, mock_get):
        """Test checking if a model exists"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "mistral:7b"}]
        }
        mock_get.return_value = mock_response

        client = OllamaClient()
        self.assertTrue(client.model_exists("mistral:7b"))

    @patch("requests.get")
    def test_model_exists_false(self, mock_get):
        """Test checking for non-existent model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "mistral:7b"}]
        }
        mock_get.return_value = mock_response

        client = OllamaClient()
        self.assertFalse(client.model_exists("llama2:7b"))

    @patch("requests.delete")
    def test_delete_model_success(self, mock_delete):
        """Test successful model deletion"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        client = OllamaClient()
        success, message = client.delete_model("mistral:7b")

        self.assertTrue(success)
        self.assertIn("Successfully deleted", message)

    @patch("requests.delete")
    def test_delete_model_not_found(self, mock_delete):
        """Test deleting non-existent model"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_delete.return_value = mock_response
        mock_delete.return_value.raise_for_status = Mock(
            side_effect=Exception("404")
        )

        client = OllamaClient()
        success, message = client.delete_model("nonexistent:7b")

        self.assertFalse(success)

    @patch("requests.get")
    def test_model_exists_exact_match(self, mock_get):
        """Test exact model name matching"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "mistral:7b"}]
        }
        mock_get.return_value = mock_response

        client = OllamaClient()
        # Exact match should work
        self.assertTrue(client.model_exists("mistral:7b"))
        # Partial match should not work
        self.assertFalse(client.model_exists("mistral:13b"))

    @patch("requests.get")
    def test_model_exists_prefix_match(self, mock_get):
        """Test prefix model name matching for base model names"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "mistral:7b-instruct-q4"}]
        }
        mock_get.return_value = mock_response

        client = OllamaClient()
        # Prefix match should work
        self.assertTrue(client.model_exists("mistral"))
        # But not for unrelated models
        self.assertFalse(client.model_exists("llama2"))


class TestModelInference(unittest.TestCase):
    """Test model inference operations"""

    @patch("requests.post")
    def test_generate_non_streaming(self, mock_post):
        """Test non-streaming text generation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Test response",
            "done": True,
        }
        mock_post.return_value = mock_response

        client = OllamaClient()
        results = list(client.generate(
            model="mistral:7b",
            prompt="Test prompt",
            stream=False,
        ))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["response"], "Test response")

    @patch("requests.post")
    def test_chat_non_streaming(self, mock_post):
        """Test non-streaming chat completion"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "Hello!"},
            "done": True,
        }
        mock_post.return_value = mock_response

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hi"}]
        results = list(client.chat(
            model="mistral:7b",
            messages=messages,
            stream=False,
        ))

        self.assertEqual(len(results), 1)
        self.assertIn("message", results[0])

    @patch("requests.post")
    def test_generate_with_options(self, mock_post):
        """Test generation with custom options"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test", "done": True}
        mock_post.return_value = mock_response

        client = OllamaClient()
        options = {"temperature": 0.9, "top_p": 0.95}
        list(client.generate(
            model="mistral:7b",
            prompt="Test",
            stream=False,
            options=options,
        ))

        # Verify options were passed
        call_args = mock_post.call_args
        self.assertIn("options", call_args[1]["json"])


class TestGPUDetection(unittest.TestCase):
    """Test GPU detection functionality"""

    @patch("subprocess.run")
    def test_detect_nvidia_gpu(self, mock_run):
        """Test NVIDIA GPU detection"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "NVIDIA GeForce RTX 3080, 10240 MiB"
        mock_run.return_value = mock_result

        client = OllamaClient()
        gpu_info = client.detect_gpu()

        self.assertTrue(gpu_info["available"])
        self.assertEqual(gpu_info["type"], "cuda")
        self.assertGreater(len(gpu_info["devices"]), 0)

    @patch("subprocess.run")
    def test_detect_no_gpu(self, mock_run):
        """Test detection when no GPU is available"""
        mock_run.side_effect = FileNotFoundError()

        client = OllamaClient()
        gpu_info = client.detect_gpu()

        self.assertFalse(gpu_info["available"])

    @patch("subprocess.run")
    @patch("platform.system")
    def test_detect_apple_silicon(self, mock_system, mock_run):
        """Test Apple Silicon GPU detection"""
        mock_system.return_value = "Darwin"
        
        # First call is for nvidia-smi (should fail)
        # Second call is for sysctl (should succeed)
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if "nvidia-smi" in cmd:
                raise FileNotFoundError()
            elif "sysctl" in cmd:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "Apple M1 Pro"
                return mock_result
            else:
                raise FileNotFoundError()
        
        mock_run.side_effect = run_side_effect

        client = OllamaClient()
        gpu_info = client.detect_gpu()

        self.assertTrue(gpu_info["available"])
        self.assertEqual(gpu_info["type"], "metal")

    def test_gpu_detection_caching(self):
        """Test that GPU detection is cached"""
        client = OllamaClient()
        
        # Set cached value
        client._gpu_info = {"available": True, "type": "test"}
        
        # Second call should return cached value
        gpu_info = client.detect_gpu()
        self.assertEqual(gpu_info["type"], "test")


class TestRecommendedOptions(unittest.TestCase):
    """Test recommended options generation"""

    def test_get_recommended_options_cpu_only(self):
        """Test recommended options for CPU-only setup"""
        client = OllamaClient()
        gpu_info = {"available": False}
        
        options = client.get_recommended_options(gpu_info)
        
        self.assertIn("num_thread", options)
        self.assertNotIn("num_gpu", options)

    def test_get_recommended_options_with_cuda(self):
        """Test recommended options with CUDA GPU"""
        client = OllamaClient()
        gpu_info = {
            "available": True,
            "type": "cuda",
            "devices": [{"name": "RTX 3080"}],
        }
        
        options = client.get_recommended_options(gpu_info)
        
        self.assertIn("num_gpu", options)
        self.assertEqual(options["num_gpu"], 1)

    def test_get_recommended_options_auto_detect(self):
        """Test auto-detection in recommended options"""
        client = OllamaClient()
        # Should auto-detect GPU
        options = client.get_recommended_options()
        
        self.assertIn("num_thread", options)


class TestModelInfo(unittest.TestCase):
    """Test model information retrieval"""

    @patch("requests.post")
    def test_get_model_info_success(self, mock_post):
        """Test successful model info retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "modelfile": "test",
            "parameters": "test",
            "template": "test",
        }
        mock_post.return_value = mock_response

        client = OllamaClient()
        info = client.get_model_info("mistral:7b")

        self.assertIsNotNone(info)
        self.assertIn("modelfile", info)

    @patch("requests.post")
    def test_get_model_info_failure(self, mock_post):
        """Test model info retrieval failure"""
        mock_post.side_effect = Exception("Model not found")

        client = OllamaClient()
        info = client.get_model_info("nonexistent:7b")

        self.assertIsNone(info)


class TestEmbeddings(unittest.TestCase):
    """Test embeddings generation"""

    @patch("requests.post")
    def test_embeddings_success(self, mock_post):
        """Test successful embeddings generation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
        }
        mock_post.return_value = mock_response

        client = OllamaClient()
        embeddings = client.embeddings(
            model="mistral:7b",
            prompt="Test text",
        )

        self.assertIsNotNone(embeddings)
        self.assertEqual(len(embeddings), 5)

    @patch("requests.post")
    def test_embeddings_failure(self, mock_post):
        """Test embeddings generation failure"""
        mock_post.side_effect = Exception("Error")

        client = OllamaClient()
        embeddings = client.embeddings(
            model="mistral:7b",
            prompt="Test",
        )

        self.assertIsNone(embeddings)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in various scenarios"""

    @patch("requests.get")
    def test_list_models_error_handling(self, mock_get):
        """Test error handling in list_models"""
        mock_get.side_effect = Exception("Connection error")

        client = OllamaClient()
        models = client.list_models()

        self.assertEqual(len(models), 0)

    @patch("requests.post")
    def test_generate_error_handling(self, mock_post):
        """Test error handling in generate"""
        mock_post.side_effect = Exception("Generation error")

        client = OllamaClient()
        results = list(client.generate(
            model="test",
            prompt="test",
            stream=False,
        ))

        self.assertEqual(len(results), 1)
        self.assertIn("error", results[0])


class TestOllamaPerformanceLogging(unittest.TestCase):
    """Test Ollama performance logging (TICKET-ARCHI)"""
    
    @patch("requests.post")
    def test_tokens_per_second_logged(self, mock_post):
        """Test that tokens/second is calculated and logged (TICKET-ARCHI)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "test",
            "eval_count": 100,  # 100 output tokens
            "prompt_eval_count": 50,
            "total_duration": 10_000_000_000,  # 10 seconds in nanoseconds
            "done": True,
        }
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        with self.assertLogs(client.logger, level='INFO') as log:
            list(client.generate(
                model="test",
                prompt="test",
                stream=False,
            ))
            
            # Check that tokens/s is logged
            log_output = '\n'.join(log.output)
            self.assertIn("tokens/s", log_output)
            # Should log 10 tokens/s (100 tokens / 10 seconds)
            self.assertIn("10.0 tokens/s", log_output)
    
    @patch("requests.post")
    def test_slow_performance_warning(self, mock_post):
        """Test that slow performance triggers a warning (TICKET-ARCHI)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "test",
            "eval_count": 100,  # 100 output tokens
            "prompt_eval_count": 50,
            "total_duration": 20_000_000_000,  # 20 seconds = 5 tokens/s (very slow!)
            "done": True,
        }
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        with self.assertLogs(client.logger, level='WARNING') as log:
            list(client.generate(
                model="test",
                prompt="test",
                stream=False,
            ))
            
            # Should have warning about low speed
            log_output = '\n'.join(log.output)
            self.assertIn("Low inference speed", log_output)
            self.assertIn("5.0 tokens/s", log_output)


if __name__ == "__main__":
    unittest.main()
