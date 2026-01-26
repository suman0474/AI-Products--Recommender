"""
DEPRECATED COMPATIBILITY SHIM FOR OLD PROMPTS MODULE

This module provides backward compatibility for code still referencing the old
'prompts' module pattern (e.g., prompts.sales_agent_greeting_prompt).

ALL NEW CODE SHOULD USE:
    from prompts_library import load_prompt
    PROMPT = load_prompt("prompt_name")

This file will be removed in a future version.
"""

import warnings
from prompts_library import load_prompt, load_prompt_sections

# Show deprecation warning when this module is imported
warnings.warn(
    "The 'prompts' module is deprecated. Please use 'from prompts_library import load_prompt' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Load consolidated prompt files
_SALES_AGENT_PROMPTS = load_prompt_sections("sales_agent_prompts")
_SALES_WORKFLOW_PROMPTS = load_prompt_sections("sales_workflow_prompts")
_INTENT_PROMPTS = load_prompt_sections("intent_prompts")
_PPI_PROMPTS = load_prompt_sections("potential_product_index_prompts")
_RANKING_PROMPTS = load_prompt_sections("ranking_prompts")


# ========================================================================================
# SALES AGENT PROMPTS (Legacy - for main.py compatibility)
# These should be refactored to use the new sales_agent_tools.py
# ========================================================================================

# Legacy sales agent prompts - load from consolidated files
sales_agent_knowledge_question_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_initial_input_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_no_additional_specs_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_yes_additional_specs_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_acknowledge_additional_specs_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_default_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_advanced_specs_yes_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_advanced_specs_no_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_advanced_specs_display_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_confirm_after_missing_info_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_confirm_after_missing_info_with_params_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_show_summary_proceed_prompt = _SALES_WORKFLOW_PROMPTS["SUMMARY_GENERATION"]
sales_agent_show_summary_intro_prompt = _SALES_WORKFLOW_PROMPTS["SUMMARY_GENERATION"]
sales_agent_final_analysis_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_analysis_error_prompt = _SALES_AGENT_PROMPTS["MAIN"]
sales_agent_greeting_prompt = _SALES_WORKFLOW_PROMPTS["GREETING"]

# ========================================================================================
# FEEDBACK PROMPTS (Legacy)
# ========================================================================================

feedback_positive_prompt = "Thank you for your positive feedback!"
feedback_negative_prompt = "Thank you for your feedback. We'll use it to improve."
feedback_comment_prompt = "Thank you for your comment: {comment}"

# ========================================================================================
# IDENTIFICATION PROMPTS (Legacy - replaced by identify_instruments_tool)
# ========================================================================================

identify_classification_prompt = _INTENT_PROMPTS["CLASSIFICATION"]
identify_greeting_prompt = _SALES_WORKFLOW_PROMPTS["GREETING"]
identify_instrument_prompt = load_prompt("instrument_identification_prompt") # Still individual
identify_unrelated_prompt = _INTENT_PROMPTS["CLASSIFICATION"]
identify_question_prompt = load_prompt("question_classification_prompt") # Still individual
identify_fallback_prompt = _INTENT_PROMPTS["CLASSIFICATION"]
identify_unexpected_prompt = _INTENT_PROMPTS["CLASSIFICATION"]

# ========================================================================================
# MANUFACTURER/VENDOR PROMPTS (Legacy)
# ========================================================================================

manufacturer_domain_prompt = _PPI_PROMPTS["VENDOR_DISCOVERY"]

# ========================================================================================
# VALIDATION PROMPTS (Legacy - replaced by schema_tools.py)
# ========================================================================================

validation_prompt = load_prompt("schema_validation_prompt") # Still individual
validation_alert_initial_prompt = "Please review the validation results."
validation_alert_repeat_prompt = "Please address the validation issues."

# ========================================================================================
# REQUIREMENT EXPLANATION PROMPTS (Legacy)
# ========================================================================================

requirement_explanation_prompt = _INTENT_PROMPTS["REQUIREMENTS_EXTRACTION"]

# ========================================================================================
# ADVANCED PARAMETER PROMPTS (Legacy)
# ========================================================================================

advanced_parameter_selection_prompt = _SALES_WORKFLOW_PROMPTS["PARAMETER_SELECTION"]

# ========================================================================================
# PROMPT GETTER FUNCTIONS (Required by chaining.py)
# These functions format prompts with variables for the analysis chain
# ========================================================================================

def get_validation_prompt(user_input: str, schema: str, format_instructions: str) -> str:
    """
    Build validation prompt for requirement extraction.
    Used by chaining.py invoke_validation_chain().
    """
    template = load_prompt("schema_validation_prompt") # Still individual
    # Template uses: {user_input}, {product_type}, {schema}
    # format_instructions not used in this template, but we need product_type
    return template.format(
        user_input=user_input,
        product_type="",  # Will be detected from input
        schema=schema
    )


def get_requirements_prompt(user_input: str) -> str:
    """
    Build requirements extraction prompt.
    Used by chaining.py invoke_requirements_chain().
    """
    # Use the loaded prompt string and create a template from it, because it's just a string now
    from langchain_core.prompts import PromptTemplate
    template_str = _INTENT_PROMPTS["REQUIREMENTS_EXTRACTION"]
    # The prompt typically has {user_input} in it.
    # Note: load_prompt returned a string, so we need to format it or use PromptTemplate
    # The original code likely used load_prompt which returned a string, then .format() on string?
    # Yes, str.format()works if the string has {placeholders}.
    return template_str.format(user_input=user_input)


def get_vendor_prompt(
    structured_requirements: str,
    products_json: str,
    pdf_content_json: str,
    format_instructions: str
) -> str:
    """
    Build vendor analysis prompt.
    Used by chaining.py invoke_vendor_chain().
    """
    template = load_prompt("analysis_tool_vendor_analysis_prompt") # Still individual
    # Template uses: {vendor}, {requirements}, {pdf_content}, {product_data}
    return template.format(
        vendor="",  # Will be filled by caller or extracted from context
        requirements=structured_requirements,
        pdf_content=pdf_content_json,
        product_data=products_json
    )


def get_ranking_prompt(vendor_analysis: str, format_instructions: str) -> str:
    """
    Build ranking prompt for product comparison.
    Used by chaining.py invoke_ranking_chain().
    """
    template = _RANKING_PROMPTS["RANKING"]
    # Template uses: {requirements}, {vendor_matches}
    return template.format(
        requirements="See vendor analysis for original requirements",
        vendor_matches=vendor_analysis
    )


def get_additional_requirements_prompt(
    user_input: str,
    product_type: str,
    schema: str,
    format_instructions: str
) -> str:
    """
    Build additional requirements extraction prompt.
    Used by chaining.py invoke_additional_requirements_chain().
    """
    template = _INTENT_PROMPTS["REQUIREMENTS_EXTRACTION"]
    return template.format(
        user_input=user_input,
        product_type=product_type,
        schema=schema,
        format_instructions=format_instructions
    )


def get_schema_description_prompt(field_name: str, product_type: str) -> str:
    """
    Build schema field description prompt.
    Used by chaining.py invoke_schema_description_chain().
    """
    # Simple template for field descriptions
    return f"""You are an industrial instrumentation expert.

Provide a clear, concise explanation of the technical specification field "{field_name}" 
for a {product_type}.

Include:
1. What this field measures or represents
2. Common values or ranges
3. Why it matters for product selection

Keep the explanation under 100 words."""


# ========================================================================================
# Note: This compatibility layer maps old prompt names to new prompts_library names
# Where exact matches don't exist, we use the closest equivalent prompt
# ========================================================================================
