"use client";

import { useState, useEffect } from "react";
import { truncateTitle } from "@/lib/press-utils";

interface PressSource {
  id: string;
  name: string;
}

interface PressArticle {
  id: string;
  sourceId: string;
  title: string;
  articleUrl: string;
  publishedAt: string | null;
  classification: string | null;
  relevanceCategory: string | null;
  summary: string | null;
  source: {
    id: string;
    name: string;
  };
}

interface Pagination {
  page: number;
  totalPages: number;
  totalCount: number;
  pageSize: number;
}

const CLASSIFICATION_OPTIONS = [
  { value: "", label: "全て" },
  { value: "relevant", label: "関連" },
  { value: "irrelevant", label: "非関連" },
];

const CATEGORY_OPTIONS = [
  { value: "", label: "全て" },
  { value: "service_feature", label: "サービス機能" },
  { value: "market_data", label: "市場データ" },
  { value: "ux_improvement", label: "UX改善" },
  { value: "pricing", label: "料金" },
  { value: "other", label: "その他" },
];

function ClassificationBadge({ classification }: { classification: string | null }) {
  if (!classification) return null;

  const styles: Record<string, string> = {
    relevant: "bg-green-100 text-green-800",
    irrelevant: "bg-gray-100 text-gray-600",
  };

  const labels: Record<string, string> = {
    relevant: "関連",
    irrelevant: "非関連",
  };

  return (
    <span className={`px-2 py-0.5 text-xs rounded-full ${styles[classification] || "bg-gray-100 text-gray-600"}`}>
      {labels[classification] || classification}
    </span>
  );
}

function CategoryBadge({ category }: { category: string | null }) {
  if (!category) return null;

  const styles: Record<string, string> = {
    service_feature: "bg-blue-100 text-blue-800",
    market_data: "bg-purple-100 text-purple-800",
    ux_improvement: "bg-orange-100 text-orange-800",
    pricing: "bg-red-100 text-red-800",
    other: "bg-gray-100 text-gray-600",
  };

  const labels: Record<string, string> = {
    service_feature: "サービス機能",
    market_data: "市場データ",
    ux_improvement: "UX改善",
    pricing: "料金",
    other: "その他",
  };

  return (
    <span className={`px-2 py-0.5 text-xs rounded-full ${styles[category] || "bg-gray-100 text-gray-600"}`}>
      {labels[category] || category}
    </span>
  );
}

export default function PressArticlesPage() {
  const [articles, setArticles] = useState<PressArticle[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    totalPages: 0,
    totalCount: 0,
    pageSize: 20,
  });
  const [sources, setSources] = useState<PressSource[]>([]);
  const [loading, setLoading] = useState(true);

  // Filter state
  const [sourceId, setSourceId] = useState("");
  const [classification, setClassification] = useState("");
  const [relevanceCategory, setRelevanceCategory] = useState("");
  const [page, setPage] = useState(1);

  // Fetch sources for filter dropdown
  useEffect(() => {
    async function fetchSources() {
      try {
        const res = await fetch("/api/press-sources");
        if (res.ok) {
          const data = await res.json();
          setSources(data.sources || []);
        }
      } catch (error) {
        console.error("Failed to fetch sources:", error);
      }
    }
    fetchSources();
  }, []);

  // Fetch articles on filter/page change
  useEffect(() => {
    async function fetchArticles() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (sourceId) params.set("sourceId", sourceId);
        if (classification) params.set("classification", classification);
        if (relevanceCategory) params.set("relevanceCategory", relevanceCategory);
        params.set("page", String(page));

        const res = await fetch(`/api/press-articles?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          setArticles(data.articles || []);
          setPagination(data.pagination || { page: 1, totalPages: 0, totalCount: 0, pageSize: 20 });
        }
      } catch (error) {
        console.error("Failed to fetch articles:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchArticles();
  }, [sourceId, classification, relevanceCategory, page]);

  function handleFilterChange(setter: (val: string) => void) {
    return (e: React.ChangeEvent<HTMLSelectElement>) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  }

  return (
    <>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">プレスリリース記事履歴</h1>
        <span className="text-sm text-gray-500">{pagination.totalCount}件</span>
      </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex items-center gap-2">
            <label htmlFor="source-filter" className="text-sm text-gray-600">
              ソース:
            </label>
            <select
              id="source-filter"
              value={sourceId}
              onChange={handleFilterChange(setSourceId)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">全て</option>
              {sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="classification-filter" className="text-sm text-gray-600">
              分類:
            </label>
            <select
              id="classification-filter"
              value={classification}
              onChange={handleFilterChange(setClassification)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CLASSIFICATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="category-filter" className="text-sm text-gray-600">
              カテゴリ:
            </label>
            <select
              id="category-filter"
              value={relevanceCategory}
              onChange={handleFilterChange(setRelevanceCategory)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="text-center py-12 text-gray-500">読み込み中...</div>
        ) : articles.length === 0 ? (
          <div className="text-center py-12 text-gray-500">記事が見つかりません</div>
        ) : (
          <>
            {/* Article list */}
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">タイトル</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">ソース</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">日付</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">分類</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">カテゴリ</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">要約</th>
                  </tr>
                </thead>
                <tbody>
                  {articles.map((article) => (
                    <tr key={article.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <a
                          href={article.articleUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                          title={article.title}
                        >
                          {truncateTitle(article.title)}
                        </a>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-700">
                        {article.source.name}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-500 whitespace-nowrap">
                        {formatDate(article.publishedAt)}
                      </td>
                      <td className="py-3 px-4">
                        <ClassificationBadge classification={article.classification} />
                      </td>
                      <td className="py-3 px-4">
                        <CategoryBadge category={article.relevanceCategory} />
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600 max-w-xs truncate">
                        {article.summary || "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pagination.totalPages > 1 && (
              <div className="flex justify-center items-center gap-4 mt-6">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  &lt; 前へ
                </button>
                <span className="text-sm text-gray-600">
                  ページ {pagination.page} / {pagination.totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(pagination.totalPages, p + 1))}
                  disabled={page >= pagination.totalPages}
                  className="px-3 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  次へ &gt;
                </button>
              </div>
            )}
          </>
        )}
    </>
  );
}
