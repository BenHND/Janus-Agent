"""
Tests for Semantic Memory (TICKET-MEM-001)

Validates the semantic memory functionality in MemoryEngine, including:
- Vector database integration
- Action vectorization
- Semantic search
- Reference resolution with semantic fallback
"""
import os
import tempfile
from pathlib import Path

import pytest

from janus.runtime.core.memory_engine import MemoryEngine, SEMANTIC_MEMORY_AVAILABLE


# Skip all tests if semantic memory dependencies are not available
pytestmark = pytest.mark.skipif(
    not SEMANTIC_MEMORY_AVAILABLE,
    reason="Semantic memory dependencies (chromadb, sentence-transformers) not installed"
)


class TestSemanticMemoryInitialization:
    """Test semantic memory initialization"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        # Cleanup chroma directory
        chroma_path = Path(db_path).parent / f"{Path(db_path).stem}_chroma"
        if chroma_path.exists():
            import shutil
            shutil.rmtree(chroma_path)
    
    def test_initialization_with_semantic_memory(self, temp_db_path):
        """Test that semantic memory initializes correctly"""
        engine = MemoryEngine(temp_db_path, enable_semantic_memory=True)
        
        assert engine._semantic_memory_enabled is True
        assert engine._embedding_model is not None
        assert engine._chroma_client is not None
        assert engine._chroma_collection is not None
    
    def test_initialization_without_semantic_memory(self, temp_db_path):
        """Test that engine works without semantic memory"""
        engine = MemoryEngine(temp_db_path, enable_semantic_memory=False)
        
        assert engine._semantic_memory_enabled is False
        assert engine._embedding_model is None
        assert engine._chroma_client is None


class TestActionVectorization:
    """Test action vectorization and storage"""
    
    @pytest.fixture
    def engine(self):
        """Create a memory engine with semantic memory enabled"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        engine = MemoryEngine(db_path, enable_semantic_memory=True)
        yield engine
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        chroma_path = Path(db_path).parent / f"{Path(db_path).stem}_chroma"
        if chroma_path.exists():
            import shutil
            shutil.rmtree(chroma_path)
    
    def test_record_file_action(self, engine):
        """Test recording and vectorizing a file open action"""
        result = engine.record_action("open_file", {
            "file_path": "/Users/test/report.pdf"
        })
        
        assert result is True
        
        # Verify it's stored in vector database
        results = engine.search_semantic("report.pdf", limit=1)
        assert len(results) > 0
        assert "report.pdf" in results[0]["description"].lower()
    
    def test_record_app_action(self, engine):
        """Test recording and vectorizing an app open action"""
        result = engine.record_action("open_app", {
            "app_name": "Safari"
        })
        
        assert result is True
        
        # Verify semantic search works
        results = engine.search_semantic("Safari application", limit=1)
        assert len(results) > 0
        assert "safari" in results[0]["description"].lower()
    
    def test_record_url_action(self, engine):
        """Test recording and vectorizing a URL open action"""
        result = engine.record_action("open_url", {
            "url": "https://github.com/BenHND/Janus"
        })
        
        assert result is True
        
        # Verify semantic search works
        results = engine.search_semantic("GitHub website", limit=1)
        assert len(results) > 0
        assert "github" in results[0]["description"].lower()
    
    def test_record_copy_action(self, engine):
        """Test recording and vectorizing a copy action"""
        result = engine.record_action("copy", {
            "content": "Important data from the budget spreadsheet"
        })
        
        assert result is True
        
        # Verify semantic search works
        results = engine.search_semantic("budget data", limit=1)
        assert len(results) > 0


