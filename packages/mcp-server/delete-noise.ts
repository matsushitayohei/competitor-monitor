/**
 * delete-noise.ts — Manual noise cleanup script.
 *
 * Deletes Change + Advice records that are confirmed noise.
 * SAFETY GUARDS:
 *   1. Refuses to run against a URL containing "neon.tech" without --force flag
 *      (production Neon DB guard — pass --force only when you are certain).
 *   2. Performs a dry-run count first and asks for explicit confirmation before deleting.
 *   3. Requires at least one filter (--before, --category, --keyword) to prevent
 *      accidental full-table wipe.
 *
 * Usage:
 *   npx ts-node delete-noise.ts --before 2026-08-01 --dry-run
 *   npx ts-node delete-noise.ts --before 2026-08-01 --category SEO
 *   npx ts-node delete-noise.ts --keyword "fr301fd001MailForm"
 *   npx ts-node delete-noise.ts --before 2026-08-28 --force   # prod DB
 */

import { config } from "dotenv";
import { resolve } from "path";
import * as readline from "readline";

config({ path: resolve(__dirname, "../../../apps/web/.env.local") });
config({ path: resolve(__dirname, "../.env"), override: true });

import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

function parseArgs(): {
  before?: string;
  category?: string;
  keyword?: string;
  dryRun: boolean;
  force: boolean;
} {
  const args = process.argv.slice(2);
  const get = (flag: string): string | undefined => {
    const idx = args.indexOf(flag);
    return idx >= 0 ? args[idx + 1] : undefined;
  };
  return {
    before: get("--before"),
    category: get("--category"),
    keyword: get("--keyword"),
    dryRun: args.includes("--dry-run"),
    force: args.includes("--force"),
  };
}

function confirm(question: string): Promise<boolean> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(`${question} (yes/no): `, (answer) => {
      rl.close();
      resolve(answer.trim().toLowerCase() === "yes");
    });
  });
}

async function main() {
  const opts = parseArgs();

  // Guard: require at least one filter
  if (!opts.before && !opts.category && !opts.keyword) {
    console.error(
      "ERROR: At least one filter is required (--before YYYY-MM-DD, --category X, or --keyword X).\n" +
        "This prevents accidental full-table deletion."
    );
    process.exit(1);
  }

  // Guard: warn about production DB
  const dbUrl = process.env.DATABASE_URL ?? "";
  const isProd = dbUrl.includes("neon.tech");
  if (isProd && !opts.force) {
    console.error(
      "ERROR: DATABASE_URL appears to point at a production Neon DB.\n" +
        "Re-run with --force if you are certain you want to delete from production."
    );
    process.exit(1);
  }
  if (isProd) {
    console.warn("WARNING: --force specified against what looks like a production DB.");
  }

  // Build where clause
  // --category filters on Change.category (CRO, SEO, AD_PRODUCT, AI, OTHER)
  // --keyword  filters on Advice.summary (human-readable summary text)
  const where: Record<string, unknown> = {};
  if (opts.before) where.detectedAt = { lt: new Date(opts.before) };
  if (opts.category) where.category = opts.category;
  if (opts.keyword) {
    where.advice = {
      summary: { contains: opts.keyword },
    };
  }

  const count = await prisma.change.count({ where });
  console.log(`Matching Change records: ${count}`);

  if (count === 0) {
    console.log("Nothing to delete.");
    await prisma.$disconnect();
    return;
  }

  if (opts.dryRun) {
    console.log("--dry-run mode: no records deleted.");
    await prisma.$disconnect();
    return;
  }

  // Interactive confirmation
  const ok = await confirm(`Delete ${count} Change records and their Advice records?`);
  if (!ok) {
    console.log("Aborted.");
    await prisma.$disconnect();
    return;
  }

  const changeIds = (await prisma.change.findMany({ where, select: { id: true } })).map((c) => c.id);

  const deletedAdvice = await prisma.advice.deleteMany({ where: { changeId: { in: changeIds } } });
  console.log(`Deleted ${deletedAdvice.count} Advice records`);

  const deletedChanges = await prisma.change.deleteMany({ where: { id: { in: changeIds } } });
  console.log(`Deleted ${deletedChanges.count} Change records`);

  await prisma.$disconnect();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
