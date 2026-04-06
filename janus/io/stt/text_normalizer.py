"""
Text normalization for cleaning and reformulating STT output
"""

import re
from typing import List, Optional


class TextNormalizer:
    """Normalizes and cleans text from speech recognition"""

    # Common filler words to remove (French and English)
    FILLER_WORDS = {
        "euh",
        "heu",
        "euh euh",
        "hum",
        "hmm",
        "ben",
        "donc",
        "alors",
        "voilà",
        "quoi",
        "en fait",
        "du coup",
        "uh",
        "um",
        "umm",
        "err",
        "like",
        "you know",
        "i mean",
        "basically",
        "actually",
        "literally",
    }

    # Contractions to expand for better understanding
    CONTRACTIONS = {
        # French
        "j'": "je ",
        "l'": "le ",
        "d'": "de ",
        "s'": "se ",
        "c'": "ce ",
        "qu'": "que ",
        "n'": "ne ",
        "m'": "me ",
        "t'": "te ",
        # English
        "can't": "cannot",
        "won't": "will not",
        "don't": "do not",
        "didn't": "did not",
        "i'm": "i am",
        "you're": "you are",
        "he's": "he is",
        "she's": "she is",
        "it's": "it is",
        "we're": "we are",
        "they're": "they are",
        "isn't": "is not",
        "aren't": "are not",
        "wasn't": "was not",
        "weren't": "were not",
    }

    def __init__(
        self,
        remove_fillers: bool = True,
        expand_contractions: bool = True,
        normalize_whitespace: bool = True,
        fix_capitalization: bool = True,
    ):
        """
        Initialize text normalizer

        Args:
            remove_fillers: Remove filler words
            expand_contractions: Expand contractions
            normalize_whitespace: Normalize spacing
            fix_capitalization: Fix sentence capitalization
        """
        self.remove_fillers = remove_fillers
        self.expand_contractions = expand_contractions
        self.normalize_whitespace = normalize_whitespace
        self.fix_capitalization = fix_capitalization

    def normalize(self, text: str) -> str:
        """
        Normalize text through full pipeline

        Args:
            text: Raw text from STT

        Returns:
            Normalized text
        """
        if not text:
            return text

        # Apply normalization steps
        normalized = text

        if self.expand_contractions:
            normalized = self._expand_contractions(normalized)

        if self.remove_fillers:
            normalized = self._remove_fillers(normalized)

        if self.normalize_whitespace:
            normalized = self._normalize_whitespace(normalized)

        if self.fix_capitalization:
            normalized = self._fix_capitalization(normalized)

        return normalized.strip()

    def _expand_contractions(self, text: str) -> str:
        """Expand contractions for better understanding"""
        expanded = text

        # Sort by length (longest first) to avoid partial replacements
        for contraction, expansion in sorted(
            self.CONTRACTIONS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            # Case-insensitive replacement
            pattern = re.compile(re.escape(contraction), re.IGNORECASE)
            expanded = pattern.sub(expansion, expanded)

        return expanded

    def _remove_fillers(self, text: str) -> str:
        """Remove filler words and hesitations"""
        # First remove multi-word fillers
        result = text
        multi_word_fillers = ["you know", "i mean", "en fait", "du coup", "euh euh"]
        for filler in multi_word_fillers:
            # Case-insensitive replacement
            pattern = re.compile(r"\b" + re.escape(filler) + r"\b", re.IGNORECASE)
            result = pattern.sub("", result)

        # Then remove single-word fillers
        words = result.split()
        filtered = []

        for word in words:
            word_lower = word.lower().strip(".,!?;:")
            if word_lower not in self.FILLER_WORDS:
                filtered.append(word)

        return " ".join(filtered)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace (remove extra spaces, fix punctuation spacing)"""
        # Replace multiple spaces with single space
        normalized = re.sub(r"\s+", " ", text)

        # Fix punctuation spacing, but preserve URLs and domains
        # Remove space before punctuation
        normalized = re.sub(r"\s+([.,!?;:])", r"\1", normalized)

        # Add space after punctuation if missing, but not for domains/URLs
        # Don't add space after dots that are part of domains (word.word pattern)
        normalized = re.sub(r"([!?;:])([^\s\d])", r"\1 \2", normalized)
        # For periods, only add space if not followed by domain extensions or numbers
        normalized = re.sub(
            r"(\.)([a-zA-Z])(?!(?:com|org|net|fr|ca|uk|de|it|es|ru|jp|cn|au|br|in|gov|edu|mil|co|io|ai|ly|me|tv|info|biz|name|pro|museum|aero|coop|jobs|mobi|travel|tel|xxx|post|asia|cat|int|local|localhost|test)\b)",
            r"\1 \2",
            normalized,
        )

        return normalized

    def _fix_capitalization(self, text: str) -> str:
        """Fix basic capitalization (first letter, after periods)"""
        if not text:
            return text

        # Capitalize first letter
        result = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

        # Capitalize after sentence-ending punctuation
        result = re.sub(r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), result)

        return result

    def clean_command_text(self, text: str) -> str:
        """
        Specialized cleaning for command text (more aggressive)

        Args:
            text: Command text to clean

        Returns:
            Cleaned command text
        """
        # For commands, we want to be more aggressive
        cleaned = text.lower().strip()

        # Remove all filler words
        words = cleaned.split()
        filtered = [w for w in words if w not in self.FILLER_WORDS]
        cleaned = " ".join(filtered)

        # Remove extra punctuation that might interfere with command parsing
        cleaned = re.sub(r"[.!?,;:]", "", cleaned)

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def remove_repetitions(self, text: str) -> str:
        """
        Remove word repetitions (e.g., 'open open chrome' -> 'open chrome')

        Args:
            text: Text with potential repetitions

        Returns:
            Text with repetitions removed
        """
        words = text.split()
        deduped = []
        prev_word = None

        for word in words:
            word_clean = word.lower().strip(".,!?;:")
            prev_clean = prev_word.lower().strip(".,!?;:") if prev_word else None

            # Only add if different from previous word
            if word_clean != prev_clean:
                deduped.append(word)

            prev_word = word

        return " ".join(deduped)

    def normalize_numbers(self, text: str) -> str:
        """
        Convert number words to digits where appropriate

        Args:
            text: Text containing number words

        Returns:
            Text with numbers normalized
        """
        # French number words
        fr_numbers = {
            "zéro": "0",
            "zero": "0",
            "un": "1",
            "une": "1",
            "deux": "2",
            "trois": "3",
            "quatre": "4",
            "cinq": "5",
            "six": "6",
            "sept": "7",
            "huit": "8",
            "neuf": "9",
            "dix": "10",
            "onze": "11",
            "douze": "12",
            "treize": "13",
            "quatorze": "14",
            "quinze": "15",
            "seize": "16",
            "vingt": "20",
            "trente": "30",
            "quarante": "40",
            "cinquante": "50",
        }

        # English number words
        en_numbers = {
            "zero": "0",
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8",
            "nine": "9",
            "ten": "10",
            "eleven": "11",
            "twelve": "12",
            "thirteen": "13",
            "fourteen": "14",
            "fifteen": "15",
            "sixteen": "16",
            "seventeen": "17",
            "eighteen": "18",
            "nineteen": "19",
            "twenty": "20",
            "thirty": "30",
            "forty": "40",
            "fifty": "50",
        }

        all_numbers = {**fr_numbers, **en_numbers}

        # Replace number words with digits
        result = text
        for word, digit in all_numbers.items():
            # Use word boundaries to avoid partial matches
            pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
            result = pattern.sub(digit, result)

        return result
