import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve(__dirname, "../../../apps/web/.env.local") });
config({ path: resolve(__dirname, "../.env"), override: true });

import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  // Delete ALL advice and changes (all current records are noise)
  const deletedAdvice = await prisma.advice.deleteMany({});
  console.log(`Deleted ${deletedAdvice.count} advice records`);

  const deletedChanges = await prisma.change.deleteMany({});
  console.log(`Deleted ${deletedChanges.count} change records`);

  await prisma.$disconnect();
}

main().catch((e) => { console.error(e); process.exit(1); });
