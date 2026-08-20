"use client";

import { useState } from "react";
import { ScreenshotImage } from "./screenshot-image";
import { ScreenshotModal } from "./screenshot-modal";
import { DiffViewer } from "./diff-viewer";

// カテゴリ英語 → 日本語
const CATEGORY_LABELS: Record<string, string> = {
  CRO: "コンバージョン改善",
  AD_PRODUCT: "広告・プロモーション",
  SEO: "SEO",
  AI: "AI機能",
  OTHER: "その他",
};

// MCP経由プレースホルダー判定
const MCP_PLACEHOLDER_PATTERN = /MCP経由/;
function isMcpPlaceholder(text: string | null | undefined): boolean {
  return !text || MCP_PLACEHOLDER_PATTERN.test(text);
}

// URL短縮：ドメイン + パスの先頭40文字
function shortenUrl(url: string): string {
  try {
    const { hostname, pathname, search } = new URL(url);
    const path = pathname + search;
    const truncated = path.length > 40 ? path.slice(0, 40) + "…" : path;
    return hostname + truncated;
  } catch {
    return url.length > 60 ? url.slice(0, 60) + "…" : url;
  }
}

interface ChangeCardProps {
  change: {
    id: string;
    serviceName: string;
    pageType: string;
    category: string | null;
    summary: string | null;
    diffText: string | null;
    beforeScreenshotPath: string | null;
    afterScreenshotPath: string | null;
    visualDiffPath: string | null;
    detectedAt: string;
    isReviewed: boolean;
    page: {
      url: string;
      device: string;
      service: {
        displayName: string;
      };
    };
    advice: {
      summary: string | null;
      intent: string | null;
      proposal: string | null;
      priority: string | null;
    } | null;
  };
}

