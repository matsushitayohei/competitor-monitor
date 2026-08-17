-- Migration: Add UIUX Structure Extraction tables
-- Date: 2026-08-14
-- Description: Adds PageStructure, OwnPage, OwnPageStructure tables
--              and structure linking columns to Change table.

-- 1. PageStructure - Competitor page component-level structure snapshots
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

-- 2. OwnPage - LIFULL HOME'S monitored pages
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

-- 3. OwnPageStructure - HOME'S page component-level structure snapshots
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

-- 4. Add structure linking columns to Change table
ALTER TABLE "Change" ADD COLUMN IF NOT EXISTS "structureBeforeId" TEXT;
ALTER TABLE "Change" ADD COLUMN IF NOT EXISTS "structureAfterId" TEXT;

-- Add FK constraints (ignore if already exists)
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
