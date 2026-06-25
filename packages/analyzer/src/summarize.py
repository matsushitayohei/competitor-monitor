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


def summarize_change(diff_text: str) -> str:
    """Generate a brief summary of the change in Japanese."""
    genai.configure(api_key=os.environ["GOOGLE_AI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-pro")
    
    response = model.generate_content(
        SUMMARIZE_PROMPT.format(diff_text=diff_text)
    )
    return response.text
