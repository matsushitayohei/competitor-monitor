"use client";

import { useState, useEffect } from "react";
import { validateServiceInput } from "@/lib/validations";

interface Service {
  id: string;
  name: string;
  displayName: string;
  baseUrl: string;
  isActive: boolean;
}

interface ServiceFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  service?: Service | null;
}

export function ServiceFormModal({ isOpen, onClose, onSuccess, service }: ServiceFormModalProps) {
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState("");

  const isEditing = !!service;

  useEffect(() => {
    if (service) {
      setName(service.name);
      setDisplayName(service.displayName);
      setBaseUrl(service.baseUrl);
      setIsActive(service.isActive);
    } else {
      setName("");
      setDisplayName("");
      setBaseUrl("");
      setIsActive(true);
    }
    setErrors({});
    setApiError("");
  }, [service, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError("");

    const data = { name, displayName, baseUrl };
    const validation = validateServiceInput(data);
    if (!validation.valid) {
      setErrors(validation.fields);
      return;
    }

    setIsSubmitting(true);
    try {
      const url = isEditing ? `/api/services/${service.id}` : "/api/services";
      const method = isEditing ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, displayName, baseUrl, isActive }),
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
          {isEditing ? "サービス編集" : "サービス追加"}
        </h3>

        {apiError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">サービス名</label>
            <input
              type="text"
              value={name}
              onChange={(e) => { setName(e.target.value); clearFieldError("name"); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="suumo"
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">表示名</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => { setDisplayName(e.target.value); clearFieldError("displayName"); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="SUUMO"
            />
            {errors.displayName && <p className="mt-1 text-xs text-red-600">{errors.displayName}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => { setBaseUrl(e.target.value); clearFieldError("baseUrl"); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="https://suumo.jp"
            />
            {errors.baseUrl && <p className="mt-1 text-xs text-red-600">{errors.baseUrl}</p>}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="isActive"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="isActive" className="text-sm text-gray-700">有効</label>
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
