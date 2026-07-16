"""AI advice generation module using Amazon Bedrock (Claude)."""

from bedrock_client import invoke_claude


SYSTEM_PROMPT = """You are a senior product manager at LIFULL HOME'S, a major Japanese real estate portal.
You analyze competitor changes and provide actionable advice. Always respond in valid JSON only."""

ADVICE_PROMPT = """A competitor has made the following UI/UX change:

Competitor: {service_name}
Page Type: {page_type}
Change Category: {category}
Change Summary: {diff_summary}

LIFULL HOME'Sがこの変更を参考にすべきかアドバイスしてください。

以下のJSON形式で回答してください:
{{
  "summary": "<何が変わったか1-2文>",
  "intent": "<なぜこの変更をしたと考えられるか>",
  "proposal": "<LIFULL HOME'Sがどう取り入れるべきか>",
  "priority": "<high/medium/low>",
  "expected_effect": "<導入した場合の期待効果>",
  "risks": "<リスクや懸念点>"
}}"""


def generate_advice(
    service_name: str,
    page_type: str,
    category: str,
    diff_summary: str,
) -> str:
    """Generate AI advice for a detected change.

    Returns:
        JSON string with advice fields.
    """
    prompt = ADVICE_PROMPT.format(
        service_name=service_name,
        page_type=page_type,
        category=category,
        diff_summary=diff_summary,
    )
    return invoke_claude(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        max_tokens=1024,
        temperature=0.4,
        json_mode=True,
    )
