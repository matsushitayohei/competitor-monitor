import { prisma } from "@/lib/prisma";
import { PressSourceList } from "@/components/press-source-list";
import { ToastProvider } from "@/components/toast";

export const dynamic = 'force-dynamic';

export default async function PressSourcesPage() {
  const sources = await prisma.pressSource.findMany({
    where: { deletedAt: null },
    orderBy: { createdAt: "asc" },
  });

  return (
    <ToastProvider>
      <PressSourceList sources={JSON.parse(JSON.stringify(sources))} />
    </ToastProvider>
  );
}
