"""
Intent Classification Service

Routes queries to the optimal handler based on detected intent.
Reduces unnecessary RAG calls for common queries like greetings,
thanks, and FAQ matches.

The classifier uses fuzzy string matching (no LLM calls) for fast,
cost-effective intent detection.
"""

import os
import re
import logging
from typing import Tuple, Optional, List
from enum import Enum

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

logger = logging.getLogger(__name__)

_NORMALIZE_RE = re.compile(r"[a-z0-9]+")


class Intent(Enum):
    """User intent categories."""
    GREETING = "greeting"
    THANKS = "thanks"
    FAQ_MATCH = "faq_match"
    SEARCH = "search"


class IntentClassifier:
    """
    Lightweight intent classifier for query routing.
    
    Uses fuzzy matching and keyword detection to classify user queries
    without requiring LLM calls. This enables fast routing of common
    queries (greetings, thanks) and FAQ matches.
    
    Attributes:
        faq_questions: List of suggested questions from CMS
        faq_match_threshold: Minimum similarity score for FAQ matching (0-100)
    """
    
    # Greeting patterns - short phrases that indicate a greeting
    GREETING_PATTERNS = [
        "hello", "hi", "hey", "good morning", "good afternoon",
        "good evening", "what's up", "howdy", "greetings", "yo",
        "hiya", "sup", "hi there", "hello there", "hey there"
    ]
    
    # Thanks patterns - phrases that indicate gratitude
    THANKS_PATTERNS = [
        "thanks", "thank you", "thx", "appreciate", "helpful",
        "got it", "understood", "makes sense", "perfect", "great",
        "awesome", "cool", "nice", "cheers", "ty", "tyvm",
        "thank you so much", "thanks a lot", "much appreciated"
    ]
    
    # Static response for greetings
    GREETING_RESPONSE = (
        "Hello! I'm here to help you learn about Litecoin. "
        "Feel free to ask me anything about Litecoin's technology, "
        "history, wallets, or how to get started!"
    )
    
    # Static response for thanks
    THANKS_RESPONSE = (
        "You're welcome! Is there anything else you'd like to know about Litecoin?"
    )
    
    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normalize text for robust intent matching.
        
        - Lowercases
        - Strips punctuation
        - Collapses to space-separated alphanumeric tokens
        
        This avoids substring false positives like 'sup' matching 'supply'.
        """
        if not text:
            return ""
        return " ".join(_NORMALIZE_RE.findall(text.lower()))

    def __init__(self, faq_questions: Optional[List[str]] = None):
        """
        Initialize the classifier.
        
        Args:
            faq_questions: List of suggested questions from CMS for FAQ matching
        """
        if not RAPIDFUZZ_AVAILABLE:
            logger.warning(
                "rapidfuzz not installed. FAQ matching will be disabled. "
                "Install with: pip install rapidfuzz"
            )
        
        self.faq_questions = faq_questions or []
        self.faq_match_threshold = float(os.getenv("FAQ_MATCH_THRESHOLD", "85"))
        
        logger.info(
            f"IntentClassifier initialized with {len(self.faq_questions)} FAQ questions, "
            f"threshold={self.faq_match_threshold}"
        )
    
    def update_faq_questions(self, questions: List[str]) -> None:
        """
        Update the FAQ questions list.
        
        Call this when suggested questions are refreshed from CMS.
        
        Args:
            questions: New list of FAQ question strings
        """
        self.faq_questions = questions
        logger.info(f"Updated FAQ questions: {len(questions)} loaded")
    
    def classify(self, query: str) -> Tuple[Intent, Optional[str], Optional[str]]:
        """
        Classify user query intent.
        
        Args:
            query: The user's query string
            
        Returns:
            Tuple of:
            - Intent enum value
            - Matched FAQ question (if FAQ_MATCH) or None
            - Static response (if GREETING/THANKS) or None
        """
        if not query or not query.strip():
            return Intent.SEARCH, None, None
        
        query_lower = query.lower().strip()
        
        # Check for greeting (short queries only)
        if self._is_greeting(query_lower):
            logger.debug(f"Classified as GREETING: {query[:50]}")
            return Intent.GREETING, None, self.GREETING_RESPONSE
        
        # Check for thanks (short queries only)
        if self._is_thanks(query_lower):
            logger.debug(f"Classified as THANKS: {query[:50]}")
            return Intent.THANKS, None, self.THANKS_RESPONSE
        
        # Check for FAQ match (if rapidfuzz available)
        matched_faq = self._match_faq(query)
        if matched_faq:
            logger.debug(f"Classified as FAQ_MATCH: {query[:50]} -> {matched_faq[:50]}")
            return Intent.FAQ_MATCH, matched_faq, None
        
        # Default to search
        return Intent.SEARCH, None, None
    
    def _is_greeting(self, query: str) -> bool:
        """
        Check if query is a greeting.
        
        Only considers short queries (3 words or less) to avoid
        false positives on longer questions that happen to contain
        greeting words.
        
        Args:
            query: Lowercase, stripped query string
            
        Returns:
            True if query is classified as a greeting
        """
        # Only check short queries
        word_count = len(query.split())
        if word_count > 3:
            return False
        
        q = self._normalize(query)
        if not q:
            return False

        # Check for exact (normalized) or fuzzy matches
        for pattern in self.GREETING_PATTERNS:
            p = self._normalize(pattern)
            if not p:
                continue
            
            # Exact match only (prevents 'sup' matching 'supply')
            if q == p:
                return True
            
            # Use fuzzy matching for short, similar-length strings to catch typos
            if RAPIDFUZZ_AVAILABLE:
                if len(q) >= 3 and abs(len(q) - len(p)) <= 3:
                    if fuzz.ratio(q, p) > 80:
                        return True
        
        return False
    
    def _is_thanks(self, query: str) -> bool:
        """
        Check if query is a thank you message.
        
        Only considers short queries (5 words or less) to avoid
        false positives.
        
        Args:
            query: Lowercase, stripped query string
            
        Returns:
            True if query is classified as thanks
        """
        # Only check short queries
        word_count = len(query.split())
        if word_count > 5:
            return False
        
        q = self._normalize(query)
        if not q:
            return False

        # Check for exact (normalized) or fuzzy matches
        for pattern in self.THANKS_PATTERNS:
            p = self._normalize(pattern)
            if not p:
                continue
            
            # Exact match only (prevents accidental substring matches)
            if q == p:
                return True
            
            # Use fuzzy matching for short, similar-length strings to catch typos
            if RAPIDFUZZ_AVAILABLE:
                if len(q) >= 3 and abs(len(q) - len(p)) <= 4:
                    if fuzz.ratio(q, p) > 80:
                        return True
        
        return False
    
    def _match_faq(self, query: str) -> Optional[str]:
        """
        Fuzzy match against FAQ questions.
        
        Uses token_sort_ratio which is more robust to word order differences.
        For example, "what is litecoin" and "litecoin what is" would score highly.
        
        Args:
            query: The user's query string
            
        Returns:
            Matched FAQ question if similarity >= threshold, else None
        """
        if not RAPIDFUZZ_AVAILABLE:
            return None
        
        if not self.faq_questions:
            return None
        
        # Use extractOne for best match with token_sort_ratio scorer
        result = process.extractOne(
            query,
            self.faq_questions,
            scorer=fuzz.token_sort_ratio
        )
        
        if result and result[1] >= self.faq_match_threshold:
            matched_question = result[0]
            score = result[1]
            logger.debug(f"FAQ match: '{query}' -> '{matched_question}' (score: {score})")
            return matched_question
        
        return None


