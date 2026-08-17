"use client";

import { useCallback, useEffect, useState } from "react";
import { ImageComparisonSlider } from "./image-comparison-slider";

interface ScreenshotModalProps {
  isOpen: boolean;
  onClose: () => void;
  beforeSrc?: string | null;
  afterSrc?: string | null;
  diffSrc?: string | null;
  serviceName: string;
  detectedAt: string;
}

type Tab = "slider" | "diff" | "before" | "after";

function getProxyUrl(originalUrl: string): string {
  return `/api/screenshots?url=${encodeURIComponent(originalUrl)}`;
}

function resolveUrl(src: string): string {
  return src.includes(".blob.vercel-storage.com/") ? getProxyUrl(src) : src;
}

export function ScreenshotModal({
  isOpen,
  onClose,
  beforeSrc,
  afterSrc,
  diffSrc,
  serviceName,
  detectedAt,
}: ScreenshotModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>("slider");

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  const tabs: { id: Tab; label: string; available: boolean }[] = [
    { id: "slider", label: "スライダー比較", available: !!beforeSrc && !!afterSrc },
    { id: "diff", label: "差分ハイライト", available: !!diffSrc },
    { id: "before", label: "Before", available: !!beforeSrc },
    { id: "after", label: "After", available: !!afterSrc },
  ];

  const availableTabs = tabs.filter((t) => t.available);

  // If active tab is not available, switch to first available
  const currentTab = availableTabs.find((t) => t.id === activeTab)
    ? activeTab
    : availableTabs[0]?.id || "slider";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-[95vw] max-w-6xl max-h-[95vh] bg-white rounded-xl shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              スクリーンショット比較
            </h2>
            <p className="text-sm text-gray-500">
              {serviceName} - {detectedAt}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="閉じる"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 4L16 16M16 4L4 16" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-6 py-3 border-b border-gray-100 bg-gray-50">
          {availableTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                currentTab === tab.id
                  ? "bg-white text-blue-700 shadow-sm border border-gray-200"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {currentTab === "slider" && beforeSrc && afterSrc && (
            <ImageComparisonSlider
              beforeSrc={beforeSrc}
              afterSrc={afterSrc}
            />
          )}

          {currentTab === "diff" && diffSrc && (
            <div className="flex justify-center">
              <img
                src={resolveUrl(diffSrc)}
                alt="差分ハイライト"
                className="max-w-full h-auto rounded-lg border border-gray-200"
              />
            </div>
          )}

          {currentTab === "before" && beforeSrc && (
            <div className="flex justify-center">
              <img
                src={resolveUrl(beforeSrc)}
                alt="Before"
                className="max-w-full h-auto rounded-lg border border-gray-200"
              />
            </div>
          )}

          {currentTab === "after" && afterSrc && (
            <div className="flex justify-center">
              <img
                src={resolveUrl(afterSrc)}
                alt="After"
                className="max-w-full h-auto rounded-lg border border-gray-200"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
