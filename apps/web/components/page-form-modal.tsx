"use client";

import { useState, useEffect } from "react";
import { validatePageInput } from "@/lib/validations";

interface MonitoredPage {
  id: string;
  url: string;
  pageType: string;
  device: string;
  isActive: boolean;
}

interface PageFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  serviceId: string;
  page?: MonitoredPage | null;
}

export function PageFormModal({ isOpen, onClose, onSuccess, serviceId, page }: PageFormModalProps) {
  const [url, setUrl] = useState("");
  const [pageType, setPageType] = useState("listing");
  const [device, setDevice] = useState("pc");
  const [isActive, setIsActive] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState("");

  const isEditing = !!page;

  useEffect(() => {
    if (page) {
      setUrl(page.url);
      setPageType(page.pageType);
      setDevice(page.device);
      setIsActive(page.isActive);
    } else {
      setUrl("");
      setPageType("listing");
      setDevice("pc");
      setIsActive(true);
    }
    setErrors({});
    setApiError("");
  }, [page, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError("");

    const data = { url, pageType, device };
    const validation = validatePageInput(data);
    if (!validation.valid) {
      setErrors(validation.fields);
      return;
    }

    setIsSubmitting(true);
    try {
      const apiUrl = isEditing
        ? `/api/pages/${page.id}`
        : `/api/services/${serviceId}/pages`;
      const method = isEditing ? "PUT" : "POST";

      const res = await fetch(apiUrl, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, pageType, device, isActive }),
      });

      if (!res.ok) {
        const result = await res.json();
        if (result.fields) {
          setErrors(result.fields);
        }
        setApiError(result.error || "エラーが発生しました");
        return;
      }

      onSuccess();
      onClose();
    } catch {
      setApiError("ネットワークエラーが発生しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  const clearFieldError = (field: string) => {
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-lg p-6 w-full max-w-md shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          {isEditing ? "ページ編集" : "ページ追加"}
        </h3>

        {apiError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
            <input
              type="text"
              value={url}
              onChange={(e) => { setUrl(e.target.value); clearFieldError("url"); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="https://suumo.jp/chintai/tokyo/"
            />
            {errors.url && <p className="mt-1 text-xs text-red-600">{errors.url}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ページ種別</label>
            <select
              value={pageType}
              onChange={(e) => { setPageType(e.target.value); clearFieldError("pageType"); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="listing">物件一覧</option>
              <option value="detail">物件詳細</option>
            </select>
            {errors.pageType && <p className="mt-1 text-xs text-red-600">{errors.pageType}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">デバイス</label>
            <select
              value={device}
              onChange={(e) => { setDevice(e.target.value); clearFieldError("device"); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="pc">PC (1280px)</option>
              <option value="sp">SP (375px)</option>
            </select>
            {errors.device && <p className="mt-1 text-xs text-red-600">{errors.device}</p>}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="pageIsActive"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="pageIsActive" className="text-sm text-gray-700">有効</label>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? "処理中..." : isEditing ? "更新" : "登録"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
