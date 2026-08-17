-- CreateTable
CREATE TABLE "press_insight" (
    "id" TEXT NOT NULL,
    "articleId" TEXT NOT NULL,
    "insightType" TEXT NOT NULL,
    "title" VARCHAR(200) NOT NULL,
    "description" TEXT NOT NULL,
    "applicability" TEXT,
    "priority" TEXT NOT NULL DEFAULT 'medium',
    "status" TEXT NOT NULL DEFAULT 'new',
    "tags" JSONB NOT NULL DEFAULT '[]',
    "sourceCompetitor" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "press_insight_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "press_insight_insightType_idx" ON "press_insight"("insightType");

-- CreateIndex
CREATE INDEX "press_insight_priority_idx" ON "press_insight"("priority");

-- CreateIndex
CREATE INDEX "press_insight_status_idx" ON "press_insight"("status");

-- CreateIndex
CREATE INDEX "press_insight_sourceCompetitor_idx" ON "press_insight"("sourceCompetitor");

-- CreateIndex
CREATE INDEX "press_insight_createdAt_idx" ON "press_insight"("createdAt" DESC);

-- AddForeignKey
ALTER TABLE "press_insight" ADD CONSTRAINT "press_insight_articleId_fkey" FOREIGN KEY ("articleId") REFERENCES "press_article"("id") ON DELETE CASCADE ON UPDATE CASCADE;
