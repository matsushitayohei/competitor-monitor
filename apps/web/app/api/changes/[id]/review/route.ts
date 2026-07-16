import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// PATCH /api/changes/[id]/review - Toggle isReviewed status
export async function PATCH(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;

    const existing = await prisma.change.findUnique({
      where: { id },
      select: { id: true, isReviewed: true },
    });

    if (!existing) {
      return NextResponse.json(
        { error: "対象の変更が見つかりません" },
        { status: 404 }
      );
    }

    const change = await prisma.change.update({
      where: { id },
      data: { isReviewed: !existing.isReviewed },
    });

    return NextResponse.json({ change }, { status: 200 });
  } catch (error) {
    console.error("Failed to update review status:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}
