"""AI advice generation module using Google Gemini."""

import google.generativeai as genai
import os


ADVICE_PROMPT = """
You are a senior product manager at LIFULL HOME'S, a major Japanese real estate portal.
A competitor has made the following UI/UX change:

Competitor: {service_name}
Page Type: {page_type}
Change Category: {category}
Change Summary: {diff_summary}

Please provide advice in Japanese on whether LIFULL HOME'S should adopt a similar change.

Respond in JSON format:
{{
  "summary": "<what changed in 1-2 sentences>",
  "intent": "<why they likely made this change>",
  "proposal": "<how LIFULL HOME'S could adopt this>",
  "priority": "<high/medium/low>",
  "expected_effect": "<expected impact if adopted>",
  "risks": "<potential risks or concerns>"
}}
"""


def generate_advice(
    service_name: str,
    page_type: str,
    category: str,
    diff_summary: str,
) -> str:
    """Generate AI advice for a detected change."""
    genai.configure(api_key=os.environ["GOOGLE_AI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-pro")
    
    prompt = ADVICE_PROMPT.format(
        service_name=service_name,
        page_type=page_type,
        category=category,
        diff_summary=diff_summary,
    )
    
    response = model.generate_content(prompt)
    return response.text
