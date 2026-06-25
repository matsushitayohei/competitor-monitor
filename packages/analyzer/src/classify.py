"""Change classification module using Google Gemini."""

import google.generativeai as genai
import os


CATEGORIES = ["CRO", "AD_PRODUCT", "SEO", "AI", "OTHER"]

CLASSIFY_PROMPT = """
You are a product analyst for a Japanese real estate portal site.
Analyze the following DOM change and classify it into one of these categories:
- CRO: Conversion rate optimization, UI improvements, form optimization, CTA changes
- AD_PRODUCT: New ad slots, ad format changes, ad placement changes
- SEO: Structured data changes, meta info changes, internal link changes
- AI: AI recommendations, chatbots, AI search features
- OTHER: Design changes, branding, etc.

DOM Change:
{diff_text}

Respond in JSON format:
{{"category": "<category>", "confidence": <0-1>, "reason": "<brief reason>"}}
"""


def classify_change(diff_text: str) -> dict:
    """Classify a DOM change using Gemini."""
    genai.configure(api_key=os.environ["GOOGLE_AI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(CLASSIFY_PROMPT.format(diff_text=diff_text))
    return response.text
