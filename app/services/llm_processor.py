"""LLM-based tokenization and tagging using DeepSeek API."""

import asyncio
import json
from openai import AsyncOpenAI
from typing import Optional
from app.core.config import settings
from app.models.schemas import TokenTag
from app.utils.retry import retry_with_backoff
from app.utils.circuit_breaker import CircuitBreaker, CircuitOpenError


FILTERING_RULES = """
CRITICAL FILTERING RULES - DO NOT include these in tokenization:

1. STOPWORDS: Common words with no product meaning
   - English: the, a, an, and, or, for, with, in, on, at, to, from, of, by
   - Chinese: 的, 了, 在, 是, 和, 与, 或, 为, 以
   - Japanese: の, は, を, に, が, で, と, へ, や
   - German: der, die, das, und, oder, für, mit, von, zu
   - French: le, la, les, un, une, et, ou, de, du, des
   - Spanish: el, la, los, las, un, una, y, o, de, del
   - Portuguese: o, a, os, as, um, uma, e, ou, de, do
   - Indonesian: yang, dan, atau, untuk, dengan, dari, ke
   - Russian: и, или, для, с, от, к, в, на
   - Korean: 의, 는, 을, 를, 이, 가, 에, 와

2. PROMOTIONAL TERMS: Not part of product identity
   - free, shipping, sale, discount, off, deal, promotion, limited, new, best, hot
   - 免费, 促销, 打折, 优惠, 包邮, 特价, 限时, 新品
   - 無料, セール, 割引, 特価, 送料無料
   - kostenlos, versand, angebot, rabatt, neu
   - gratuit, livraison, solde, promotion, nouveau
   - gratis, envío, oferta, descuento, nuevo
   - grátis, frete, oferta, desconto, novo

3. NOISE:
   - Single characters (unless part of model numbers like "iPhone X", "Type-C")
   - Pure numbers without units (unless sizes: "500ml", "3-pack", "256GB" are OK)
   - HTML/special chars: &, <, >, #, @, etc.
   - Extra whitespace or punctuation only

4. CONFIDENCE MARKING:
   - Mark confidence < 0.5 for highly ambiguous terms
   - Common words that might be product terms (e.g., "new", "pro", "plus") should have confidence 0.7-0.8

If a term should be excluded, DO NOT include it in the output tokens array.
Only return meaningful product-related tokens.
"""


class LLMProcessor:
    """Processes keywords using DeepSeek API for tokenization and tagging."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        self.model_name = settings.deepseek_model
        self.temperature = settings.deepseek_temperature
        self.circuit_breaker = CircuitBreaker(
            threshold=settings.llm_circuit_breaker_threshold,
            timeout=settings.llm_circuit_breaker_timeout
        )

    def _build_prompt(self, keyword: str, language: str) -> str:
        """Build the prompt for LLM processing."""
        lang_names = {
            "zh": "Chinese",
            "en": "English",
            "es": "Spanish",
            "ja": "Japanese",
            "ko": "Korean",
            "de": "German",
            "fr": "French",
            "pt": "Portuguese",
            "id": "Indonesian",
            "ru": "Russian",
        }

        prompt = f"""You are an e-commerce keyword tokenization and tagging expert.

Task: Tokenize the following {lang_names.get(language, 'English')} product keyword and tag each token with semantic categories.

{FILTERING_RULES}

CRITICAL RULES:
1. **PRESERVE MULTI-WORD ENTITIES**: Keep product names, model numbers, and brand+model combinations together
   - "iPhone 15 Pro" → ONE token (not ["iPhone", "15", "Pro"])
   - "Air Max 90" → ONE token
   - "跑步鞋" → ONE token (not ["跑步", "鞋"])

2. **TOKENIZATION GUIDELINES**:
   - Brand + Model = one token (e.g., "Galaxy S23")
   - Product categories = separate if standalone (e.g., "shoes")
   - Attributes/specs = separate (e.g., "256GB", "black")
   - Multi-word descriptors = keep together if they form a semantic unit

3. **TAG TYPES** (a token can have multiple tags):
   - brand_term: Brand names (Apple, Nike, 华为)
   - product_term: Product categories (shoes, laptop, 手机)
   - audience_term: Target demographic (men, kids, 学生)
   - scenario_term: Usage context (running, office, 运动)
   - color_term: Colors (black, red, 黑色)
   - size_term: Sizes/dimensions (10.5, 256GB, XL)
   - selling_point_term: Features (waterproof, wireless, 防水)
   - attribute_term: Technical specs (memory, battery, 内存)

4. **CONFIDENCE SCORING**:
   - 0.95: Clear, unambiguous terms
   - 0.85: High confidence but some context-dependence
   - 0.70: Uncertain, needs more context

Keyword: "{keyword}"

Return ONLY a JSON object with this exact structure:
{{
  "tokens": [
    {{"token": "...", "tags": ["tag1", "tag2"], "confidence": 0.95}},
    ...
  ]
}}

