import { prisma } from "@/lib/prisma";

export const dynamic = 'force-dynamic';

export default async function DashboardPage() {
  const totalChanges = await prisma.change.count();
  const recentChanges = await prisma.change.findMany({
    orderBy: { detectedAt: "desc" },
    take: 5,
    include: { page: { include: { service: true } } },
  });
  const services = await prisma.service.count({ where: { isActive: true } });
  const pages = await prisma.monitoredPage.count({ where: { isActive: true } });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">ダッシュボード</h1>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">監視サービス数</p>
          <p className="text-3xl font-bold text-gray-900">{services}</p>
        </div>
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">監視ページ数</p>
          <p className="text-3xl font-bold text-gray-900">{pages}</p>
        </div>
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">検知済み変更</p>
          <p className="text-3xl font-bold text-gray-900">{totalChanges}</p>
        </div>
      </div>

      {/* Recent changes */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">直近の変更</h2>
        </div>
        {recentChanges.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            まだ変更が検知されていません。スキャンを実行すると結果がここに表示されます。
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {recentChanges.map((change) => (
              <li key={change.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {change.page.service.displayName} - {change.pageType === "listing" ? "一覧" : "詳細"}
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
