"use client";

import { useState } from "react";
import { useToast } from "@/components/toast";
import { PageFormModal } from "@/components/page-form-modal";
import { DeleteConfirmDialog } from "@/components/delete-confirm-dialog";
import { formatInTimeZone } from "date-fns-tz";

interface MonitoredPage {
  id: string;
  url: string;
  pageType: string;
  device: string;
  isActive: boolean;
  lastScannedAt: string | null;
}

interface ServicePagesSectionProps {
  serviceId: string;
  pages: MonitoredPage[];
  onRefresh: () => void;
}

export function ServicePagesSection({ serviceId, pages, onRefresh }: ServicePagesSectionProps) {
  const { showToast } = useToast();
  const [isPageFormOpen, setIsPageFormOpen] = useState(false);
  const [editingPage, setEditingPage] = useState<MonitoredPage | null>(null);
  const [deletingPage, setDeletingPage] = useState<MonitoredPage | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteConfirm = async () => {
    if (!deletingPage) return;
    setIsDeleting(true);
    try {
      const res = await fetch(`/api/pages/${deletingPage.id}`, { method: "DELETE" });
      if (!res.ok) {
        const data = await res.json();
        showToast(data.error || "削除に失敗しました", "error");
        return;
      }
      showToast("ページを削除しました", "success");
      onRefresh();
    } catch {
      showToast("ネットワークエラーが発生しました", "error");
    } finally {
      setIsDeleting(false);
      setDeletingPage(null);
    }
  };

  const handlePageSuccess = () => {
    showToast(editingPage ? "ページを更新しました" : "ページを登録しました", "success");
    setEditingPage(null);
    onRefresh();
  };

  const formatPageType = (type: string) => {
    switch (type) {
      case "listing": return "物件一覧";
      case "detail": return "物件詳細";
      case "search": return "条件設定";
      default: return type;
    }
  };
  const formatDevice = (device: string) => device === "pc" ? "PC" : "SP";
  const formatDate = (date: string | null) => {
    if (!date) return "未スキャン";
    return formatInTimeZone(new Date(date), "Asia/Tokyo", "yyyy/MM/dd HH:mm");
  };

  return (
    <div className="mt-4 border-t border-gray-100 pt-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">監視ページ</h4>
        <button
          onClick={() => { setEditingPage(null); setIsPageFormOpen(true); }}
          className="text-xs px-3 py-1 bg-blue-50 text-blue-700 rounded hover:bg-blue-100"
        >
          ページ追加
        </button>
      </div>

      {pages.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-4">監視対象のページがありません</p>
      ) : (
        <div className="space-y-2">
          {pages.map((page) => (
            <div key={page.id} className="flex items-center justify-between p-3 bg-gray-50 rounded text-sm">
              <div className="flex-1 min-w-0">
                <p className="text-gray-900 truncate">{page.url}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="px-2 py-0.5 bg-gray-200 text-gray-700 text-xs rounded">{formatPageType(page.pageType)}</span>
                  <span className="px-2 py-0.5 bg-gray-200 text-gray-700 text-xs rounded">{formatDevice(page.device)}</span>
                  <span className={`px-2 py-0.5 text-xs rounded ${page.isActive ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-500"}`}>
                    {page.isActive ? "有効" : "無効"}
                  </span>
                  <span className="text-xs text-gray-400">{formatDate(page.lastScannedAt)}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 ml-2">
                <button
                  onClick={() => { setEditingPage(page); setIsPageFormOpen(true); }}
                  className="p-1.5 text-gray-400 hover:text-blue-600 rounded hover:bg-blue-50"
                  title="編集"
                >
                  ✏️
                </button>
                <button
                  onClick={() => setDeletingPage(page)}
                  className="p-1.5 text-gray-400 hover:text-red-600 rounded hover:bg-red-50"
                  title="削除"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <PageFormModal
        isOpen={isPageFormOpen}
        onClose={() => { setIsPageFormOpen(false); setEditingPage(null); }}
        onSuccess={handlePageSuccess}
        serviceId={serviceId}
        page={editingPage}
      />

      <DeleteConfirmDialog
        isOpen={!!deletingPage}
        onClose={() => setDeletingPage(null)}
        onConfirm={handleDeleteConfirm}
        title="ページの削除"
        message={`「${deletingPage?.url}」を削除しますか？この操作は取り消せません。`}
        isLoading={isDeleting}
      />
    </div>
  );
}
