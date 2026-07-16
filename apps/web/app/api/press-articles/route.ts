import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

const PAGE_SIZE = 20;

// Task 9.2: GET /api/press-articles - List press articles with filtering and pagination
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const sourceId = searchParams.get("sourceId");
    const classification = searchParams.get("classification");
    const relevanceCategory = searchParams.get("relevanceCategory");
    const page = Math.max(1, parseInt(searchParams.get("page") || "1", 10));

    // Build where clause with AND logic, excluding soft-deleted articles
    const where = {
      deletedAt: null,
      ...(sourceId && { sourceId }),
      ...(classification && { classification }),
      ...(relevanceCategory && { relevanceCategory }),
    };

    const [articles, total] = await Promise.all([
      prisma.pressArticle.findMany({
        where,
        orderBy: { publishedAt: "desc" },
        skip: (page - 1) * PAGE_SIZE,
        take: PAGE_SIZE,
        include: { source: { select: { id: true, name: true } } },
      }),
      prisma.pressArticle.count({ where }),
    ]);

    return NextResponse.json({
      articles,
      pagination: {
        page,
        pageSize: PAGE_SIZE,
        total,
        totalPages: Math.ceil(total / PAGE_SIZE),
      },
    });
  } catch (error) {
    console.error("Failed to fetch press articles:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}