export function ChangeCard({ change }: ChangeCardProps) {
  const [modalOpen, setModalOpen] = useState(false);

  const hasScreenshots = change.beforeScreenshotPath || change.afterScreenshotPath || change.visualDiffPath;
  const hasBeforeAfter = change.beforeScreenshotPath && change.afterScreenshotPath;

  // AI分析テキストがMCPプレースホルダーでなければ表示
  const aiSummary = !isMcpPlaceholder(change.advice?.summary) ? change.advice?.summary : null;
  const aiIntent = !isMcpPlaceholder(change.advice?.intent) ? change.advice?.intent : null;
  const aiProposal = !isMcpPlaceholder(change.advice?.proposal) ? change.advice?.proposal : null;
  const hasRealAdvice = aiSummary || aiIntent || aiProposal;

  const categoryLabel = change.category ? (CATEGORY_LABELS[change.category] ?? change.category) : null;

  // スクリーンショット表示列数の計算
  const screenshotCols =
    change.visualDiffPath && hasBeforeAfter ? 3
    : change.visualDiffPath || hasBeforeAfter ? 2
    : change.beforeScreenshotPath || change.afterScreenshotPath ? 1
    : 0;

  return (
    <>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="px-5 pt-4 pb-3">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">
                {change.page.service.displayName}
              </span>
              <span className="text-sm text-gray-500">
                {change.pageType === "list" ? "物件一覧" : "物件詳細"}
              </span>
              <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                {change.page.device === "sp" ? "SP" : "PC"}
              </span>
              {!change.isReviewed && (
                <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-green-100 text-green-700">
                  NEW
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {categoryLabel && (
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  {categoryLabel}
                </span>
              )}
              {change.advice?.priority && (
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                  change.advice.priority === "high" ? "bg-red-50 text-red-700 border border-red-200" :
                  change.advice.priority === "medium" ? "bg-orange-50 text-orange-700 border border-orange-200" :
                  "bg-gray-50 text-gray-600 border border-gray-200"
                }`}>
                  {change.advice.priority === "high" ? "🔴 高" :
                   change.advice.priority === "medium" ? "🟡 中" : "⚪ 低"}
                </span>
              )}
              <span className="text-xs text-gray-400">
                {new Date(change.detectedAt).toLocaleDateString("ja-JP")}
              </span>
            </div>
          </div>

          {/* URL（短縮表示） */}
          <a
            href={change.page.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:underline"
            title={change.page.url}
          >
            {shortenUrl(change.page.url)}
          </a>
        </div>

        {/* Summary - MAIN display (always shown prominently) */}
        {change.summary && (
          <div className="px-5 pb-3">
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
              <p className="text-xs font-medium text-gray-500 mb-1.5">📋 検知された変更内容</p>
              <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-line">{change.summary}</p>
            </div>
          </div>
        )}

        {/* AI Advice - summary & intent（MCPプレースホルダーは非表示） */}
        {hasRealAdvice && (
          <div className="mx-5 mb-3 p-3 bg-indigo-50 rounded-lg border border-indigo-200">
            <p className="text-xs font-medium text-indigo-700 mb-1">🤖 AI分析</p>
            {aiSummary && (
              <p className="text-sm text-indigo-900 leading-relaxed">{aiSummary}</p>
            )}
            {aiIntent && (
              <p className="text-xs text-indigo-600 mt-1.5">
                <span className="font-medium">競合の狙い:</span> {aiIntent}
              </p>
            )}
          </div>
        )}

        {/* HOME'Sへの提案（MCPプレースホルダーは非表示） */}
        {aiProposal && (
          <div className="mx-5 mb-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
            <p className="text-xs font-medium text-amber-700 mb-1">💡 HOME&apos;Sへの提案</p>
            <p className="text-sm text-amber-900 leading-relaxed">{aiProposal}</p>
          </div>
        )}

        {/* ── スクリーンショット比較エリア（常時表示・クリック不要） ── */}
        {screenshotCols > 0 && (
          <div className="px-5 pb-3">
            <p className="text-xs font-medium text-gray-500 mb-2">
              📸 変更箇所の比較
              {hasScreenshots && (
                <button
                  onClick={() => setModalOpen(true)}
                  className="ml-2 text-blue-500 hover:text-blue-700 hover:underline"
                >
                  拡大表示 →
                </button>
              )}
            </p>
            <div className={`grid gap-2 ${
              screenshotCols === 3 ? "grid-cols-3" :
              screenshotCols === 2 ? "grid-cols-2" :
              "grid-cols-1"
            }`}>
              {/* Before */}
              {change.beforeScreenshotPath && (
                <div className="overflow-hidden rounded-lg border border-gray-200">
                  <ScreenshotImage
                    src={change.beforeScreenshotPath}
                    alt="Before"
                    label="Before"
                    height="h-52"
                    objectFit="object-contain"
                  />
                </div>
              )}
              {/* After */}
              {change.afterScreenshotPath && (
                <div className="overflow-hidden rounded-lg border border-gray-200">
                  <ScreenshotImage
                    src={change.afterScreenshotPath}
                    alt="After"
                    label="After"
                    height="h-52"
                    objectFit="object-contain"
                  />
                </div>
              )}
              {/* 差分ハイライト（赤枠付き） */}
              {change.visualDiffPath && (
                <div className="overflow-hidden rounded-lg border border-red-200">
                  <ScreenshotImage
                    src={change.visualDiffPath}
                    alt="変更箇所ハイライト"
                    label="変更箇所"
                    height="h-52"
                    objectFit="object-contain"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── DOM差分（開発者向け・最下部） ── */}
        {change.diffText && (
          <div className="px-5 pb-4 border-t border-gray-100 pt-3 mt-1">
            <details className="group">
              <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-500 transition-colors select-none">
                <span className="group-open:hidden">▶ DOM差分を表示（開発者向け）</span>
                <span className="hidden group-open:inline">▼ DOM差分を閉じる</span>
              </summary>
              <div className="mt-2">
                <DiffViewer diffText={change.diffText} />
              </div>
            </details>
          </div>
        )}
      </div>

      {/* Modal for detailed comparison */}
      {hasScreenshots && (
        <ScreenshotModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          beforeSrc={change.beforeScreenshotPath}
          afterSrc={change.afterScreenshotPath}
          diffSrc={change.visualDiffPath}
          serviceName={`${change.page.service.displayName} - ${change.pageType === "list" ? "物件一覧" : "物件詳細"}`}
          detectedAt={new Date(change.detectedAt).toLocaleDateString("ja-JP")}
        />
      )}
    </>
  );
}
