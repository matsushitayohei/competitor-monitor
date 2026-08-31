-- Add isDismissed column to Change table
-- Run this in Vercel Storage > Query tab (disable read-only toggle first)

ALTER TABLE "Change"
  ADD COLUMN IF NOT EXISTS "isDismissed" BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS "Change_isDismissed_idx"
  ON "Change" ("isDismissed");
