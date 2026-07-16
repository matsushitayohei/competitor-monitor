"""Change summarization module using Amazon Bedrock (Claude)."""

from bedrock_client import invoke_claude


SYSTEM_PROMPT = """You are analyzing UI/UX changes on Japanese real estate websites.
Provide concise summaries in Japanese."""

SUMMARIZE_PROMPT = """以下のDOM差分を3行以内で日本語で要約してください。
ユーザーから見える変更点にフォーカスしてください。

DOM Diff:
{diff_text}

要約:"""


def summarize_change(diff_text: str) -> str:
    """Generate a brief summary of the change in Japanese.

    Returns:
        Summary text in Japanese (3 lines max).
    """
    prompt = SUMMARIZE_PROMPT.format(diff_text=diff_text)
    return invoke_claude(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        max_tokens=500,
        temperature=0.3,
    )
