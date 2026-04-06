"""
ToolRetrievalService - RAG for Dynamic Tool Selection

TICKET-FEAT-TOOL-RAG: Implements semantic search for backend tools.
Instead of injecting all available tools into the prompt (which causes token overflow),
this service dynamically selects the 3-5 most relevant tools based on the user's query
using vector similarity search.

Architecture:
- ChromaDB for vector storage
- sentence-transformers/all-MiniLM-L6-v2 for embeddings
- <200ms retrieval latency target
- Scalable to 100+ tools without prompt modification

RAG-001 Enhancements:
- Session-based caching for stable tool selection
- Version hash tracking for automatic cache invalidation
- Delta-only updates to minimize prompt size

Usage:
    service = ToolRetrievalService()
    service.index_tools(TOOLS_CATALOG, catalog_version=CATALOG_VERSION_HASH)
    relevant_tools = service.get_relevant_tools(
        "Search contact in Salesforce", 
        session_id="user_session_123",
        top_k=5
    )
"""

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy imports for optional dependencies
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning(
        "Tool RAG dependencies (chromadb, sentence-transformers) not available. "
        "Install them to enable dynamic tool selection: pip install chromadb sentence-transformers"
    )


class ToolRetrievalService:
    """
    Service for semantic retrieval of relevant tools based on user queries.
    
    Uses ChromaDB for vector storage and sentence-transformers for embedding generation.
    Dynamically selects the most relevant tools to inject into the LLM prompt.
    
    RAG-001 Enhancements:
    - Session-based caching for stable tool selection
    - Version hash tracking for automatic cache invalidation
    - Delta-only updates to minimize prompt size
    """
    
    def __init__(
        self,
        collection_name: str = "tool_definitions",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        enable_cache: bool = True,
        enable_session_cache: bool = True,
        enable_delta_updates: bool = True,
    ):
        """
        Initialize ToolRetrievalService.
        
        Args:
            collection_name: ChromaDB collection name for tool storage
            embedding_model: Sentence-transformers model for embeddings
            enable_cache: Enable result caching for performance
            enable_session_cache: Enable session-based tool selection caching (RAG-001)
            enable_delta_updates: Enable delta-only tool updates (RAG-001)
        """
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.enable_cache = enable_cache
        self.enable_session_cache = enable_session_cache
        self.enable_delta_updates = enable_delta_updates
        
        # Lazy-loaded components
        self._chroma_client = None
        self._collection = None
        self._embedding_model = None
        self._indexed = False
        self._catalog_version = None  # RAG-001: Track catalog version
        
        # Simple cache for repeated queries
        self._cache: Dict[str, str] = {}
        
        # RAG-001: Session-based cache
        # session_id -> {query_hash -> tool_ids}
        self._session_cache: Dict[str, Dict[str, List[str]]] = {}
        
        # RAG-001: Last tool selection per session for delta computation
        # session_id -> {query_hash -> tool_ids}
        self._last_selection: Dict[str, Dict[str, List[str]]] = {}
        
        # Performance tracking
        self._stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "session_cache_hits": 0,  # RAG-001
            "delta_updates": 0,  # RAG-001
            "avg_latency_ms": 0,
            "max_latency_ms": 0,
        }
        
        # Latency threshold (configurable)
        self.LATENCY_THRESHOLD_MS = 200  # Target for tool retrieval performance
        
        if not RAG_AVAILABLE:
            logger.warning("Tool RAG not available - tool retrieval will be disabled")
    
    @property
    def available(self) -> bool:
        """Check if RAG dependencies are available."""
        return RAG_AVAILABLE
    
    @property
    def indexed(self) -> bool:
        """Check if tools have been indexed."""
        return self._indexed
    
    def _init_chromadb(self):
        """Initialize ChromaDB client and collection (lazy)."""
        if self._chroma_client is not None:
            return
        
        if not RAG_AVAILABLE:
            logger.error("Cannot initialize ChromaDB - dependencies not available")
            return
        
        try:
            # Use in-memory client for fast retrieval
            # Trade-offs:
            # - PRO: Very fast queries (no disk I/O), low latency
            # - PRO: Simple setup (no persistence path management)
            # - CON: Data lost on restart (requires re-indexing)
            # - CON: Higher memory usage (~150-250MB for 100 tools)
            # 
            # For production with frequent restarts, consider PersistentClient:
            # self._chroma_client = chromadb.PersistentClient(path="./chroma_data")
            self._chroma_client = chromadb.Client()
            
            # Get or create collection
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Tool definitions for RAG-based tool selection"}
            )
            
            logger.info(f"ChromaDB initialized: collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._chroma_client = None
            self._collection = None
    
    def _init_embedding_model(self):
        """Initialize sentence-transformers model (lazy)."""
        if self._embedding_model is not None:
            return
        
        if not RAG_AVAILABLE:
            logger.error("Cannot initialize embedding model - dependencies not available")
            return
        
        try:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            from janus.ai.embeddings.shared_sentence_transformer import get_sentence_transformer

            self._embedding_model = get_sentence_transformer(self.embedding_model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._embedding_model = None
    
    def index_tools(self, tools_catalog: List[Dict[str, Any]], catalog_version: Optional[str] = None) -> bool:
        """
        Index tools catalog into ChromaDB with embeddings.
        
        RAG-001: Now supports version tracking for automatic cache invalidation.
        
        Args:
            tools_catalog: List of tool definitions with structure:
                {
                    "id": str,
                    "signature": str,
                    "description": str,
                    "keywords": str
                }
            catalog_version: Optional version hash for cache invalidation (RAG-001).
                If provided and different from current, caches are cleared.
                
                Example usage:
                    # Old API (still works)
                    service.index_tools(TOOLS_CATALOG)
                    
                    # New API with version tracking (RAG-001)
                    from janus.config.tools_registry import CATALOG_VERSION_HASH
                    service.index_tools(TOOLS_CATALOG, catalog_version=CATALOG_VERSION_HASH)
        
        Returns:
            True if indexing successful, False otherwise
        """
        if not RAG_AVAILABLE:
            logger.warning("Tool RAG not available - skipping indexing")
            return False
        
        # RAG-001: Check version and invalidate caches if changed
        if catalog_version and self._catalog_version and catalog_version != self._catalog_version:
            logger.info(f"Catalog version changed: {self._catalog_version} -> {catalog_version}")
            self.clear_cache()
            self._session_cache.clear()
            self._last_selection.clear()
        
        self._catalog_version = catalog_version
        
        # Initialize components
        self._init_chromadb()
        self._init_embedding_model()
        
        if self._collection is None or self._embedding_model is None:
            logger.error("Cannot index tools - ChromaDB or embedding model not initialized")
            return False
        
        try:
            start_time = time.time()
            
            # Prepare documents for embedding
            documents = []
            metadatas = []
            ids = []
            
            for tool in tools_catalog:
                tool_id = tool.get("id")
                signature = tool.get("signature", "")
                description = tool.get("description", "")
                keywords = tool.get("keywords", "")
                
                if not tool_id:
                    logger.warning(f"Skipping tool without ID: {tool}")
                    continue
                
                # Combine description and keywords for better semantic matching
                document = f"{description} {keywords}"
                
                documents.append(document)
                metadatas.append({
                    "signature": signature,
                    "description": description,
                    "keywords": keywords,
                })
                ids.append(tool_id)
            
            if not documents:
                logger.warning("No valid tools to index")
                return False
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(documents)} tools...")
            embeddings = self._embedding_model.encode(documents, show_progress_bar=False)
            
            # Add to ChromaDB collection
            self._collection.add(
                embeddings=embeddings.tolist(),
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            
            duration_ms = (time.time() - start_time) * 1000
            self._indexed = True
            
            logger.info(
                f"Successfully indexed {len(documents)} tools in {duration_ms:.2f}ms "
                f"({duration_ms/len(documents):.2f}ms per tool)"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to index tools: {e}", exc_info=True)
            return False
    
    def get_relevant_tools(
        self,
        query: str,
        top_k: int = 5,
        format_for_prompt: bool = True,
        session_id: Optional[str] = None,
        return_delta: bool = False,
    ) -> str:
        """
        Retrieve most relevant tools for a given user query.
        
        RAG-001 Enhancements:
        - Session-based caching for stable tool selection
        - Delta-only updates to minimize prompt size
        
        Args:
            query: User's goal or query (e.g., "Search contact in Salesforce")
            top_k: Number of tools to retrieve (default: 5)
            format_for_prompt: Format output as prompt-ready string
            session_id: Optional session ID for session-based caching (RAG-001)
            return_delta: If True and session_id provided, return only changed tools (RAG-001)
        
        Returns:
            Formatted string of relevant tool definitions ready for prompt injection,
            or empty string if retrieval fails
        """
        if not self.available or not self.indexed:
            logger.debug("Tool RAG not available or not indexed - returning empty tools")
            return ""
        
        # Create query hash for caching (used for both regular and session cache)
        query_hash = hashlib.md5(f"{query}:{top_k}".encode()).hexdigest()[:12]
        cache_key = f"{query}:{top_k}"
        
        # RAG-001: Check session cache first
        if self.enable_session_cache and session_id and session_id in self._session_cache:
            session_cache = self._session_cache[session_id]
            if query_hash in session_cache:
                self._stats["session_cache_hits"] += 1
                self._stats["total_queries"] += 1
                logger.debug(f"Session cache hit for session {session_id}: '{query[:50]}...'")
                
                # If delta requested, compute delta
                if return_delta and self.enable_delta_updates:
                    return self._compute_delta(session_id, query_hash, session_cache[query_hash])
                else:
                    # Return full cached result
                    tool_ids = session_cache[query_hash]
                    return self._format_tools_by_ids(tool_ids)
        
        # Check regular cache
        if self.enable_cache and cache_key in self._cache:
            self._stats["cache_hits"] += 1
            self._stats["total_queries"] += 1
            logger.debug(f"Tool retrieval cache hit for: '{query[:50]}...'")
            return self._cache[cache_key]
        
        try:
            start_time = time.time()
            
            # Generate query embedding
            query_embedding = self._embedding_model.encode([query], show_progress_bar=False)
            
            # Query ChromaDB for similar tools
            results = self._collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k,
            )
            
            # Extract tool IDs from results
            tool_ids = results["ids"][0] if results and results.get("ids") else []
            
            # RAG-001: Store in session cache if session_id provided
            if self.enable_session_cache and session_id:
                if session_id not in self._session_cache:
                    self._session_cache[session_id] = {}
                self._session_cache[session_id][query_hash] = tool_ids
                
                # Handle delta updates
                if return_delta and self.enable_delta_updates:
                    output = self._compute_delta(session_id, query_hash, tool_ids)
                    self._stats["delta_updates"] += 1
                else:
                    # Format results for prompt
                    if format_for_prompt:
                        output = self._format_tools_for_prompt(results)
                    else:
                        output = str(results)
            else:
                # Format results for prompt
                if format_for_prompt:
                    output = self._format_tools_for_prompt(results)
                else:
                    output = str(results)
            
            # Update stats
            duration_ms = (time.time() - start_time) * 1000
            self._stats["total_queries"] += 1
            self._stats["avg_latency_ms"] = (
                (self._stats["avg_latency_ms"] * (self._stats["total_queries"] - 1) + duration_ms)
                / self._stats["total_queries"]
            )
            self._stats["max_latency_ms"] = max(self._stats["max_latency_ms"], duration_ms)
            
            # Cache result (regular cache) - reuse cache_key from earlier
            if self.enable_cache:
                self._cache[cache_key] = output
            
            # Log performance
            logger.debug(
                f"Retrieved {top_k} tools in {duration_ms:.2f}ms for: '{query[:50]}...'"
            )
            
            if duration_ms > self.LATENCY_THRESHOLD_MS:
                logger.warning(
                    f"Tool retrieval latency ({duration_ms:.2f}ms) exceeds "
                    f"{self.LATENCY_THRESHOLD_MS}ms target"
                )
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to retrieve relevant tools: {e}", exc_info=True)
            return ""
    
    def _compute_delta(self, session_id: str, query_hash: str, current_tool_ids: List[str]) -> str:
        """
        Compute delta between current and previous tool selection.
        
        RAG-001: Returns only tools that changed since last query.
        
        Args:
            session_id: Session identifier
            query_hash: Query hash for tracking
            current_tool_ids: Currently selected tool IDs
            
        Returns:
            Formatted delta string with added/removed tools
        """
        # Get previous selection
        if session_id not in self._last_selection:
            self._last_selection[session_id] = {}
        
        previous_tool_ids = self._last_selection[session_id].get(query_hash, [])
        
        # Compute delta
        added = set(current_tool_ids) - set(previous_tool_ids)
        removed = set(previous_tool_ids) - set(current_tool_ids)
        
        # Update last selection
        self._last_selection[session_id][query_hash] = current_tool_ids
        
        # Format delta
        lines = []
        
        if added:
            lines.append("# Added tools:")
            for tool_id in added:
                tool_info = self._get_tool_info(tool_id)
                if tool_info:
                    lines.append(f"+ {tool_info}")
        
        if removed:
            lines.append("# Removed tools:")
            for tool_id in removed:
                tool_info = self._get_tool_info(tool_id)
                if tool_info:
                    lines.append(f"- {tool_info}")
        
        if not added and not removed:
            # No changes - return full list
            return self._format_tools_by_ids(current_tool_ids)
        
        return "\n".join(lines)
    
    def _format_tools_by_ids(self, tool_ids: List[str]) -> str:
        """
        Format tools by their IDs (for session cache).
        
        Args:
            tool_ids: List of tool IDs
            
        Returns:
            Formatted tool string
        """
        lines = []
        for tool_id in tool_ids:
            tool_info = self._get_tool_info(tool_id)
            if tool_info:
                lines.append(f"- {tool_info}")
        return "\n".join(lines)
    
    def _get_tool_info(self, tool_id: str) -> Optional[str]:
        """
        Get formatted tool information by ID.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Formatted string like "signature: description" or None
        """
        try:
            # Query ChromaDB for tool metadata
            result = self._collection.get(ids=[tool_id])
            if result and result.get("metadatas"):
                metadata = result["metadatas"][0]
                signature = metadata.get("signature", tool_id)
                description = metadata.get("description", "")
                
                if description:
                    return f"{signature}: {description}"
                else:
                    return signature
        except Exception as e:
            logger.debug(f"Could not retrieve tool info for {tool_id}: {e}")
        
        return None
    
    def _format_tools_for_prompt(self, results: Dict[str, Any]) -> str:
        """
        Format ChromaDB query results into prompt-ready string.
        
        Args:
            results: ChromaDB query results
        
        Returns:
            Formatted string like:
            - crm.search_contact(name: str): Search for a contact in Salesforce
            - messaging.post_message(platform: str, channel: str, text: str): Post a message
        """
        if not results or not results.get("ids") or not results["ids"][0]:
            return ""
        
        lines = []
        
        # results structure: {"ids": [[...]], "metadatas": [[...]], ...}
        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        
        for tool_id, metadata in zip(ids, metadatas):
            signature = metadata.get("signature", tool_id)
            description = metadata.get("description", "")
            
            # Format: - signature: description
            line = f"- {signature}"
            if description:
                line += f": {description}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            **self._stats,
            "cache_size": len(self._cache),
            "session_cache_size": len(self._session_cache),  # RAG-001
            "catalog_version": self._catalog_version,  # RAG-001
            "indexed": self._indexed,
            "available": self.available,
        }
    
    def clear_cache(self):
        """Clear the query cache."""
        self._cache.clear()
        logger.info("Tool retrieval cache cleared")
    
    def clear_session_cache(self, session_id: Optional[str] = None):
        """
        Clear session-based cache.
        
        RAG-001: Allows clearing cache for specific session or all sessions.
        
        Args:
            session_id: If provided, clear only this session. Otherwise clear all.
        """
        if session_id:
            if session_id in self._session_cache:
                del self._session_cache[session_id]
            if session_id in self._last_selection:
                del self._last_selection[session_id]
            logger.info(f"Session cache cleared for session: {session_id}")
        else:
            self._session_cache.clear()
            self._last_selection.clear()
            logger.info("All session caches cleared")
