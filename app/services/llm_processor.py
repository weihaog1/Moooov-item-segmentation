"""LLM-based tokenization and tagging using DeepSeek API."""

import json
from openai import AsyncOpenAI
from typing import Optional
from app.core.config import settings
from app.models.schemas import TokenTag


class LLMProcessor:
    """Processes keywords using DeepSeek API for tokenization and tagging."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        self.model_name = settings.deepseek_model
        self.temperature = settings.deepseek_temperature

    def _build_prompt(self, keyword: str, language: str) -> str:
        """Build the prompt for LLM processing."""
        lang_names = {
            "zh": "Chinese",
            "en": "English",
            "es": "Spanish",
            "ja": "Japanese",
            "ko": "Korean",
        }

        return f"""You are an e-commerce keyword tokenization and tagging expert.

Task: Tokenize the following {lang_names.get(language, 'English')} product keyword and tag each token with semantic categories.

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

    async def process(
        self, keyword: str, language: str
    ) -> Optional[list[TokenTag]]:
        """
        Process keyword using LLM to tokenize and tag.

        Args:
            keyword: The keyword to process
            language: Language code

        Returns:
            List of TokenTag objects or None if processing fails
        """
        try:
            prompt = self._build_prompt(keyword, language)

            # Use OpenAI-compatible API format
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            # Parse JSON response from DeepSeek
            result = json.loads(response.choices[0].message.content)
            tokens_data = result.get("tokens", [])

            # Convert to TokenTag objects
            return [
                TokenTag(
                    token=t["token"],
                    tags=t.get("tags", []),
                    confidence=t.get("confidence", 0.7),
                )
                for t in tokens_data
            ]
        except Exception as e:
            # Log error but don't crash - return None for graceful degradation
            import traceback
            print(f"LLM processing error: {e}")
            print(f"Full traceback:\n{traceback.format_exc()}")
            return None


# Global instance
llm_processor = LLMProcessor()
