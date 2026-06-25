import { prisma } from "@/lib/prisma";
import { Sidebar } from "@/components/sidebar";

export default async function AdvicePage() {
  const advices = await prisma.advice.findMany({
    orderBy: { createdAt: "desc" },
    take: 30,
    include: { change: { include: { page: { include: { service: true } } } } },
  });

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">AIアドバイス</h1>
        {advices.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            まだAIアドバイスがありません。変更が検知されると自動生成されます。
          </div>
        ) : (
          <div className="space-y-4">
            {advices.map((advice) => (
              <div key={advice.id} className="bg-white p-6 rounded-lg border border-gray-200">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-900">
                    {advice.change.page.service.displayName} - {advice.change.category}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    advice.priority === "high" ? "bg-red-100 text-red-800" :
                    advice.priority === "medium" ? "bg-orange-100 text-orange-800" :
                    "bg-gray-100 text-gray-600"
                  }`}>
                    {advice.priority}
                  </span>
                </div>
                {advice.summary && <p className="text-sm text-gray-700 mb-2"><strong>概要:</strong> {advice.summary}</p>}
                {advice.intent && <p className="text-sm text-gray-700 mb-2"><strong>意図:</strong> {advice.intent}</p>}
                {advice.proposal && <p className="text-sm text-gray-700 mb-2"><strong>提案:</strong> {advice.proposal}</p>}
                {advice.expectedEffect && <p className="text-sm text-gray-700 mb-2"><strong>期待効果:</strong> {advice.expectedEffect}</p>}
                {advice.risks && <p className="text-sm text-gray-500 text-xs"><strong>リスク:</strong> {advice.risks}</p>}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
