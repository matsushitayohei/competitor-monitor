import { prisma } from "@/lib/prisma";
import { Sidebar } from "@/components/sidebar";
import { ServiceCardList } from "@/components/service-card-list";
import { ToastProvider } from "@/components/toast";

export default async function SitesPage() {
  const services = await prisma.service.findMany({
    where: { deletedAt: null },
    include: {
      pages: { where: { deletedAt: null }, orderBy: { createdAt: "asc" } },
      _count: { select: { pages: { where: { deletedAt: null } } } },
    },
    orderBy: { createdAt: "asc" },
  });

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <ToastProvider>
          <ServiceCardList services={JSON.parse(JSON.stringify(services))} />
        </ToastProvider>
      </main>
    </div>
  );
}
