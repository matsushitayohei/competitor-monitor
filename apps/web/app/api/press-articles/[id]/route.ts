import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// PATCH /api/press-articles/[id]
// Updates mutable fields on a press article.
// Accepted body: { summary?: string, classification?: string, relevanceCategory?: string, needsManualReview?: boolean }
export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    const body = await request.json();

    const allowedFields = [
      "summary",
      "classification",
      "relevanceCategory",
      "needsManualReview",
    ] as const;

    const data: Record<string, unknown> = {};
    for (const field of allowedFields) {
      if (field in body) {
        data[field] = body[field];
      }
    }

    if (Object.keys(data).length === 0) {
      return NextResponse.json(
        { error: "更新するフィールドがありません" },
        { status: 400 }
      );
    }

    const article = await prisma.pressArticle.findUnique({
      where: { id, deletedAt: null },
    });

    if (!article) {
      return NextResponse.json(
        { error: "記事が見つかりません" },
        { status: 404 }
      );
    }

    const updated = await prisma.pressArticle.update({
      where: { id },
      data: {
        ...data,
        updatedAt: new Date(),
      },
    });

    return NextResponse.json(updated);
  } catch (error) {
    console.error("Failed to update press article:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}
