import { prisma } from "@/lib/prisma";
import { Sidebar } from "@/components/sidebar";

export default async function SitesPage() {
  const services = await prisma.service.findMany({
    where: { deletedAt: null },
    include: { pages: { where: { deletedAt: null } } },
    orderBy: { createdAt: "asc" },
  });

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">対象サイト</h1>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {services.map((service) => (
            <div key={service.id} className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">{service.displayName}</h2>
                <span className={`px-2 py-1 text-xs rounded-full ${service.isActive ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}>
                  {service.isActive ? "有効" : "無効"}
                </span>
              </div>
              <p className="text-sm text-gray-500 mb-2">{service.baseUrl}</p>
              <p className="text-sm text-gray-600">{service.pages.length} ページ監視中</p>
            </div>
          ))}
        </div>

        {services.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            監視対象のサービスがまだ登録されていません。
          </div>
        )}
      </main>
    </div>
  );
}
