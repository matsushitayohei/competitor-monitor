"""Change classification module using Amazon Bedrock (Claude)."""

from bedrock_client import invoke_claude


CATEGORIES = ["CRO", "AD_PRODUCT", "SEO", "AI", "OTHER"]

SYSTEM_PROMPT = """You are a product analyst for a Japanese real estate portal site.
You classify UI/UX changes into exactly one category. Always respond in valid JSON only."""

CLASSIFY_PROMPT = """Analyze the following DOM change and classify it into one of these categories:
- CRO: Conversion rate optimization, UI improvements, form optimization, CTA changes
- AD_PRODUCT: New ad slots, ad format changes, ad placement changes
- SEO: Structured data changes, meta info changes, internal link changes
- AI: AI recommendations, chatbots, AI search features
- OTHER: Design changes, branding, etc.

DOM Change:
{diff_text}

Respond in JSON format only:
{{"category": "<category>", "confidence": <0-1>, "reason": "<brief reason in Japanese>"}}"""


def classify_change(diff_text: str) -> str:
    """Classify a DOM change using Claude via Bedrock.

    Returns:
        JSON string with category, confidence, and reason.
    """
    prompt = CLASSIFY_PROMPT.format(diff_text=diff_text)
    return invoke_claude(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        max_tokens=256,
        temperature=0.2,
        json_mode=True,
    )
