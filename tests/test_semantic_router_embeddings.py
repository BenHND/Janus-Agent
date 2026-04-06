"""
Tests for SemanticRouter embedding-based classification (TICKET-ROUTER-001)
"""
import unittest
from unittest.mock import patch, MagicMock

from janus.ai.reasoning.semantic_router import SemanticRouter, EMBEDDINGS_AVAILABLE


@unittest.skipIf(not EMBEDDINGS_AVAILABLE, "Embeddings not available")
class TestSemanticRouterEmbeddings(unittest.TestCase):
    """Test SemanticRouter with embedding-based classification"""

    def setUp(self):
        """Set up test SemanticRouter with embeddings enabled"""
        self.router = SemanticRouter(reasoner=None, enable_embeddings=True)

    def test_initialization_with_embeddings(self):
        """Test SemanticRouter initialization with embeddings"""
        self.assertTrue(self.router._use_embeddings)
        self.assertIsNotNone(self.router._embedding_model)
        self.assertIsNotNone(self.router._centroids)
        self.assertEqual(len(self.router._centroids), 3)
        self.assertIn("NOISE", self.router._centroids)
        self.assertIn("CHAT", self.router._centroids)
        self.assertIn("ACTION", self.router._centroids)

    def test_acceptance_criteria_franglais(self):
        """
        Test acceptance criteria: 'Peux-tu check mes mails' (franglais) 
        should be classified as ACTION
        """
        result = self.router.classify_intent("Peux-tu check mes mails")
        self.assertEqual(result, "ACTION")

    def test_franglais_variations(self):
        """Test various franglais expressions for ACTION classification"""
        franglais_actions = [
            "Peux-tu check mes mails",
            "Check mes emails",
            "Ouvre mon browser",
            "Lance le terminal et run mon script",
        ]
        for text in franglais_actions:
            with self.subTest(input=text):
                result = self.router.classify_intent(text)
                self.assertEqual(result, "ACTION", f"Failed for: '{text}'")

    def test_embedding_noise_classification(self):
        """Test embedding-based NOISE classification"""
        noise_inputs = [
            "Merci",
            "Bonjour",
            "Ok",
            "D'accord",
            "Thanks",
            "Hello",
        ]
        for text in noise_inputs:
            with self.subTest(input=text):
                result = self.router.classify_intent(text)
                self.assertEqual(result, "NOISE", f"Failed for: '{text}'")

    def test_embedding_chat_classification(self):
        """Test embedding-based CHAT classification"""
        chat_inputs = [
            "Qui est le président",
            "Comment faire un gâteau",
            "Raconte une blague",
            "What is the weather",
        ]
        for text in chat_inputs:
            with self.subTest(input=text):
                result = self.router.classify_intent(text)
                self.assertEqual(result, "CHAT", f"Failed for: '{text}'")

    def test_embedding_action_classification(self):
        """Test embedding-based ACTION classification"""
        action_inputs = [
            "Ouvre Chrome",
            "Ferme Safari",
            "Cherche sur Google",
            "Envoie un email",
            "Open Chrome",
            "Close Safari",
        ]
        for text in action_inputs:
            with self.subTest(input=text):
                result = self.router.classify_intent(text)
                self.assertEqual(result, "ACTION", f"Failed for: '{text}'")

    def test_embedding_similarity_computation(self):
        """Test that _classify_with_embeddings returns a valid category"""
        result = self.router._classify_with_embeddings("Ouvre Chrome")
        self.assertIn(result, ["NOISE", "CHAT", "ACTION"])


class TestSemanticRouterEmbeddingsFallback(unittest.TestCase):
    """Test SemanticRouter behavior when embeddings are not available"""

    @patch('janus.reasoning.semantic_router.EMBEDDINGS_AVAILABLE', False)
    def test_initialization_without_embeddings(self):
        """Test SemanticRouter gracefully falls back when embeddings unavailable"""
        router = SemanticRouter(reasoner=None, enable_embeddings=True)
        self.assertFalse(router._use_embeddings)
        self.assertIsNone(router._embedding_model)
        self.assertIsNone(router._centroids)

    @patch('janus.reasoning.semantic_router.EMBEDDINGS_AVAILABLE', False)
    def test_fallback_to_keywords_when_embeddings_unavailable(self):
        """Test that keyword-based classification works when embeddings unavailable"""
        router = SemanticRouter(reasoner=None, enable_embeddings=True)
        result = router.classify_intent("Ouvre Safari")
        self.assertEqual(result, "ACTION")


class TestSemanticRouterEmbeddingsDisabled(unittest.TestCase):
    """Test SemanticRouter with embeddings explicitly disabled"""

    def test_initialization_embeddings_disabled(self):
        """Test SemanticRouter initialization with embeddings disabled"""
        router = SemanticRouter(reasoner=None, enable_embeddings=False)
        self.assertFalse(router._use_embeddings)
        self.assertIsNone(router._embedding_model)
        self.assertIsNone(router._centroids)

    def test_classification_with_embeddings_disabled(self):
        """Test classification falls back to keywords when embeddings disabled"""
        router = SemanticRouter(reasoner=None, enable_embeddings=False)
        result = router.classify_intent("Ouvre Safari")
        self.assertEqual(result, "ACTION")


if __name__ == "__main__":
    unittest.main()
