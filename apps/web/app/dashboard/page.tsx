import { prisma } from "@/lib/prisma";

export const dynamic = 'force-dynamic';

export default async function DashboardPage() {
  const totalChanges = await prisma.change.count();
  const recentChanges = await prisma.change.findMany({
    orderBy: { detectedAt: "desc" },
    take: 10,
    include: { page: { include: { service: true } } },
  });
  const services = await prisma.service.findMany({
    where: { isActive: true, deletedAt: null },
    select: { id: true, category: true },
  });
  const pages = await prisma.monitoredPage.count({ where: { isActive: true, deletedAt: null } });

  const realEstateCount = services.filter((s) => s.category === "real_estate").length;
  const otherCount = services.filter((s) => s.category === "other").length;

  // Group recent changes by category
  const realEstateChanges = recentChanges.filter(
    (c) => c.page.service.category === "real_estate"
  );
  const otherChanges = recentChanges.filter(
    (c) => c.page.service.category !== "real_estate"
  );

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">ダッシュボード</h1>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">監視サービス数</p>
          <p className="text-3xl font-bold text-gray-900">{services.length}</p>
          <div className="mt-2 flex gap-3 text-xs text-gray-500">
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
              不動産 {realEstateCount}
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              他業種 {otherCount}
            </span>
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">監視ページ数</p>
          <p className="text-3xl font-bold text-gray-900">{pages}</p>
        </div>
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">検知済み変更</p>
          <p className="text-3xl font-bold text-gray-900">{totalChanges}</p>
        </div>
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">直近の変更</p>
          <div className="mt-1 flex gap-3 text-sm">
            <span className="inline-flex items-center gap-1 text-indigo-700">
              <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
              不動産 {realEstateChanges.length}
            </span>
            <span className="inline-flex items-center gap-1 text-amber-700">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              他業種 {otherChanges.length}
            </span>
          </div>
        </div>
      </div>

      {/* Recent changes - Real Estate */}
      <div className="bg-white rounded-lg border border-gray-200 mb-6">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-400"></span>
          <h2 className="text-lg font-semibold text-gray-900">不動産 - 直近の変更</h2>
        </div>
        {realEstateChanges.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">
            不動産カテゴリの変更はまだ検知されていません。
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {realEstateChanges.map((change) => (
              <li key={change.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {change.page.service.displayName} - {change.pageType === "list" ? "一覧" : "詳細"}
                  </p>
                  <p className="text-sm text-gray-500">{change.summary || "分析中..."}</p>
                </div>
                <div className="flex items-center gap-2">
                  {change.category && (
                    <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                      {change.category}
                    </span>
                  )}
                  <span className="text-xs text-gray-400">
                    {change.detectedAt.toLocaleDateString("ja-JP")}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Recent changes - Other */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
          <h2 className="text-lg font-semibold text-gray-900">他業種 - 直近の変更</h2>
        </div>
        {otherChanges.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">
            他業種カテゴリの変更はまだ検知されていません。
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {otherChanges.map((change) => (
              <li key={change.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {change.page.service.displayName} - {change.pageType === "list" ? "一覧" : "詳細"}
                  </p>
                  <p className="text-sm text-gray-500">{change.summary || "分析中..."}</p>
                </div>
                <div className="flex items-center gap-2">
                  {change.category && (
                    <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                      {change.category}
                    </span>
                  )}
                  <span className="text-xs text-gray-400">
                    {change.detectedAt.toLocaleDateString("ja-JP")}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
