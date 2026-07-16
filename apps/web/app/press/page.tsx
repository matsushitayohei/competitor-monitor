import { prisma } from "@/lib/prisma";
import { Sidebar } from "@/components/sidebar";
import { PressSourceList } from "@/components/press-source-list";
import { ToastProvider } from "@/components/toast";

export const dynamic = 'force-dynamic';

export default async function PressSourcesPage() {
  const sources = await prisma.pressSource.findMany({
    where: { deletedAt: null },
    orderBy: { createdAt: "asc" },
  });

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <ToastProvider>
          <PressSourceList sources={JSON.parse(JSON.stringify(sources))} />
        </ToastProvider>
      </main>
    </div>
  );
}
