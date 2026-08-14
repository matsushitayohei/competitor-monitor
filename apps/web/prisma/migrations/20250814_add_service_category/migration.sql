-- Add category column to Service table
ALTER TABLE "Service" ADD COLUMN "category" TEXT NOT NULL DEFAULT 'real_estate';

-- Create index on category
CREATE INDEX "Service_category_idx" ON "Service"("category");
