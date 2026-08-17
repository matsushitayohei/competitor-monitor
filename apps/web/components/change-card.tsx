"use client";

import { useState } from "react";
import { ScreenshotImage } from "./screenshot-image";
import { ScreenshotModal } from "./screenshot-modal";

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
              {change.category && (
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  {change.category}
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

          {/* URL */}
          <a
            href={change.page.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:underline break-all line-clamp-1"
          >
            {change.page.url}
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

        {/* AI Advice - inline summary */}
        {change.advice?.proposal && (
          <div className="mx-5 mb-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
            <p className="text-xs font-medium text-amber-700 mb-1">💡 HOME&apos;Sへの提案</p>
            <p className="text-sm text-amber-900 leading-relaxed">{change.advice.proposal}</p>
          </div>
        )}

        {/* Visual Diff - shown only when clear structural changes were detected */}
        {change.visualDiffPath && (
          <div className="px-5 pb-3">
            <button
              onClick={() => setModalOpen(true)}
              className="w-full text-left group"
            >
              <p className="text-xs font-medium text-gray-500 mb-1.5">
                🔍 構造変更箇所
                <span className="ml-2 text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">
                  クリックして拡大比較 →
                </span>
              </p>
              <div className="relative overflow-hidden rounded-lg border border-gray-200 group-hover:border-blue-300 transition-colors">
                <ScreenshotImage
                  src={change.visualDiffPath}
                  alt="変更箇所ハイライト"
                  label=""
                  height="h-72"
                  objectFit="object-contain"
                />
                <div className="absolute inset-0 bg-blue-500/0 group-hover:bg-blue-500/5 transition-colors flex items-center justify-center">
                  <span className="opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 px-3 py-1.5 rounded-full text-sm text-blue-700 shadow">
                    拡大して比較する
                  </span>
                </div>
              </div>
            </button>
          </div>
        )}

        {/* Before/After comparison - always available when screenshots exist */}
        {!change.visualDiffPath && (change.beforeScreenshotPath || change.afterScreenshotPath) && (
          <div className="px-5 pb-3">
            <button
              onClick={() => setModalOpen(true)}
              className="w-full text-left group"
            >
              <p className="text-xs font-medium text-gray-500 mb-1.5">
                📸 Before / After
                <span className="ml-2 text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">
                  クリックしてスライダー比較 →
                </span>
              </p>
              <div className="grid grid-cols-2 gap-2">
                {change.beforeScreenshotPath && (
                  <div className="relative overflow-hidden rounded-lg border border-gray-200 group-hover:border-blue-300 transition-colors">
                    <ScreenshotImage
                      src={change.beforeScreenshotPath}
                      alt="Before"
                      label="Before"
                      height="h-48"
                      objectFit="object-contain"
                    />
                  </div>
                )}
                {change.afterScreenshotPath && (
                  <div className="relative overflow-hidden rounded-lg border border-gray-200 group-hover:border-blue-300 transition-colors">
                    <ScreenshotImage
                      src={change.afterScreenshotPath}
                      alt="After"
                      label="After"
                      height="h-48"
                      objectFit="object-contain"
                    />
                  </div>
                )}
              </div>
            </button>
          </div>
        )}

        {/* When visual diff exists but Before/After also available, show small link */}
        {change.visualDiffPath && (change.beforeScreenshotPath && change.afterScreenshotPath) && (
          <div className="px-5 pb-2">
            <button
              onClick={() => setModalOpen(true)}
              className="text-xs text-blue-500 hover:text-blue-700 hover:underline"
            >
              📸 Before/After スライダーで比較する
            </button>
          </div>
        )}

        {/* DOM diff - collapsed */}
        {change.diffText && (
          <div className="px-5 pb-4">
            <details className="group">
              <summary className="text-xs font-medium text-gray-400 cursor-pointer hover:text-gray-600 transition-colors">
                <span className="group-open:hidden">▶ DOM差分を表示</span>
                <span className="hidden group-open:inline">▼ DOM差分を閉じる</span>
              </summary>
              <pre className="mt-2 p-3 bg-gray-900 text-gray-100 text-xs rounded-lg overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap break-all">
                {change.diffText.split("\n").map((line, i) => (
                  <span
                    key={i}
                    className={
                      line.startsWith("+") && !line.startsWith("+++")
                        ? "text-green-400"
                        : line.startsWith("-") && !line.startsWith("---")
                        ? "text-red-400"
                        : line.startsWith("@@")
                        ? "text-cyan-400"
                        : ""
                    }
                  >
                    {line}{"\n"}
                  </span>
                ))}
              </pre>
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
