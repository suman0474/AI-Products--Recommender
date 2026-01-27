# tools/intent_tools.py
# Intent Classification and Requirements Extraction Tools

import json
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import os
from llm_fallback import create_llm_with_fallback, invoke_with_retry_fallback
from prompts_library import load_prompt_sections
logger = logging.getLogger(__name__)


# ============================================================================
# TOOL INPUT SCHEMAS
# ============================================================================

class ClassifyIntentInput(BaseModel):
    """Input for intent classification"""
    user_input: str = Field(description="User's input message to classify")
    current_step: Optional[str] = Field(default=None, description="Current workflow step")
    context: Optional[str] = Field(default=None, description="Conversation context")


class ExtractRequirementsInput(BaseModel):
    """Input for requirements extraction"""
    user_input: str = Field(description="User's input containing requirements")


# ============================================================================
# PROMPTS - Loaded from consolidated prompts_library file
# ============================================================================

_INTENT_PROMPTS = load_prompt_sections("intent_prompts")

INTENT_CLASSIFICATION_PROMPT = _INTENT_PROMPTS["CLASSIFICATION"]
REQUIREMENTS_EXTRACTION_PROMPT = _INTENT_PROMPTS["REQUIREMENTS_EXTRACTION"]


# ============================================================================
# RULE-BASED CLASSIFICATION (OPTIMIZATION - avoid LLM for obvious intents)
# ============================================================================
# These patterns are checked BEFORE calling the LLM to save API calls.
# All callers of classify_intent_tool benefit automatically.

_GREETING_PHRASES = {'hi', 'hello', 'hey', 'hi there', 'hello there',
                     'good morning', 'good afternoon', 'good evening'}

_CONFIRM_PHRASES = {'yes', 'y', 'yep', 'yeah', 'sure', 'ok', 'okay',
                    'proceed', 'continue', 'go ahead', 'confirm', 'approved'}

_REJECT_PHRASES = {'no', 'n', 'nope', 'cancel', 'stop', 'reject', 'decline',
                   'never mind', 'nevermind', 'forget it'}

_KNOWLEDGE_STARTERS = [
    'what is ', 'what are ', 'what does ', "what's ",
    'how does ', 'how do ', 'how to ', 'how can ',
    'why is ', 'why does ', 'why do ', 'why are ',
    'tell me about ', 'explain ', 'define ', 'describe ',
    'difference between ', 'compare ', 'meaning of ', 'definition of '
]

_PRODUCT_REQUEST_STARTERS = [
    'i need a ', 'i need an ', 'looking for a ', 'looking for an ',
    'i want a ', 'i want an ', 'need a ', 'need an ',
    'find me a ', 'find a ', 'get me a ', 'show me ',
    'recommend a ', 'suggest a '
]


