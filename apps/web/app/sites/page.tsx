import { prisma } from "@/lib/prisma";
import { Sidebar } from "@/components/sidebar";
import { ServiceCardList } from "@/components/service-card-list";
import { ToastProvider } from "@/components/toast";

export const dynamic = 'force-dynamic';

/** Convert Date fields to ISO strings so Client Components receive plain objects. */
function serializeServices(services: Awaited<ReturnType<typeof fetchServices>>) {
  return services.map((s) => ({
    ...s,
    createdAt: s.createdAt?.toISOString() ?? null,
    updatedAt: s.updatedAt?.toISOString() ?? null,
    deletedAt: s.deletedAt?.toISOString() ?? null,
    pages: s.pages.map((p) => ({
      ...p,
      lastScannedAt: p.lastScannedAt?.toISOString() ?? null,
      createdAt: p.createdAt?.toISOString() ?? null,
      updatedAt: p.updatedAt?.toISOString() ?? null,
      deletedAt: p.deletedAt?.toISOString() ?? null,
    })),
  }));
}

async function fetchServices() {
  return prisma.service.findMany({
    where: { deletedAt: null },
    include: {
      pages: { where: { deletedAt: null }, orderBy: { createdAt: "asc" } },
      _count: { select: { pages: { where: { deletedAt: null } } } },
    },
    orderBy: { createdAt: "asc" },
  });
}

export default async function SitesPage() {
  const services = serializeServices(await fetchServices());

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <ToastProvider>
          <ServiceCardList services={services} />
        </ToastProvider>
      </main>
    </div>
  );
}
