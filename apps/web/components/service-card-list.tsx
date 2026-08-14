"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/toast";
import { ServiceFormModal } from "@/components/service-form-modal";
import { DeleteConfirmDialog } from "@/components/delete-confirm-dialog";
import { ServicePagesSection } from "@/components/service-pages-section";
import { SERVICE_CATEGORIES } from "@/lib/validations";

interface MonitoredPage {
  id: string;
  url: string;
  pageType: string;
  device: string;
  isActive: boolean;
  lastScannedAt: string | null;
}

interface Service {
  id: string;
  name: string;
  displayName: string;
  baseUrl: string;
  category: string;
  isActive: boolean;
  pages: MonitoredPage[];
  _count: { pages: number };
}

interface ServiceCardListProps {
  services: Service[];
}

const CATEGORY_TABS = [
  { value: "all", label: "すべて" },
  ...SERVICE_CATEGORIES,
] as const;

export function ServiceCardList({ services }: ServiceCardListProps) {
  const router = useRouter();
  const { showToast } = useToast();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [deletingService, setDeletingService] = useState<Service | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [expandedServiceId, setExpandedServiceId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("all");

  const filteredServices = activeTab === "all"
    ? services
    : services.filter((s) => s.category === activeTab);

  const handleServiceSuccess = () => {
    showToast(editingService ? "サービスを更新しました" : "サービスを登録しました", "success");
    setEditingService(null);
    router.refresh();
  };

  const handleDeleteConfirm = async () => {
    if (!deletingService) return;
    setIsDeleting(true);
    try {
      const res = await fetch(`/api/services/${deletingService.id}`, { method: "DELETE" });
      if (!res.ok) {
        const data = await res.json();
        showToast(data.error || "削除に失敗しました", "error");
        return;
      }
      showToast("サービスを削除しました", "success");
      router.refresh();
    } catch {
      showToast("ネットワークエラーが発生しました", "error");
    } finally {
      setIsDeleting(false);
      setDeletingService(null);
    }
  };

  const toggleExpand = (serviceId: string) => {
    setExpandedServiceId((prev) => (prev === serviceId ? null : serviceId));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">対象サイト</h1>
        <button
          onClick={() => { setEditingService(null); setIsFormOpen(true); }}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
        >
          サービス追加
        </button>
      </div>

      {/* Category tabs */}
      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {CATEGORY_TABS.map((tab) => {
          const count = tab.value === "all"
            ? services.length
            : services.filter((s) => s.category === tab.value).length;
          return (
            <button
              key={tab.value}
              onClick={() => setActiveTab(tab.value)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.value
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab.label}
              <span className="ml-1.5 text-xs text-gray-400">({count})</span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredServices.map((service) => (
          <div key={service.id} className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h2
                className="text-lg font-semibold text-gray-900 cursor-pointer hover:text-blue-600"
                onClick={() => toggleExpand(service.id)}
              >
                {service.displayName}
              </h2>
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => { e.stopPropagation(); setEditingService(service); setIsFormOpen(true); }}
                  className="p-1.5 text-gray-400 hover:text-blue-600 rounded hover:bg-blue-50"
                  title="編集"
                >
                  ✏️
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setDeletingService(service); }}
                  className="p-1.5 text-gray-400 hover:text-red-600 rounded hover:bg-red-50"
                  title="削除"
                >
                  🗑️
                </button>
                <span className={`ml-2 px-2 py-1 text-xs rounded-full ${service.isActive ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}>
                  {service.isActive ? "有効" : "無効"}
                </span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mb-2">{service.baseUrl}</p>
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 text-xs rounded-full ${
                service.category === "real_estate"
                  ? "bg-indigo-100 text-indigo-700"
                  : "bg-amber-100 text-amber-700"
              }`}>
                {SERVICE_CATEGORIES.find((c) => c.value === service.category)?.label || "不動産"}
              </span>
            </div>
            <p
              className="text-sm text-gray-600 cursor-pointer hover:text-blue-600"
              onClick={() => toggleExpand(service.id)}
            >
              {new Set((service.pages || []).map((p) => `${p.url}::${p.pageType}`)).size} ページ監視中
            </p>

            {expandedServiceId === service.id && (
              <ServicePagesSection
                serviceId={service.id}
                pages={service.pages}
                onRefresh={() => router.refresh()}
              />
            )}
          </div>
        ))}
      </div>

      {filteredServices.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          {activeTab === "all"
            ? "監視対象のサービスがまだ登録されていません。"
            : `このカテゴリのサービスはまだ登録されていません。`}
        </div>
      )}

      <ServiceFormModal
        isOpen={isFormOpen}
        onClose={() => { setIsFormOpen(false); setEditingService(null); }}
        onSuccess={handleServiceSuccess}
        service={editingService}
      />

      <DeleteConfirmDialog
        isOpen={!!deletingService}
        onClose={() => setDeletingService(null)}
        onConfirm={handleDeleteConfirm}
        title="サービスの削除"
        message={`「${deletingService?.displayName}」を削除しますか？関連する全ての監視ページも削除されます。`}
        isLoading={isDeleting}
      />
    </div>
  );
}
