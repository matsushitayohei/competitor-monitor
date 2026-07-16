"""Change summarization module."""

import google.generativeai as genai
import os


SUMMARIZE_PROMPT = """
You are analyzing a UI/UX change on a Japanese real estate website.
Summarize the following DOM diff in 3 lines or less, in Japanese.
Focus on what the user-visible change is.

DOM Diff:
{diff_text}

Summary (in Japanese, 3 lines max):
"""

_model = None


def _get_model():
    """Get or initialize the Gemini model (singleton)."""
    global _model
    if _model is None:
        genai.configure(api_key=os.environ["GOOGLE_AI_API_KEY"])
        _model = genai.GenerativeModel(
            "gemini-1.5-pro",
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=500,
            ),
        )
    return _model


def summarize_change(diff_text: str) -> str:
    """Generate a brief summary of the change in Japanese."""
    model = _get_model()
    response = model.generate_content(
        SUMMARIZE_PROMPT.format(diff_text=diff_text)
    )
    return response.text