Examples for {lang_names.get(language, 'English')}:
"""

        # Add language-specific examples
        if language == "zh":
            return prompt + """
Example 1:
Input: "Apple iPhone 15 Pro 256GB 黑色"
Output: {
  "tokens": [
    {"token": "Apple", "tags": ["brand_term"], "confidence": 0.95},
    {"token": "iPhone 15 Pro", "tags": ["product_term"], "confidence": 0.95},
    {"token": "256GB", "tags": ["size_term", "attribute_term"], "confidence": 0.95},
    {"token": "黑色", "tags": ["color_term"], "confidence": 0.95}
  ]
}

Example 2:
Input: "耐克男款跑步鞋"
Output: {
  "tokens": [
    {"token": "耐克", "tags": ["brand_term"], "confidence": 0.95},
    {"token": "男款", "tags": ["audience_term"], "confidence": 0.95},
    {"token": "跑步鞋", "tags": ["product_term", "scenario_term"], "confidence": 0.95}
  ]
}
"""
        elif language == "en":
            return prompt + """
Example 1:
Input: "Nike Air Max 90 men's black running shoes"
Output: {
  "tokens": [
    {"token": "Nike", "tags": ["brand_term"], "confidence": 0.95},
    {"token": "Air Max 90", "tags": ["product_term"], "confidence": 0.95},
    {"token": "men's", "tags": ["audience_term"], "confidence": 0.95},
    {"token": "black", "tags": ["color_term"], "confidence": 0.95},
    {"token": "running shoes", "tags": ["product_term", "scenario_term"], "confidence": 0.95}
  ]
}

Example 2:
Input: "Apple MacBook Pro 14-inch M3 Pro 1TB Space Gray"
Output: {
  "tokens": [
    {"token": "Apple", "tags": ["brand_term"], "confidence": 0.95},
    {"token": "MacBook Pro", "tags": ["product_term"], "confidence": 0.95},
    {"token": "14-inch", "tags": ["size_term"], "confidence": 0.95},
    {"token": "M3 Pro", "tags": ["attribute_term"], "confidence": 0.95},
    {"token": "1TB", "tags": ["size_term", "attribute_term"], "confidence": 0.95},
    {"token": "Space Gray", "tags": ["color_term"], "confidence": 0.95}
  ]
}
"""
        else:  # es, ja, ko - simplified
            return prompt + """
Ensure you preserve multi-word entities and provide accurate tags based on semantic meaning.
"""

        return prompt

    def _parse_response(self, response) -> Optional[list[TokenTag]]:
        """
        Parse LLM response with robust error handling.

        Args:
            response: Raw response from LLM API

        Returns:
            List of TokenTag objects or None if parsing fails
        """
        try:
            content = response.choices[0].message.content
            data = json.loads(content)

            # Validate structure
            if "tokens" not in data:
                print("Warning: LLM response missing 'tokens' field")
                return None

            tokens = []
            for token_data in data["tokens"]:
                # Skip malformed tokens
                if "token" not in token_data or "tags" not in token_data:
                    continue

                tokens.append(
                    TokenTag(
                        token=token_data["token"],
                        tags=token_data.get("tags", []),
                        confidence=token_data.get("confidence", 0.5),
                    )
                )

            return tokens if tokens else None

        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
            print(f"Failed to parse LLM response: {e}")
            return None

    @retry_with_backoff(
        max_retries=settings.llm_max_retries,
        base_delay=settings.llm_retry_delay
    )
    async def process(
        self, keyword: str, language: str
    ) -> Optional[list[TokenTag]]:
        """
        Process keyword using LLM to tokenize and tag.

        Includes retry logic with exponential backoff and circuit breaker
        for resilience against LLM service failures.

        Args:
            keyword: The keyword to process
            language: Language code

        Returns:
            List of TokenTag objects or None if processing fails

        Raises:
            CircuitOpenError: When circuit breaker is open
            asyncio.TimeoutError: When request exceeds timeout
        """
        # Check circuit breaker first
        if self.circuit_breaker.is_open():
            raise CircuitOpenError("LLM service unavailable - circuit breaker open")

        try:
            prompt = self._build_prompt(keyword, language)

            # Call LLM with timeout
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    response_format={"type": "json_object"}
                ),
                timeout=settings.llm_request_timeout
            )

            # Parse response
            result = self._parse_response(response)

            # Record success
            self.circuit_breaker.record_success()

            return result

        except asyncio.TimeoutError as e:
            # Record failure and re-raise (retry decorator will catch it)
            self.circuit_breaker.record_failure()
            print(f"LLM timeout after {settings.llm_request_timeout}s for: {keyword}")
            raise

        except Exception as e:
            # Record failure and re-raise
            self.circuit_breaker.record_failure()
            print(f"LLM processing error: {e}")
            raise


# Global instance
llm_processor = LLMProcessor()
