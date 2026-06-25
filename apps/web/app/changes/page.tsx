import { prisma } from "@/lib/prisma";
import { Sidebar } from "@/components/sidebar";

export default async function ChangesPage() {
  const changes = await prisma.change.findMany({
    orderBy: { detectedAt: "desc" },
    take: 50,
    include: {
      page: { include: { service: true } },
      advice: true,
    },
  });

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">変更履歴</h1>

        {changes.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            まだ変更が検知されていません。
          </div>
        ) : (
          <div className="space-y-4">
            {changes.map((change) => (
              <div key={change.id} className="bg-white p-6 rounded-lg border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">
                      {change.page.service.displayName}
                    </span>
                    <span className="text-sm text-gray-500">
                      {change.pageType === "listing" ? "物件一覧" : "物件詳細"}
                    </span>
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
                </div>
                {change.summary && (
                  <p className="text-sm text-gray-700 mb-3">{change.summary}</p>
                )}
                {change.advice && (
                  <div className="mt-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                    <p className="text-xs font-medium text-yellow-800 mb-1">AIアドバイス</p>
                    <p className="text-sm text-yellow-900">{change.advice.proposal}</p>
                    {change.advice.priority && (
                      <span className={`mt-2 inline-block px-2 py-0.5 text-xs rounded-full ${
                        change.advice.priority === "high" ? "bg-red-100 text-red-800" :
                        change.advice.priority === "medium" ? "bg-orange-100 text-orange-800" :
                        "bg-gray-100 text-gray-600"
                      }`}>
                        優先度: {change.advice.priority}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
