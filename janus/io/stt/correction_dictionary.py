"""
Correction dictionary for common speech-to-text phonetic errors
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional


class CorrectionDictionary:
    """Manages a dictionary of common STT errors and their corrections"""

    # Default corrections for common phonetic confusions
    DEFAULT_CORRECTIONS = {
        # Application names - French phonetic errors
        "v s cold": "vscode",
        "v s code": "vscode",
        "vs cold": "vscode",
        "vs code": "vscode",
        "visual studio code": "vscode",
        "visuelle studio": "visual studio",
        "be as code": "vscode",
        "safari": "Safari",
        "sa fari": "Safari",
        "sa farie": "Safari",
        "safarie": "Safari",
        "chrome": "Chrome",
        "crome": "Chrome",
        "chrôme": "Chrome",
        "fire fox": "Firefox",
        "firefox": "Firefox",
        "fire faux": "Firefox",
        "faille refuge": "Firefox",
        "slack": "Slack",
        "slaque": "Slack",
        "notion": "Notion",
        "no sion": "Notion",
        # Common commands - French
        "clique": "clique",
        "clic": "clique",
        "click": "clique",
        "copie": "copie",
        "copy": "copie",
        "colle": "colle",
        "paste": "colle",
        "ouvre": "ouvre",
        "ouvrir": "ouvre",
        "open": "ouvre",
        "lance": "lance",
        "lancer": "lance",
        "launch": "lance",
        "ferme": "ferme",
        "fermer": "ferme",
        "close": "ferme",
        "tape": "tape",
        "taper": "tape",
        "écris": "écris",
        "écrire": "écris",
        "sélectionne": "sélectionne",
        "sélectionner": "sélectionne",
        # Technical terms - extended
        "terminer": "terminal",
        "terminal": "terminal",
        "terme inal": "terminal",
        "git hub": "github",
        "get hub": "github",
        "gît": "git",
        "git": "git",
        "docker": "docker",
        "docker hub": "docker",
        "doc air": "docker",
        "doc heure": "docker",
        "python": "python",
        "pie thon": "python",
        "parle ton": "python",
        "javascript": "javascript",
        "java script": "javascript",
        "type script": "typescript",
        "typescript": "typescript",
        "node": "node",
        "note": "node",
        "react": "react",
        "ré acte": "react",
        "vue": "vue",
        "angular": "angular",
        "an gu laire": "angular",
        "npm": "npm",
        "n p m": "npm",
        # Common French words with frequent errors
        "navigateur": "navigateur",
        "naviga teur": "navigateur",
        "fichier": "fichier",
        "fi chier": "fichier",
        "dossier": "dossier",
        "dos sier": "dossier",
        "recherche": "recherche",
        "rechercher": "recherche",
        "re cherche": "recherche",
        "fenêtre": "fenêtre",
        "fe nêtre": "fenêtre",
        "onglet": "onglet",
        "on glet": "onglet",
        "bouton": "bouton",
        "bou ton": "bouton",
        "page": "page",
        "pa je": "page",
        "site": "site",
        "ci te": "site",
        "internet": "internet",
        "inter net": "internet",
        "ordinateur": "ordinateur",
        "ordi na teur": "ordinateur",
        "clavier": "clavier",
        "cla vier": "clavier",
        "souris": "souris",
        "sou ri": "souris",
        "écran": "écran",
        "é cran": "écran",
    }

    def __init__(
        self,
        custom_corrections: Optional[Dict[str, str]] = None,
        dictionary_path: Optional[str] = None,
    ):
        """
        Initialize correction dictionary

        Args:
            custom_corrections: Optional custom corrections to add
            dictionary_path: Optional path to load corrections from JSON file
        """
        self.corrections = self.DEFAULT_CORRECTIONS.copy()

        # Load from file if provided
        if dictionary_path and Path(dictionary_path).exists():
            self.load_from_file(dictionary_path)

        # Add custom corrections
        if custom_corrections:
            self.corrections.update(custom_corrections)

        # Pre-compile regex patterns for efficiency
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for all corrections"""
        self.patterns = {}
        for error, correction in self.corrections.items():
            # Create case-insensitive pattern with word boundaries
            pattern = re.compile(r"\b" + re.escape(error) + r"\b", re.IGNORECASE)
            self.patterns[error] = (pattern, correction)

    def correct_text(self, text: str) -> str:
        """
        Apply corrections to text

        Args:
            text: Input text with potential errors

        Returns:
            Corrected text
        """
        if not text:
            return text

        corrected = text

        # Apply each correction pattern
        for error, (pattern, correction) in self.patterns.items():
            corrected = pattern.sub(correction, corrected)

        return corrected

    def add_correction(self, error: str, correction: str):
        """
        Add a new correction to the dictionary

        Args:
            error: The erroneous text
            correction: The correct text
        """
        error_lower = error.lower()
        self.corrections[error_lower] = correction

        # Update compiled pattern
        pattern = re.compile(r"\b" + re.escape(error_lower) + r"\b", re.IGNORECASE)
        self.patterns[error_lower] = (pattern, correction)

    def remove_correction(self, error: str):
        """
        Remove a correction from the dictionary

        Args:
            error: The error pattern to remove
        """
        error_lower = error.lower()
        if error_lower in self.corrections:
            del self.corrections[error_lower]
            del self.patterns[error_lower]

    def get_corrections(self) -> Dict[str, str]:
        """
        Get all corrections

        Returns:
            Dictionary of error -> correction mappings
        """
        return self.corrections.copy()

    def save_to_file(self, path: str):
        """
        Save corrections to JSON file

        Args:
            path: File path to save to
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.corrections, f, indent=2, ensure_ascii=False)

    def load_from_file(self, path: str):
        """
        Load corrections from JSON file

        Args:
            path: File path to load from
        """
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            self.corrections.update(loaded)

    def find_similar_corrections(self, text: str, threshold: int = 3) -> List[str]:
        """
        Find potential corrections that might apply to the text

        Args:
            text: Text to check
            threshold: Maximum edit distance for similarity

        Returns:
            List of possible corrections
        """
        text_lower = text.lower()
        similar = []

        for error, correction in self.corrections.items():
            if error in text_lower or text_lower in error:
                similar.append(f"{error} -> {correction}")

        return similar
