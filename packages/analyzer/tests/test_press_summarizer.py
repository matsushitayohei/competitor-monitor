"""Unit tests for press_summarizer module."""

import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from press_summarizer import (
    summarize_press_article,
    _extract_key_sentences,
    _truncate_at_sentence_boundary,
    _split_into_sentences,
)


class TestTruncateAtSentenceBoundary:
    """Tests for _truncate_at_sentence_boundary."""

    def test_short_text_returns_as_is(self):
        text = "短いテキスト。"
        assert _truncate_at_sentence_boundary(text, 200) == text

    def test_exact_max_length_returns_as_is(self):
        text = "あ" * 200
        assert _truncate_at_sentence_boundary(text, 200) == text

    def test_truncates_at_maru(self):
        text = "最初の文。二番目の文。三番目の文は長いです。" + "あ" * 200
        result = _truncate_at_sentence_boundary(text, 30)
        assert result.endswith("。")
        assert len(result) <= 30

    def test_truncates_at_exclamation(self):
        text = "すごい！これは長いテキストです。" + "あ" * 200
        result = _truncate_at_sentence_boundary(text, 5)
        assert result == "すごい！"

    def test_truncates_at_question(self):
        text = "本当？これは長いテキストです。" + "あ" * 200
        result = _truncate_at_sentence_boundary(text, 5)
        assert result == "本当？"

    def test_no_boundary_hard_truncates(self):
        text = "あ" * 300
        result = _truncate_at_sentence_boundary(text, 200)
        assert len(result) == 200

    def test_empty_text(self):
        assert _truncate_at_sentence_boundary("", 200) == ""


class TestExtractKeySentences:
    """Tests for _extract_key_sentences."""

    def test_extracts_service_feature_keywords(self):
        body = "当社は新機能を開発しました。これにより使いやすさが向上します。関係ないことです。"
        result = _extract_key_sentences(body, "service_feature")
        assert len(result) >= 1
        assert any("新機能" in s for s in result)

    def test_extracts_market_data_keywords(self):
        body = "調査結果を発表しました。前年比で20%増加しています。その他の話。"
        result = _extract_key_sentences(body, "market_data")
        assert len(result) >= 1
        assert any("調査" in s for s in result)

    def test_extracts_pricing_keywords(self):
        body = "料金プランを改定しました。月額500円から利用可能です。詳細はこちら。"
        result = _extract_key_sentences(body, "pricing")
        assert len(result) >= 1
        assert any("料金" in s for s in result)

    def test_other_category_returns_empty(self):
        body = "何らかのテキストです。特にキーワードはありません。"
        result = _extract_key_sentences(body, "other")
        assert result == []

    def test_unknown_category_returns_empty(self):
        body = "何らかのテキストです。"
        result = _extract_key_sentences(body, "unknown_category")
        assert result == []

    def test_empty_body_returns_empty(self):
        result = _extract_key_sentences("", "service_feature")
        assert result == []


class TestSplitIntoSentences:
    """Tests for _split_into_sentences."""

    def test_splits_on_maru(self):
        text = "最初の文。二番目の文。"
        result = _split_into_sentences(text)
        assert result == ["最初の文。", "二番目の文。"]

    def test_splits_on_mixed_delimiters(self):
        text = "文一。文二！文三？"
        result = _split_into_sentences(text)
        assert result == ["文一。", "文二！", "文三？"]

    def test_trailing_text_without_delimiter(self):
        text = "最初の文。残りのテキスト"
        result = _split_into_sentences(text)
        assert result == ["最初の文。", "残りのテキスト"]

    def test_empty_text(self):
        result = _split_into_sentences("")
        assert result == []


class TestSummarizePressArticle:
    """Tests for summarize_press_article."""

    def test_empty_body_returns_empty(self):
        assert summarize_press_article("", "service_feature") == ""

    def test_whitespace_only_returns_empty(self):
        assert summarize_press_article("   ", "service_feature") == ""

    def test_short_body_in_range_returned_as_is(self):
        body = "あ" * 80  # 80 chars, within 50-200 range
        result = summarize_press_article(body, "service_feature")
        assert result == body

    def test_short_body_under_50_returned_as_is(self):
        body = "短い文。"
        result = summarize_press_article(body, "service_feature")
        assert result == body

    def test_summary_max_200_chars(self):
        # Create a long body with many sentences
        body = "新機能をリリースしました。" * 50
        result = summarize_press_article(body, "service_feature")
        assert len(result) <= 200

    def test_summary_includes_first_sentence(self):
        body = "SUUMOが新機能を提供開始しました。これは画期的なサービスです。今後もアップデートを続けていきます。その他の情報。追加の文章がここに入ります。"
        result = summarize_press_article(body, "service_feature")
        # First sentence should be included
        assert "SUUMOが新機能を提供開始しました。" in result

    def test_summary_prioritizes_category_keywords(self):
        body = "プレスリリースです。関係ない文章です。新機能として検索を強化しました。その他のお知らせ。"
        result = summarize_press_article(body, "service_feature")
        # Should include keyword-containing sentence
        assert "新機能" in result

    def test_long_first_sentence_truncated(self):
        # First sentence is over 200 chars
        body = "あ" * 250 + "。次の文。"
        result = summarize_press_article(body, "service_feature")
        assert len(result) <= 200

    def test_body_exactly_200_chars(self):
        body = "あ" * 200
        result = summarize_press_article(body, "service_feature")
        assert result == body
        assert len(result) == 200

    def test_body_exactly_50_chars(self):
        body = "あ" * 50
        result = summarize_press_article(body, "service_feature")
        assert result == body
        assert len(result) == 50

    def test_realistic_article_service_feature(self):
        body = (
            "株式会社カナリーは、賃貸物件検索アプリ「カナリー」において新機能「AI物件提案」の提供を開始しました。"
            "この機能は、ユーザーの検索履歴や閲覧パターンをAIが分析し、最適な物件を自動提案するものです。"
            "従来の検索に加え、ユーザーが気づかなかった好条件の物件を発見できるようになります。"
            "利用は無料で、アプリを最新版にアップデートすることで利用可能です。"
        )
        result = summarize_press_article(body, "service_feature")
        assert 50 <= len(result) <= 200

    def test_realistic_article_market_data(self):
        body = (
            "株式会社リクルートは、2024年度の賃貸市場動向に関する調査結果を発表しました。"
            "調査によると、首都圏の平均家賃は前年比3.2%増加しています。"
            "特にワンルーム物件の需要が高まっており、空室率は過去最低のデータとなりました。"
            "今後も賃料の上昇傾向が続くと予測されています。"
        )
        result = summarize_press_article(body, "market_data")
        assert 50 <= len(result) <= 200