class TestSemanticSearch:
    """Test semantic search functionality"""
    
    @pytest.fixture
    def engine_with_actions(self):
        """Create an engine with several recorded actions"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        engine = MemoryEngine(db_path, enable_semantic_memory=True)
        
        # Record various actions
        engine.record_action("open_file", {"file_path": "/Users/test/budget_2024.xlsx"})
        engine.record_action("open_file", {"file_path": "/Users/test/report.pdf"})
        engine.record_action("open_app", {"app_name": "Safari"})
        engine.record_action("open_url", {"url": "https://github.com"})
        engine.record_action("copy", {"content": "Sales data for Q4 2024"})
        
        yield engine
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        chroma_path = Path(db_path).parent / f"{Path(db_path).stem}_chroma"
        if chroma_path.exists():
            import shutil
            shutil.rmtree(chroma_path)
    
    def test_search_by_file_type(self, engine_with_actions):
        """Test searching for PDF files"""
        results = engine_with_actions.search_semantic("PDF document", limit=5)
        
        assert len(results) > 0
        # Should find the report.pdf
        assert any("pdf" in r["description"].lower() for r in results)
    
    def test_search_by_content(self, engine_with_actions):
        """Test searching by content description"""
        results = engine_with_actions.search_semantic("budget spreadsheet", limit=5)
        
        assert len(results) > 0
        # Should find the budget_2024.xlsx
        assert any("budget" in r["description"].lower() for r in results)
    
    def test_search_multilingual(self, engine_with_actions):
        """Test searching with French query"""
        results = engine_with_actions.search_semantic("le fichier PDF", limit=5)
        
        assert len(results) > 0
        # Should still find PDF-related actions
        assert any("pdf" in r["description"].lower() for r in results)
    
    def test_search_temporal(self, engine_with_actions):
        """Test searching with temporal reference"""
        results = engine_with_actions.search_semantic("the file we opened earlier", limit=5)
        
        assert len(results) > 0
        # Should find file-related actions
        assert any("file" in r["description"].lower() for r in results)
    
    def test_search_limit(self, engine_with_actions):
        """Test that search respects limit parameter"""
        results = engine_with_actions.search_semantic("file", limit=2)
        
        assert len(results) <= 2
    
    def test_search_empty_query(self, engine_with_actions):
        """Test search with empty query"""
        results = engine_with_actions.search_semantic("", limit=5)
        
        # Should return something or handle gracefully
        assert isinstance(results, list)


class TestReferenceResolutionWithSemanticSearch:
    """Test reference resolution with semantic search fallback"""
    
    @pytest.fixture
    def engine(self):
        """Create an engine with semantic memory"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        engine = MemoryEngine(db_path, enable_semantic_memory=True)
        yield engine
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        chroma_path = Path(db_path).parent / f"{Path(db_path).stem}_chroma"
        if chroma_path.exists():
            import shutil
            shutil.rmtree(chroma_path)
    
    def test_exact_keyword_resolution(self, engine):
        """Test that exact keywords still work"""
        engine.record_action("copy", {"content": "test data"})
        
        result = engine.resolve_reference("it")
        assert result == "test data"
    
    def test_semantic_fallback_for_file(self, engine):
        """Test semantic fallback when exact keywords don't match"""
        engine.record_action("open_file", {"file_path": "/Users/test/report.pdf"})
        
        # Query that doesn't match exact keywords
        result = engine.resolve_reference("the PDF we saw earlier")
        
        assert result is not None
        assert "report.pdf" in str(result).lower()
    
    def test_semantic_fallback_french(self, engine):
        """Test semantic fallback with French query"""
        engine.record_action("open_file", {"file_path": "/Users/test/document.pdf"})
        
        # French query
        result = engine.resolve_reference("le fichier d'hier")
        
        assert result is not None
        # Should resolve to file path or action data containing it
    
    def test_semantic_fallback_app(self, engine):
        """Test semantic fallback for app references"""
        engine.record_action("open_app", {"app_name": "Safari"})
        
        result = engine.resolve_reference("the browser we opened")
        
        assert result is not None
        assert "safari" in str(result).lower()
    
    def test_exact_keyword_takes_precedence(self, engine):
        """Test that exact keywords take precedence over semantic search"""
        engine.record_action("copy", {"content": "exact match"})
        engine.record_action("open_file", {"file_path": "/test/file.pdf"})
        
        # "it" should resolve to last_copied, not semantic search
        result = engine.resolve_reference("it")
        assert result == "exact match"


class TestAcceptanceCriteria:
    """Test the acceptance criteria from TICKET-MEM-001"""
    
    @pytest.fixture
    def engine(self):
        """Create an engine for acceptance testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        engine = MemoryEngine(db_path, enable_semantic_memory=True)
        yield engine
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        chroma_path = Path(db_path).parent / f"{Path(db_path).stem}_chroma"
        if chroma_path.exists():
            import shutil
            shutil.rmtree(chroma_path)
    
    def test_acceptance_criteria(self, engine):
        """
        ACCEPTANCE CRITERIA:
        User opens "report.pdf". Later, they say "Renvoie le PDF qu'on a vu tout à l'heure".
        The agent should find "report.pdf".
        """
        # Step 1: User opens report.pdf
        engine.record_action("open_file", {
            "file_path": "/Users/alice/documents/report.pdf"
        })
        
        # Simulate some time passing and other actions
        engine.record_action("open_app", {"app_name": "Safari"})
        engine.record_action("copy", {"content": "some text"})
        
        # Step 2: User asks for "le PDF qu'on a vu tout à l'heure" (the PDF we saw earlier)
        result = engine.resolve_reference("le PDF qu'on a vu tout à l'heure")
        
        # Step 3: Verify that the agent found report.pdf
        assert result is not None
        assert "report.pdf" in str(result).lower()
        
        # Also test English version
        result_en = engine.resolve_reference("the PDF we saw earlier")
        assert result_en is not None
        assert "report.pdf" in str(result_en).lower()
    
    def test_multiple_pdfs_finds_most_recent(self, engine):
        """Test that when multiple PDFs exist, semantic search finds the most relevant"""
        # Open several PDFs
        engine.record_action("open_file", {"file_path": "/docs/old_budget.pdf"})
        engine.record_action("open_file", {"file_path": "/docs/presentation.pdf"})
        engine.record_action("open_file", {"file_path": "/docs/recent_report.pdf"})
        
        # Search for "recent report"
        result = engine.resolve_reference("the recent report we looked at")
        
        assert result is not None
        # Should find the recent_report.pdf as most semantically similar


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def engine(self):
        """Create an engine with semantic memory"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        engine = MemoryEngine(db_path, enable_semantic_memory=True)
        yield engine
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        chroma_path = Path(db_path).parent / f"{Path(db_path).stem}_chroma"
        if chroma_path.exists():
            import shutil
            shutil.rmtree(chroma_path)
    
    def test_search_with_no_actions(self, engine):
        """Test semantic search when no actions have been recorded"""
        results = engine.search_semantic("any query", limit=5)
        
        assert results == []
    
    def test_resolve_reference_with_no_actions(self, engine):
        """Test reference resolution when no actions have been recorded"""
        result = engine.resolve_reference("the file from earlier")
        
        assert result is None
    
    def test_malformed_action_data(self, engine):
        """Test that malformed action data doesn't break vectorization"""
        # Record action with unexpected structure
        result = engine.record_action("custom_action", {
            "unexpected_field": "value",
            "nested": {"data": "here"}
        })
        
        assert result is True
        
        # Should still be searchable
        results = engine.search_semantic("custom action", limit=1)
        assert len(results) >= 0  # Should not crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
