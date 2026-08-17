import { prisma } from "@/lib/prisma";
import { Sidebar } from "@/components/sidebar";
import { ChangeCard } from "@/components/change-card";
import Link from "next/link";

export const dynamic = 'force-dynamic';

interface SearchParams {
  service?: string;
  category?: string;
  reviewed?: string;
  page?: string;
}

const PAGE_SIZE = 20;

export default async function ChangesPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const currentPage = Math.max(1, parseInt(searchParams.page || "1"));
  const serviceFilter = searchParams.service || "";
  const categoryFilter = searchParams.category || "";
  const reviewedFilter = searchParams.reviewed || "";

  const where = {
    ...(serviceFilter && { serviceName: serviceFilter }),
    ...(categoryFilter && { category: categoryFilter }),
    ...(reviewedFilter === "true" && { isReviewed: true }),
    ...(reviewedFilter === "false" && { isReviewed: false }),
  };

  const [changes, totalCount, services] = await Promise.all([
    prisma.change.findMany({
      where,
      orderBy: { detectedAt: "desc" },
      skip: (currentPage - 1) * PAGE_SIZE,
      take: PAGE_SIZE,
      include: {
        page: { include: { service: true } },
        advice: true,
      },
    }),
    prisma.change.count({ where }),
    prisma.service.findMany({
      where: { deletedAt: null },
      select: { name: true, displayName: true },
    }),
  ]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  function buildUrl(params: Record<string, string>) {
    const p = new URLSearchParams();
    if (params.service || serviceFilter) p.set("service", params.service ?? serviceFilter);
    if (params.category || categoryFilter) p.set("category", params.category ?? categoryFilter);
    if (params.reviewed || reviewedFilter) p.set("reviewed", params.reviewed ?? reviewedFilter);
    if (params.page) p.set("page", params.page);
    // Remove empty params
    for (const [k, v] of p.entries()) { if (!v) p.delete(k); }
    const qs = p.toString();
    return `/changes${qs ? `?${qs}` : ""}`;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">変更履歴</h1>
          <span className="text-sm text-gray-500">{totalCount}件</span>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">サービス:</label>
            <div className="flex gap-1">
              <Link
                href={buildUrl({ service: "", page: "1" })}
                className={`px-2 py-1 text-xs rounded ${!serviceFilter ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
              >
                全て
              </Link>
              {services.map((s) => (
                <Link
                  key={s.name}
                  href={buildUrl({ service: s.name, page: "1" })}
                  className={`px-2 py-1 text-xs rounded ${serviceFilter === s.name ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                >
                  {s.displayName}
                </Link>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">カテゴリ:</label>
            <div className="flex gap-1">
              {["", "CRO", "AD_PRODUCT", "SEO", "AI", "OTHER"].map((cat) => (
                <Link
                  key={cat}
                  href={buildUrl({ category: cat, page: "1" })}
                  className={`px-2 py-1 text-xs rounded ${categoryFilter === cat ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                >
                  {cat || "全て"}
                </Link>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">既読:</label>
            <div className="flex gap-1">
              {[
                { value: "", label: "全て" },
                { value: "false", label: "未読" },
                { value: "true", label: "既読" },
              ].map((opt) => (
                <Link
                  key={opt.value}
                  href={buildUrl({ reviewed: opt.value, page: "1" })}
                  className={`px-2 py-1 text-xs rounded ${reviewedFilter === opt.value ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                >
                  {opt.label}
                </Link>
              ))}
            </div>
          </div>
        </div>

        {changes.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            条件に該当する変更はありません。
          </div>
        ) : (
          <div className="space-y-4">
            {changes.map((change) => (
              <ChangeCard
                key={change.id}
                change={{
                  ...change,
                  detectedAt: change.detectedAt.toISOString(),
                  page: {
                    ...change.page,
                    device: change.page.device,
                  },
                }}
              />
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-center items-center gap-2 mt-8">
            {currentPage > 1 && (
              <Link
                href={buildUrl({ page: String(currentPage - 1) })}
                className="px-3 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50"
              >
                ← 前
              </Link>
            )}
            <span className="text-sm text-gray-600">
              {currentPage} / {totalPages}
            </span>
            {currentPage < totalPages && (
              <Link
                href={buildUrl({ page: String(currentPage + 1) })}
                className="px-3 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50"
              >
                次 →
              </Link>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
