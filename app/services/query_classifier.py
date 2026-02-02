"""
Query classifier to route simple vs complex queries to appropriate models.

Simple queries can use cheaper/faster models (Ollama, or Claude Haiku).
Complex queries need more powerful models (Claude Sonnet).

This can reduce LLM costs by 40-60%.
"""

import logging
import re

logger = logging.getLogger(__name__)


class QueryComplexity:
    """Query complexity levels."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class QueryClassifier:
    """
    Classify queries by complexity to route to appropriate LLM.

    Classification Criteria:

    SIMPLE:
    - Short queries (< 20 words)
    - Factual questions (who, what, when, where)
    - Single concept queries
    - Example: "What is the main topic?"

    MODERATE:
    - Medium queries (20-50 words)
    - Multiple concepts
    - Requires comparison
    - Example: "Compare X and Y"

    COMPLEX:
    - Long queries (> 50 words)
    - Requires reasoning, analysis, synthesis
    - Multi-step questions
    - Abstract concepts
    - Example: "Analyze the implications of X on Y and Z"
    """

    def __init__(self):
        """Initialize query classifier."""
        # Keywords indicating simple queries
        self.simple_indicators = {
            "what is",
            "who is",
            "when was",
            "where is",
            "define",
            "definition",
            "meaning of",
            "list",
            "name",
            "identify",
        }

        # Keywords indicating complex queries
        self.complex_indicators = {
            "analyze",
            "compare",
            "contrast",
            "evaluate",
            "explain why",
            "how does",
            "what are the implications",
            "synthesize",
            "critique",
            "assess",
            "reasoning",
            "argument",
            "perspective",
        }

        # Question patterns
        self.simple_patterns = [
            r"^what is ",
            r"^who is ",
            r"^when ",
            r"^where ",
            r"^how many ",
            r"^list ",
        ]

        self.complex_patterns = [
            r"compare .+ and ",
            r"analyze .+ in terms of",
            r"what are the implications",
            r"explain the relationship between",
            r"why does .+ affect ",
        ]

    def classify(self, query: str) -> str:
        """
        Classify query complexity.

        Args:
            query: User query text

        Returns:
            Complexity level: 'simple', 'moderate', or 'complex'
        """
        # Normalize query
        normalized = query.lower().strip()
        word_count = len(normalized.split())

        # Score for complexity
        complexity_score = 0

        # 1. Length-based scoring
        if word_count < 10:
            complexity_score -= 2
        elif word_count < 20:
            complexity_score -= 1
        elif word_count > 50:
            complexity_score += 2
        elif word_count > 30:
            complexity_score += 1

        # 2. Pattern matching
        for pattern in self.simple_patterns:
            if re.search(pattern, normalized):
                complexity_score -= 2
                break

        for pattern in self.complex_patterns:
            if re.search(pattern, normalized):
                complexity_score += 2
                break

        # 3. Keyword indicators
        for indicator in self.simple_indicators:
            if indicator in normalized:
                complexity_score -= 1
                break

        for indicator in self.complex_indicators:
            if indicator in normalized:
                complexity_score += 1

        # 4. Question marks (multiple questions = complex)
        question_marks = normalized.count("?")
        if question_marks > 1:
            complexity_score += 1

        # 5. Conjunctions (and, or, but) indicate multiple concepts
        conjunctions = len(re.findall(r"\b(and|or|but|however|moreover)\b", normalized))
        if conjunctions > 2:
            complexity_score += 1

        # Final classification
        if complexity_score <= -2:
            classification = QueryComplexity.SIMPLE
        elif complexity_score >= 2:
            classification = QueryComplexity.COMPLEX
        else:
            classification = QueryComplexity.MODERATE

        logger.info(
            f"Query classified as {classification.upper()} "
            f"(score: {complexity_score}, words: {word_count}): {query[:50]}..."
        )

        return classification

    def get_recommended_model(
        self,
        query: str,
        primary_provider: str,
    ) -> tuple[str, str]:
        """
        Get recommended model based on query complexity.

        Args:
            query: User query
            primary_provider: Primary LLM provider ('anthropic' or 'ollama')

        Returns:
            Tuple of (provider, model_name)
        """
        complexity = self.classify(query)

        if primary_provider == "anthropic":
            # Anthropic routing
            if complexity == QueryComplexity.SIMPLE:
                return ("anthropic", "claude-haiku-3-5-20241022")
            elif complexity == QueryComplexity.MODERATE:
                return ("anthropic", "claude-sonnet-4-20250514")
            else:  # COMPLEX
                return ("anthropic", "claude-sonnet-4-20250514")

        else:  # ollama
            # Ollama routing (use smaller models for simple queries)
            if complexity == QueryComplexity.SIMPLE:
                return ("ollama", "llama3.2:1b")  # Smallest model
            elif complexity == QueryComplexity.MODERATE:
                return ("ollama", "llama3.2")  # Standard model
            else:  # COMPLEX
                return ("ollama", "llama3.2:70b")  # Largest model

    def should_use_cache(self, query: str) -> bool:
        """
        Determine if query should use cache.

        Simple, factual queries benefit most from caching.
        Complex, analytical queries should bypass cache.

        Args:
            query: User query

        Returns:
            True if query should use cache
        """
        complexity = self.classify(query)

        # Cache simple and moderate queries
        # Complex queries often need fresh analysis
        return complexity in [QueryComplexity.SIMPLE, QueryComplexity.MODERATE]


# Global classifier instance
query_classifier = QueryClassifier()
