import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/**
 * One-time backfill endpoint: Extracts publishedAt dates from bodyText
 * for articles where publishedAt is NULL.
 *
 * GET /api/backfill-dates?dry-run=true  (preview mode)
 * GET /api/backfill-dates               (execute mode)
 *
 * This endpoint should be removed after the backfill is complete.
 */

function extractDateFromText(text: string): string | null {
  if (!text) return null;

  // Check the first 1000 characters where dates typically appear
  const head = text.slice(0, 1000);

  // Pattern: 2025年1月15日
  const jpMatch = head.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
  if (jpMatch) {
    const [, year, month, day] = jpMatch;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }

  // Pattern: 2025.01.15
  const dotMatch = head.match(/(\d{4})\.(\d{1,2})\.(\d{1,2})/);
  if (dotMatch) {
    const [, year, month, day] = dotMatch;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }

  // Pattern: 2025/01/15
  const slashMatch = head.match(/(\d{4})\/(\d{1,2})\/(\d{1,2})/);
  if (slashMatch) {
    const [, year, month, day] = slashMatch;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }

  // Pattern: 2025-01-15
  const dashMatch = head.match(/(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (dashMatch) {
    const [, year, month, day] = dashMatch;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }

  return null;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const dryRun = searchParams.get("dry-run") === "true";

  try {
    // Find articles without publishedAt
    const articles = await prisma.pressArticle.findMany({
      where: {
        publishedAt: null,
        deletedAt: null,
      },
      select: {
        id: true,
        title: true,
        bodyText: true,
      },
    });

    const results: { id: string; title: string; date: string }[] = [];
    const noDate: { id: string; title: string }[] = [];

    for (const article of articles) {
      const date = extractDateFromText(article.bodyText || "");
      if (date) {
        results.push({
          id: article.id,
          title: article.title.slice(0, 60),
          date,
        });

        if (!dryRun) {
          await prisma.pressArticle.update({
            where: { id: article.id },
            data: { publishedAt: new Date(date + "T00:00:00Z") },
          });
        }
      } else {
        noDate.push({
          id: article.id,
          title: article.title.slice(0, 60),
        });
      }
    }

    return NextResponse.json({
      mode: dryRun ? "dry-run" : "executed",
      totalWithoutDate: articles.length,
      updated: results.length,
      stillNoDate: noDate.length,
      updatedArticles: results,
      noDateArticles: noDate.slice(0, 20), // show first 20
    });
  } catch (error) {
    console.error("Backfill error:", error);
    return NextResponse.json(
      { error: "バックフィル処理でエラーが発生しました", details: String(error) },
      { status: 500 }
    );
  }
}
