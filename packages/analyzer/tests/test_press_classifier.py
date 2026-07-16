"""Unit tests for press article classifier."""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from press_classifier import (
    classify_press_article,
    ClassificationResult,
    CONFIDENCE_THRESHOLD,
)


class TestClassifyPressArticle:
    """Tests for classify_press_article function."""

    # --- Empty content tests ---

    def test_empty_title_and_body_returns_classification_failed(self):
        result = classify_press_article("", "")
        assert result.is_relevant is False
        assert result.category == "classification_failed"
        assert result.confidence == 0.0
        assert result.needs_manual_review is False

    def test_none_like_whitespace_returns_classification_failed(self):
        result = classify_press_article("   ", "   ")
        assert result.is_relevant is False
        assert result.category == "classification_failed"

    # --- Irrelevant pattern tests ---

    def test_personnel_change_is_irrelevant(self):
        result = classify_press_article("人事異動のお知らせ", "取締役の変更について")
        assert result.is_relevant is False
        assert result.category is None

    def test_ir_announcement_is_irrelevant(self):
        result = classify_press_article("2025年度決算報告", "株主の皆様へ配当のご案内")
        assert result.is_relevant is False
        assert result.category is None

    def test_event_announcement_is_irrelevant(self):
        result = classify_press_article("不動産セミナー開催", "展示会のお知らせ")
        assert result.is_relevant is False
        assert result.category is None

    def test_csr_is_irrelevant(self):
        result = classify_press_article("CSR活動報告", "SDGs達成に向けた取り組み")
        assert result.is_relevant is False
        assert result.category is None

    def test_office_move_is_irrelevant(self):
        result = classify_press_article("オフィス移転のお知らせ", "新オフィスについて")
        assert result.is_relevant is False
        assert result.category is None

    # --- Relevant pattern tests ---

    def test_new_feature_is_service_feature(self):
        result = classify_press_article(
            "新機能リリースのお知らせ",
            "本日より新サービスの提供開始いたします。機能追加により使いやすくなりました。"
        )
        assert result.is_relevant is True
        assert result.category == "service_feature"
        assert result.confidence >= CONFIDENCE_THRESHOLD

    def test_market_data_is_market_data(self):
        result = classify_press_article(
            "不動産市場調査レポート公開",
            "最新の統計データに基づくトレンド分析。市場動向をまとめた白書を発行。"
        )
        assert result.is_relevant is True
        assert result.category == "market_data"
        assert result.confidence >= CONFIDENCE_THRESHOLD

    def test_ux_improvement_is_ux_improvement(self):
        result = classify_press_article(
            "サイトリニューアルのお知らせ",
            "UI/UXデザインを刷新し、ユーザビリティを大幅に改善しました。"
        )
        assert result.is_relevant is True
        assert result.category == "ux_improvement"
        assert result.confidence >= CONFIDENCE_THRESHOLD

    def test_pricing_change_is_pricing(self):
        result = classify_press_article(
            "料金プラン改定のお知らせ",
            "新しい価格プランを導入します。一部機能を無料で提供開始。"
        )
        assert result.is_relevant is True
        assert result.category == "pricing"
        assert result.confidence >= CONFIDENCE_THRESHOLD

    # --- Manual review flag tests ---

    def test_no_matching_patterns_flags_manual_review(self):
        """Article with no relevant/irrelevant patterns → relevant + manual review."""
        result = classify_press_article(
            "お知らせ",
            "弊社に関する重要なお知らせです。"
        )
        assert result.is_relevant is True
        assert result.needs_manual_review is True
        assert result.category == "other"

    def test_low_confidence_flags_manual_review(self):
        """Article with very few keyword matches → below threshold → manual review."""
        result = classify_press_article(
            "一般的なお知らせ",
            "本日ある調査を公開しました。"  # Only 1 keyword from market_data
        )
        # With only 1 match out of 9 alternatives, score = 1/9 ≈ 0.11 < 0.3 threshold
        assert result.is_relevant is True
        assert result.needs_manual_review is True
        assert result.category == "other"

    # --- Mixed pattern tests ---

    def test_irrelevant_with_relevant_patterns_stays_relevant(self):
        """Article with both irrelevant and relevant patterns → relevant wins if score is high."""
        result = classify_press_article(
            "新機能リリースとイベント開催のお知らせ",
            "新サービスの提供開始に伴い、機能追加のアップデートを行いました。リリース記念イベントも開催。"
        )
        # Has both irrelevant (イベント) and relevant (新機能, リリース, 新サービス, 提供開始, 機能追加, アップデート)
        assert result.is_relevant is True
        assert result.category == "service_feature"

    # --- Category assignment uniqueness ---

    def test_exactly_one_category_assigned(self):
        """Each relevant article gets exactly one category."""
        result = classify_press_article(
            "新サービスリリース",
            "新機能をリリースしました。"
        )
        assert result.is_relevant is True
        assert result.category in [
            "service_feature", "market_data", "ux_improvement", "pricing", "other"
        ]