def _classify_rule_based(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Attempt rule-based intent classification without calling the LLM.

    Returns a result dict if a rule matches, or None if LLM is needed.
    This saves 1 LLM API call for ~40-60% of common queries.
    """
    query = user_input.lower().strip()

    # Pure greeting
    if query in _GREETING_PHRASES:
        logger.info(f"[INTENT_RULE] Greeting detected: '{query}'")
        return {
            "success": True,
            "intent": "greeting",
            "confidence": 1.0,
            "next_step": "greeting",
            "extracted_info": {"rule_based": True},
            "is_solution": False,
            "solution_indicators": []
        }

    # Confirm/Reject
    if query in _CONFIRM_PHRASES:
        logger.info(f"[INTENT_RULE] Confirm detected: '{query}'")
        return {
            "success": True,
            "intent": "confirm",
            "confidence": 1.0,
            "next_step": None,
            "extracted_info": {"rule_based": True},
            "is_solution": False,
            "solution_indicators": []
        }

    if query in _REJECT_PHRASES:
        logger.info(f"[INTENT_RULE] Reject detected: '{query}'")
        return {
            "success": True,
            "intent": "reject",
            "confidence": 1.0,
            "next_step": None,
            "extracted_info": {"rule_based": True},
            "is_solution": False,
            "solution_indicators": []
        }

    # Knowledge questions
    if any(query.startswith(p) for p in _KNOWLEDGE_STARTERS):
        logger.info(f"[INTENT_RULE] Knowledge question detected: '{query[:50]}'")
        return {
            "success": True,
            "intent": "question",
            "confidence": 0.95,
            "next_step": None,
            "extracted_info": {"rule_based": True},
            "is_solution": False,
            "solution_indicators": []
        }

    # Product requests - need to distinguish complex systems from simple requests (PHASE 2 FIX)
    if any(query.startswith(p) for p in _PRODUCT_REQUEST_STARTERS):
        # Detect complex system indicators
        complex_indicators = [
            'system', 'complete', 'profiling', 'multiple', 'design a',
            'comprehensive', 'circuit', 'package', 'skid', 'plant',
            'solution', 'full', 'integrated', 'platform', 'architecture',
            'end-to-end', 'complete solution', 'total solution'
        ]

        # Count how many complex indicators are present
        matched_indicators = [ind for ind in complex_indicators if ind in query]
        indicator_count = len(matched_indicators)
        is_complex = indicator_count >= 2

        # PHASE 2 FIX: Also check for explicit solution phrases
        solution_phrases = [
            'i\'m designing', 'i\'m building', 'i need a complete',
            'i need a system', 'planning a', 'creating a solution',
            'designing a', 'building a', 'implementing a solution'
        ]
        is_solution_phrase = any(phrase in query for phrase in solution_phrases)

        # Determine intent and is_solution flag (PHASE 2 FIX)
        if is_complex or is_solution_phrase:
            logger.info(
                f"[INTENT_RULE] Complex/solution request detected: '{query[:50]}' "
                f"(indicators={indicator_count}, solution_phrase={is_solution_phrase})"
            )
            return {
                "success": True,
                "intent": "solution",  # PHASE 2 FIX: Changed from "question" to "solution"
                "confidence": 0.85,
                "next_step": None,
                "extracted_info": {
                    "rule_based": True,
                    "complex_indicators": matched_indicators,
                    "indicator_count": indicator_count
                },
                "is_solution": True,  # PHASE 2 FIX: NOW SET TO TRUE
                "solution_indicators": matched_indicators
            }
        else:
            logger.info(f"[INTENT_RULE] Simple product request detected: '{query[:50]}'")
            return {
                "success": True,
                "intent": "requirements",  # PHASE 2 FIX: Changed from "question" to "requirements"
                "confidence": 0.9,
                "next_step": None,
                "extracted_info": {"rule_based": True},
                "is_solution": False,
                "solution_indicators": []
            }

    # No rule matched - need LLM
    return None


# ============================================================================
# TOOLS
# ============================================================================

@tool("classify_intent", args_schema=ClassifyIntentInput)
def classify_intent_tool(
    user_input: str,
    current_step: Optional[str] = None,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify user intent for routing in the procurement workflow.
    Returns intent type, confidence, and suggested next step.

    OPTIMIZATION: Tries rule-based classification first to avoid LLM calls
    for obvious intents (greetings, confirms, knowledge questions, simple requests).
    Falls back to LLM with invoke_with_retry_fallback for ambiguous queries.
    """
    # =========================================================================
    # STEP 1: Try rule-based classification (no LLM call)
    # =========================================================================
    rule_result = _classify_rule_based(user_input)
    if rule_result is not None:
        return rule_result

    # =========================================================================
    # STEP 2: Fall back to LLM classification
    # =========================================================================
    logger.info(f"[INTENT_LLM] Rule-based didn't match, calling LLM for: '{user_input[:60]}'")

    try:
        llm = create_llm_with_fallback(
            model="gemini-2.5-flash",
            temperature=0.1,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

        prompt = ChatPromptTemplate.from_template(INTENT_CLASSIFICATION_PROMPT)
        parser = JsonOutputParser()

        chain = prompt | llm | parser

        # Use retry wrapper with automatic key rotation and OpenAI fallback
        result = invoke_with_retry_fallback(
            chain,
            {
                "user_input": user_input,
                "current_step": current_step or "start",
                "context": context or "New conversation"
            },
            max_retries=3,
            fallback_to_openai=True,
            model="gemini-2.5-flash",
            temperature=0.1
        )

        return {
            "success": True,
            "intent": result.get("intent", "unrelated"),
            "confidence": result.get("confidence", 0.5),
            "next_step": result.get("next_step"),
            "extracted_info": result.get("extracted_info", {}),
            "is_solution": result.get("is_solution", False),
            "solution_indicators": result.get("solution_indicators", [])
        }

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return {
            "success": False,
            "intent": "unrelated",
            "confidence": 0.0,
            "next_step": None,
            "error": str(e)
        }


@tool("extract_requirements", args_schema=ExtractRequirementsInput)
def extract_requirements_tool(user_input: str) -> Dict[str, Any]:
    """
    Extract structured technical requirements from user input.
    Identifies product type, specifications, and infers missing common specs.

    Uses invoke_with_retry_fallback for automatic retry, key rotation,
    and OpenAI fallback on RESOURCE_EXHAUSTED errors.
    """
    try:
        llm = create_llm_with_fallback(
            model="gemini-2.5-flash",
            temperature=0.1,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

        prompt = ChatPromptTemplate.from_template(REQUIREMENTS_EXTRACTION_PROMPT)
        parser = JsonOutputParser()

        chain = prompt | llm | parser

        # Use retry wrapper with automatic key rotation and OpenAI fallback
        result = invoke_with_retry_fallback(
            chain,
            {"user_input": user_input},
            max_retries=3,
            fallback_to_openai=True,
            model="gemini-2.5-flash",
            temperature=0.1
        )

        return {
            "success": True,
            "product_type": result.get("product_type"),
            "specifications": result.get("specifications", {}),
            "inferred_specs": result.get("inferred_specs", {}),
            "raw_requirements_text": result.get("raw_requirements_text", user_input)
        }

    except Exception as e:
        logger.error(f"Requirements extraction failed: {e}")
        return {
            "success": False,
            "product_type": None,
            "specifications": {},
            "error": str(e)
        }
