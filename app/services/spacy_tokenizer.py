"""Custom spaCy tokenizer using learned multi-word patterns."""

import spacy
from spacy.language import Language
from spacy.tokens import Doc
from spacy.matcher import PhraseMatcher
from typing import List, Dict, Optional
from app.services.pattern_extractor import pattern_extractor
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class CustomSpacyTokenizer:
    """Custom tokenizer using learned multi-word patterns."""

    def __init__(self):
        self.nlp = {}  # Dictionary of language models
        self.patterns_loaded = False

    async def initialize(self):
        """Initialize spaCy models for all languages with learned patterns."""
        if self.patterns_loaded:
            logger.info("spaCy tokenizer already initialized")
            return

        logger.info("Initializing spaCy tokenizer with learned patterns...")

        # Extract patterns from database
        patterns_by_lang = await pattern_extractor.get_all_patterns_by_language(
            min_occurrences=settings.pattern_matching_min_occurrences
        )

        for lang in settings.supported_languages:
            try:
                # Create blank spaCy model (no NER, just tokenizer)
                spacy_lang = self._get_spacy_lang_code(lang)
                nlp = spacy.blank(spacy_lang)

                # Get patterns for this language
                patterns = patterns_by_lang.get(lang, [])

                if patterns:
                    # Add custom component for merging multi-word entities
                    if not Language.has_factory("multiword_merger"):
                        Language.factory("multiword_merger", func=create_multiword_merger)

                    nlp.add_pipe("multiword_merger", config={"patterns": patterns})
                    logger.info(f"Loaded {len(patterns)} patterns for language '{lang}'")
                else:
                    logger.warning(f"No patterns found for language '{lang}'")

                # Store model
                self.nlp[lang] = nlp

            except Exception as e:
                logger.error(f"Failed to initialize spaCy for language '{lang}': {e}")
                # Continue with other languages

        self.patterns_loaded = True
        logger.info(f"spaCy tokenizer initialized for {len(self.nlp)} languages")

    def _get_spacy_lang_code(self, lang: str) -> str:
        """Map our language codes to spaCy language codes."""
        mapping = {
            "zh": "zh",
            "en": "en",
            "es": "es",
            "id": "id",
            "pt": "pt",
            "fr": "fr",
            "ja": "ja",
            "ru": "ru",
            "de": "de",
            "ko": "ko"
        }
        return mapping.get(lang, "en")

    def tokenize(self, text: str, language: str) -> List[str]:
        """
        Tokenize text using custom rules with learned patterns.

        Args:
            text: Text to tokenize
            language: Language code

        Returns:
            List of tokens
        """
        if not self.patterns_loaded:
            # Fallback to simple tokenization if not initialized
            logger.warning("spaCy not initialized, using simple tokenization")
            return text.split()

        nlp = self.nlp.get(language)
        if not nlp:
            logger.warning(f"No spaCy model for '{language}', using simple tokenization")
            return text.split()

        doc = nlp(text)
        return [token.text for token in doc]


@Language.factory("multiword_merger")
def create_multiword_merger(nlp: Language, name: str, patterns: List[str]):
    """Factory function to create MultiwordMerger component."""
    return MultiwordMerger(nlp, patterns)


class MultiwordMerger:
    """Custom component to merge multi-word entities based on learned patterns."""

    def __init__(self, nlp: Language, patterns: List[str]):
        """
        Initialize the merger with learned patterns.

        Args:
            nlp: spaCy language model
            patterns: List of multi-word patterns to merge
        """
        self.matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

        # Add patterns to matcher
        if patterns:
            # Sort patterns by length (longest first) for greedy matching
            sorted_patterns = sorted(patterns, key=len, reverse=True)

            # Create pattern docs
            pattern_docs = [nlp.make_doc(text) for text in sorted_patterns]
            self.matcher.add("MULTIWORD", pattern_docs)

            logger.debug(f"MultiwordMerger initialized with {len(patterns)} patterns")
        else:
            logger.warning("MultiwordMerger initialized with no patterns")

    def __call__(self, doc: Doc) -> Doc:
        """
        Process doc to merge multi-word entities.

        Strategy: Longest match first (greedy) to handle overlapping patterns.

        Args:
            doc: spaCy Doc object

        Returns:
            Processed Doc with merged entities
        """
        matches = self.matcher(doc)

        if not matches:
            return doc

        # Sort matches by start position and length (longest first)
        matches = sorted(matches, key=lambda x: (x[1], -(x[2] - x[1])))

        # Track which tokens are already merged
        merged_tokens = set()
        spans_to_merge = []

        for match_id, start, end in matches:
            # Skip if any token in this span is already merged
            if any(i in merged_tokens for i in range(start, end)):
                continue

            # Mark tokens as merged
            for i in range(start, end):
                merged_tokens.add(i)

            # Add span to merge list
            spans_to_merge.append(doc[start:end])

        # Merge spans
        if spans_to_merge:
            with doc.retokenize() as retokenizer:
                for span in spans_to_merge:
                    retokenizer.merge(span)

        return doc


# Global instance
custom_tokenizer = CustomSpacyTokenizer()
