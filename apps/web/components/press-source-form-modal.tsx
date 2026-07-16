"use client";

import { useState, useEffect } from "react";
import { validatePressSourceInput } from "@/lib/press-validations";

interface PressSource {
  id: string;
  name: string;
  url: string;
  isActive: boolean;
}

interface PressSourceFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  source?: PressSource | null;
}

export function PressSourceFormModal({ isOpen, onClose, onSuccess, source }: PressSourceFormModalProps) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState("");

  const isEditing = !!source;

  useEffect(() => {
    if (source) {
      setName(source.name);
      setUrl(source.url);
    } else {
      setName("");
      setUrl("");
    }
    setErrors({});
    setApiError("");
  }, [source, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError("");

    const data = { name, url };
    const validation = validatePressSourceInput(data);
    if (!validation.valid) {
      setErrors(validation.errors);
      return;
    }

    setIsSubmitting(true);
    try {
      const endpoint = isEditing ? `/api/press-sources/${source.id}` : "/api/press-sources";
      const method = isEditing ? "PUT" : "POST";

      const res = await fetch(endpoint, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, url }),
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
          {isEditing ? "プレスソース編集" : "プレスソース新規登録"}
        </h3>

        {apiError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ソース名</label>
            <input
              type="text"
              value={name}
              onChange={(e) => { setName(e.target.value); clearFieldError("name"); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="suumo-press"
            />
            <p className="mt-1 text-xs text-gray-500">英数字とハイフンのみ（1〜50文字）</p>
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
            <input
              type="text"
              value={url}
              onChange={(e) => { setUrl(e.target.value); clearFieldError("url"); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="https://www.suumo.jp/press/"
            />
            {errors.url && <p className="mt-1 text-xs text-red-600">{errors.url}</p>}
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50"
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
