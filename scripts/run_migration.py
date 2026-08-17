"""Run migration SQL against the database.

Usage:
    python scripts/run_migration.py

Requires DATABASE_URL environment variable (non-pooling connection).
Set it in apps/web/.env.local or packages/scraper/.env or pass directly.
"""

import os
import sys

from dotenv import load_dotenv

# Try loading from multiple .env files
for env_path in [
    os.path.join(os.path.dirname(__file__), "..", "apps", "web", ".env.local"),
    os.path.join(os.path.dirname(__file__), "..", "apps", "web", ".env"),
    os.path.join(os.path.dirname(__file__), "..", "packages", "scraper", ".env"),
]:
    if os.path.exists(env_path):
        load_dotenv(env_path)

import psycopg2


def get_database_url() -> str:
    """Get a writable database URL (non-pooling preferred)."""
    # Non-pooling URL allows DDL operations
    url = os.environ.get("POSTGRES_URL_NON_POOLING")
    if url:
        return url
    # Fall back to DATABASE_URL (may or may not be pooled)
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # Try Vercel-style env var
    url = os.environ.get("competitor_monitor_POSTGRES_URL")
    if url:
        return url
    raise RuntimeError(
        "No database URL found. Set POSTGRES_URL_NON_POOLING or DATABASE_URL."
    )


MIGRATION_SQL = """
-- 1. PageStructure
CREATE TABLE IF NOT EXISTS "PageStructure" (
  "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
  "pageId" TEXT NOT NULL,
  "capturedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "structureSummary" JSONB NOT NULL,
  "sections" JSONB NOT NULL,
  "cvPoints" JSONB,
  "formAnalysis" JSONB,
  "componentCount" INTEGER NOT NULL DEFAULT 0,
  "hash" VARCHAR(64) NOT NULL,
  "metadata" JSONB,
  CONSTRAINT "PageStructure_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "PageStructure_pageId_fkey" FOREIGN KEY ("pageId") 
    REFERENCES "MonitoredPage"("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "PageStructure_pageId_capturedAt_idx" 
  ON "PageStructure"("pageId", "capturedAt" DESC);
CREATE INDEX IF NOT EXISTS "PageStructure_hash_idx" 
  ON "PageStructure"("hash");

-- 2. OwnPage
CREATE TABLE IF NOT EXISTS "OwnPage" (
  "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
  "name" VARCHAR(255) NOT NULL,
  "pageType" VARCHAR(50) NOT NULL,
  "url" TEXT NOT NULL,
  "device" VARCHAR(10) NOT NULL DEFAULT 'pc',
  "category" VARCHAR(50) DEFAULT 'chintai',
  "isActive" BOOLEAN NOT NULL DEFAULT true,
  "lastScannedAt" TIMESTAMP(3),
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletedAt" TIMESTAMP(3),
  CONSTRAINT "OwnPage_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "OwnPage_pageType_device_idx" 
  ON "OwnPage"("pageType", "device");
CREATE INDEX IF NOT EXISTS "OwnPage_isActive_idx" 
  ON "OwnPage"("isActive");

-- 3. OwnPageStructure
CREATE TABLE IF NOT EXISTS "OwnPageStructure" (
  "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
  "ownPageId" TEXT NOT NULL,
  "capturedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "structureSummary" JSONB NOT NULL,
  "sections" JSONB NOT NULL,
  "cvPoints" JSONB,
  "formAnalysis" JSONB,
  "componentCount" INTEGER NOT NULL DEFAULT 0,
  "hash" VARCHAR(64) NOT NULL,
  "metadata" JSONB,
  CONSTRAINT "OwnPageStructure_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "OwnPageStructure_ownPageId_fkey" FOREIGN KEY ("ownPageId") 
    REFERENCES "OwnPage"("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "OwnPageStructure_ownPageId_capturedAt_idx" 
  ON "OwnPageStructure"("ownPageId", "capturedAt" DESC);
CREATE INDEX IF NOT EXISTS "OwnPageStructure_hash_idx" 
  ON "OwnPageStructure"("hash");

-- 4. Change table structure columns
ALTER TABLE "Change" ADD COLUMN IF NOT EXISTS "structureBeforeId" TEXT;
ALTER TABLE "Change" ADD COLUMN IF NOT EXISTS "structureAfterId" TEXT;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'Change_structureBeforeId_fkey'
  ) THEN
    ALTER TABLE "Change" ADD CONSTRAINT "Change_structureBeforeId_fkey" 
      FOREIGN KEY ("structureBeforeId") REFERENCES "PageStructure"("id") ON DELETE SET NULL;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'Change_structureAfterId_fkey'
  ) THEN
    ALTER TABLE "Change" ADD CONSTRAINT "Change_structureAfterId_fkey" 
      FOREIGN KEY ("structureAfterId") REFERENCES "PageStructure"("id") ON DELETE SET NULL;
  END IF;
END $$;
"""

REGISTER_OWN_PAGES_SQL = """
INSERT INTO "OwnPage" (id, name, "pageType", url, device, category) VALUES
  (gen_random_uuid()::text, 'HOME''S 賃貸 物件詳細 SP', 'detail', 'https://www.homes.co.jp/chintai/room/c427ff08785ddef1731c72e4befb90a272f3eb9b/', 'sp', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 一覧 SP', 'list', 'https://www.homes.co.jp/chintai/tokyo/bunkyo-city/list/', 'sp', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 物件詳細 PC', 'detail', 'https://www.homes.co.jp/chintai/room/c427ff08785ddef1731c72e4befb90a272f3eb9b/', 'pc', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 一覧 PC', 'list', 'https://www.homes.co.jp/chintai/tokyo/bunkyo-city/list/', 'pc', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 トップ SP', 'top', 'https://www.homes.co.jp/chintai/', 'sp', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 トップ PC', 'top', 'https://www.homes.co.jp/chintai/', 'pc', 'chintai');
"""


def main():
    url = get_database_url()
    print(f"Connecting to database...")
    print(f"  URL prefix: {url[:30]}...")

    conn = psycopg2.connect(url, sslmode="require")
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            print("\n[1/3] Running migration (create tables, indexes, constraints)...")
            cur.execute(MIGRATION_SQL)
            print("  Done.")

            print("\n[2/3] Verifying tables...")
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('PageStructure', 'OwnPage', 'OwnPageStructure')
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]
            print(f"  Created tables: {tables}")
            if len(tables) != 3:
                print("  ERROR: Expected 3 tables!")
                sys.exit(1)

            print("\n[3/3] Registering HOME'S pages...")
            # Check if already registered
            cur.execute('SELECT COUNT(*) FROM "OwnPage"')
            count = cur.fetchone()[0]
            if count > 0:
                print(f"  Skipped — {count} pages already exist.")
            else:
                cur.execute(REGISTER_OWN_PAGES_SQL)
                cur.execute('SELECT COUNT(*) FROM "OwnPage"')
                count = cur.fetchone()[0]
                print(f"  Registered {count} pages.")

        print("\n✓ Migration complete!")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
