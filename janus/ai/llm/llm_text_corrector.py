"""
LLM Text Corrector - Unified interface for semantic correction and reformatting

This module provides a unified adapter that uses the centralized LLM client
for text correction tasks (semantic correction, natural reformatting, etc.).

Uses UnifiedLLMClient for all text processing operations.
"""

from typing import Any, Dict, Optional

from janus.logging import get_logger

logger = get_logger("llm_text_corrector")


class LLMTextCorrector:
    """
    Unified LLM-based text correction using the centralized LLM client.
    
    This uses UnifiedLLMClient configured in [llm] section of config.ini.
    
    Benefits:
    - Single LLM instance for all text processing
    - Consistent behavior across features
    - Easier configuration and maintenance
    - Better resource utilization
    """
    
    def __init__(self, llm_client):
        """
        Initialize LLM text corrector
        
        Args:
            llm_client: UnifiedLLMClient instance from janus.ai.llm.unified_client
        """
        self.llm_client = llm_client
        self.logger = logger
        
        # Statistics
        self.total_corrections = 0
        self.total_reformats = 0
    
    def correct_transcript(
        self,
        raw_transcript: str,
        language: str = "en",
        previous_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Correct transcript using the main LLM
        
        Args:
            raw_transcript: Raw transcript text
            language: Language code (fr or en)
            previous_context: Optional previous context for coherence
        
        Returns:
            Dictionary with correction results
        """
        if not self.llm_client or not self.llm_client.available:
            # Fallback: return raw transcript if LLM not available
            return {
                "corrected": raw_transcript,
                "raw": raw_transcript,
                "model_used": False,
                "tokens_used": 0,
            }
        
        # Build prompt
        if language == "fr":
            system_prompt = """Tu es un assistant de correction de transcriptions audio.
Corrige la grammaire, supprime les mots de remplissage (euh, um, etc.),
et améliore la clarté sans changer le sens. Réponds UNIQUEMENT avec le texte corrigé."""
            
            user_prompt = f"Transcription brute: {raw_transcript}\n\nTranscription corrigée:"
            if previous_context:
                user_prompt = f"Contexte précédent: {previous_context}\n\n{user_prompt}"
        else:  # English
            system_prompt = """You are an audio transcription correction assistant.
Fix grammar, remove filler words (uh, um, like, etc.),
and improve clarity without changing the meaning. Respond ONLY with the corrected text."""
            
            user_prompt = f"Raw transcript: {raw_transcript}\n\nCorrected transcript:"
            if previous_context:
                user_prompt = f"Previous context: {previous_context}\n\n{user_prompt}"
        
        try:
            # Call the UnifiedLLMClient
            corrected_text = self._call_llm(system_prompt, user_prompt)
            
            # Clean up response
            corrected_text = self._clean_llm_output(corrected_text, raw_transcript)
            
            self.total_corrections += 1
            
            return {
                "corrected": corrected_text,
                "raw": raw_transcript,
                "model_used": True,
                "tokens_used": 0,  # LLMService doesn't expose token counts in response
            }
        except Exception as e:
            self.logger.warning(f"LLM correction failed: {e}")
            return {
                "corrected": raw_transcript,
                "raw": raw_transcript,
                "model_used": False,
                "tokens_used": 0,
                "error": str(e),
            }
    
    def reformat_text(
        self,
        text: str,
        language: str = "fr",
        previous_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reformat text using the main LLM (natural reformatter)
        
        Args:
            text: Text to reformat
            language: Language code (fr, en)
            previous_context: Optional previous context
        
        Returns:
            Dictionary with reformatted text and metadata
        """
        if not self.llm_client or not self.llm_client.available:
            # Fallback: return original text
            return {
                "original": text,
                "reformatted": text,
                "method": "passthrough",
                "confidence": 0.5,
            }
        
        # Build prompt
        if language.lower().startswith("fr"):
            system_prompt = """Tu es un assistant qui reformule des commandes vocales.
Réécris proprement cette commande vocale sans changer le sens.
Retire les hésitations (euh, um, ben, etc.) et améliore la grammaire si nécessaire.
Garde tous les noms techniques et commandes exactement comme ils sont."""
            
            user_prompt = f"Commande: {text}\nCommande reformulée:"
            if previous_context:
                user_prompt = f"Contexte précédent: {previous_context}\n\n{user_prompt}"
        else:
            system_prompt = """You are an assistant that reformulates voice commands.
Rewrite this voice command clearly without changing its meaning.
Remove hesitations (uh, um, like, etc.) and improve grammar if needed.
Keep all technical terms and commands exactly as they are."""
            
            user_prompt = f"Command: {text}\nReformulated command:"
            if previous_context:
                user_prompt = f"Previous context: {previous_context}\n\n{user_prompt}"
        
        try:
            # Call the main LLM service
            reformatted = self._call_llm(system_prompt, user_prompt)
            
            # Clean up response
            reformatted = self._clean_llm_output(reformatted, text)
            
            self.total_reformats += 1
            
            return {
                "original": text,
                "reformatted": reformatted,
                "method": "llm",
                "confidence": 0.9,
            }
        except Exception as e:
            self.logger.warning(f"LLM reformatting failed: {e}")
            return {
                "original": text,
                "reformatted": text,
                "method": "passthrough",
                "confidence": 0.5,
                "error": str(e),
            }
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call LLM service with prompts
        
        Args:
            system_prompt: System instructions
            user_prompt: User query
        
        Returns:
            Generated text
        """
        response = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=200,
            temperature=0.3  # Low temperature for consistent corrections
        )
        return response.strip()
    
    def _clean_llm_output(self, output: str, original: str) -> str:
        """
        Clean LLM output of artifacts
        
        Args:
            output: LLM response
            original: Original input text
        
        Returns:
            Cleaned text
        """
        # Remove quotes if present
        output = output.strip("\"'")
        
        # If output is empty or too short, return original
        if len(output) < 3:
            return original
        
        # Remove common prefixes
        prefixes = [
            "Transcription corrigée:",
            "Corrected transcript:",
            "Commande reformulée:",
            "Reformulated command:",
            "Reformulated:",
            "→",
            "=>",
            ":",
        ]
        
        for prefix in prefixes:
            if output.startswith(prefix):
                output = output[len(prefix):].strip()
        
        return output if output else original
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get correction statistics"""
        return {
            "total_corrections": self.total_corrections,
            "total_reformats": self.total_reformats,
            "llm_provider": self.llm_client.provider if self.llm_client else "none",
            "llm_model": self.llm_client.model if self.llm_client else "none",
            "llm_available": self.llm_client.available if self.llm_client else False,
        }
