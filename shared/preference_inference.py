"""LLM-based inference of user preferences from message content.

Determines output_format, require_code_approval, and clean_message (with format hints stripped).
No regex or hardcoded patterns – uses structured LLM output.
"""

import logging
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class InferredPreferences(BaseModel):
    """Structured output from preference inference."""

    output_format: Literal["json", "pdf", "xl", "audio"] = Field(
        description="Output format: json (default), pdf, xl (Excel), or audio"
    )
    require_code_approval: bool = Field(
        description="True if user wants to approve code before it runs (e.g. 'approve before running', 'review code first')"
    )
    clean_message: str = Field(
        description="The message with output format hints removed (e.g. 'give me pdf' stripped) so agents focus on the task"
    )
    format_hint: str = Field(
        default="",
        description="Instruction for the planner on how to format the final output (e.g. 'Format as markdown table', 'Format as concise spoken summary'). Empty if json.",
    )


INFERENCE_SYSTEM = """You are a preference extractor. Given a user message, determine:
1. output_format: json (default), pdf, xl (Excel), or audio. Choose based on what the user asks for (e.g. "give me a pdf", "excel spreadsheet", "read aloud", "as audio").
2. require_code_approval: true only if the user explicitly wants to approve/review code before execution (e.g. "approve before running", "show me code first", "review before running"). Default false.
3. clean_message: the same message but with output format phrases removed so the task is clear. E.g. "give me a pdf of top companies" -> "top companies". Keep the core task intact. If no format hints, return the message unchanged.
4. format_hint: a brief instruction for the planner on how to format the final output. Examples:
   - For xl/Excel: "Format the final output as a markdown table with | separators."
   - For pdf: "Format the final output with clear headings, structured lists, and readable paragraphs."
   - For audio: "Format the final output as a concise spoken summary."
   - For json: leave empty."""


async def infer_preferences(
    message: str,
    explicit_format: str = "json",
    explicit_require_approval: bool = False,
) -> InferredPreferences:
    """Infer output_format, require_code_approval, and clean_message from user message via LLM.

    When explicit_format is not "json" or explicit_require_approval is True, those override inference.
    """
    from shared.llm import get_llm, is_llm_available

    if not is_llm_available("classify"):
        return InferredPreferences(
            output_format=explicit_format if explicit_format != "json" else "json",
            require_code_approval=explicit_require_approval,
            clean_message=message,
            format_hint="",
        )

    format_override = explicit_format if explicit_format not in ("json", "auto") else None
    approval_override = explicit_require_approval

    user_content = f"Message: {message}"
    if format_override:
        user_content += f"\n\n(Use output_format={format_override} – user explicitly selected this.)"
    if approval_override:
        user_content += "\n\n(Use require_code_approval=true – user explicitly enabled this.)"

    try:
        llm = get_llm("classify", temperature=0)
        structured = llm.with_structured_output(InferredPreferences)
        result = await structured.ainvoke([
            {"role": "system", "content": INFERENCE_SYSTEM},
            {"role": "user", "content": user_content},
        ])
        if format_override:
            result = InferredPreferences(
                output_format=format_override,
                require_code_approval=result.require_code_approval,
                clean_message=result.clean_message,
                format_hint=result.format_hint,
            )
        if approval_override:
            result = InferredPreferences(
                output_format=result.output_format,
                require_code_approval=True,
                clean_message=result.clean_message,
                format_hint=result.format_hint,
            )
        return result
    except Exception as e:
        logger.warning("Preference inference failed: %s – using defaults", e)
        return InferredPreferences(
            output_format=explicit_format if explicit_format in ("pdf", "xl", "audio") else "json",
            require_code_approval=explicit_require_approval,
            clean_message=message,
            format_hint="",
        )
