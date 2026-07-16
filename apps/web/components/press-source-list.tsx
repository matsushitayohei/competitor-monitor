"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/toast";
import { PressSourceFormModal } from "@/components/press-source-form-modal";

interface PressSource {
  id: string;
  name: string;
  url: string;
  isActive: boolean;
  createdAt: string;
}

interface PressSourceListProps {
  sources: PressSource[];
}

export function PressSourceList({ sources }: PressSourceListProps) {
  const router = useRouter();
  const { showToast } = useToast();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<PressSource | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const handleFormSuccess = () => {
    showToast(editingSource ? "ソースを更新しました" : "ソースを登録しました", "success");
    setEditingSource(null);
    router.refresh();
  };

  const handleToggleActive = async (source: PressSource) => {
    setTogglingId(source.id);
    try {
      const res = await fetch(`/api/press-sources/${source.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isActive: !source.isActive }),
      });

      if (!res.ok) {
        const data = await res.json();
        showToast(data.error || "更新に失敗しました", "error");
        return;
      }

      showToast(
        source.isActive ? "ソースを無効化しました" : "ソースを有効化しました",
        "success"
      );
      router.refresh();
    } catch {
      showToast("ネットワークエラーが発生しました", "error");
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">プレスリリースソース管理</h1>
        <button
          onClick={() => { setEditingSource(null); setIsFormOpen(true); }}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
        >
          新規登録
        </button>
      </div>

      {sources.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          ソースが登録されていません
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">名前</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">URL</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ステータス</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">アクション</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sources.map((source) => (
                <tr key={source.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">
                    {source.name}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 hover:underline truncate block max-w-xs"
                      title={source.url}
                    >
                      {source.url.length > 50 ? source.url.slice(0, 50) + "..." : source.url}
                    </a>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                      source.isActive
                        ? "bg-green-100 text-green-800"
                        : "bg-gray-100 text-gray-600"
                    }`}>
                      {source.isActive ? "有効" : "無効"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => { setEditingSource(source); setIsFormOpen(true); }}
                        className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
                      >
                        編集
                      </button>
                      <button
                        onClick={() => handleToggleActive(source)}
                        disabled={togglingId === source.id}
                        className={`px-3 py-1.5 text-xs font-medium rounded disabled:opacity-50 ${
                          source.isActive
                            ? "text-orange-700 bg-orange-50 hover:bg-orange-100"
                            : "text-green-700 bg-green-50 hover:bg-green-100"
                        }`}
                      >
                        {togglingId === source.id
                          ? "処理中..."
                          : source.isActive
                            ? "無効化"
                            : "有効化"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <PressSourceFormModal
        isOpen={isFormOpen}
        onClose={() => { setIsFormOpen(false); setEditingSource(null); }}
        onSuccess={handleFormSuccess}
        source={editingSource}
      />
    </div>
  );
}
