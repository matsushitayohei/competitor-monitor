import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validatePageInput } from "@/lib/validations";

// Task 3.3: PUT /api/pages/[id] - Update Page
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;

    const existing = await prisma.monitoredPage.findFirst({
      where: { id, deletedAt: null },
    });

    if (!existing) {
      return NextResponse.json(
        { error: "対象のページが見つかりません" },
        { status: 404 }
      );
    }

    const data = await request.json();

    const validation = validatePageInput(data, { partial: true });
    if (!validation.valid) {
      return NextResponse.json(
        { error: "入力内容に誤りがあります", fields: validation.fields },
        { status: 400 }
      );
    }

    const page = await prisma.monitoredPage.update({
      where: { id },
      data: {
        ...(data.url !== undefined && { url: data.url }),
        ...(data.pageType !== undefined && { pageType: data.pageType }),
        ...(data.device !== undefined && { device: data.device }),
        ...(data.isActive !== undefined && { isActive: data.isActive }),
      },
    });

    return NextResponse.json({ page }, { status: 200 });
  } catch (error) {
    console.error("Failed to update page:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}

// Task 3.4: DELETE /api/pages/[id] - Soft Delete Page
export async function DELETE(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;

    const existing = await prisma.monitoredPage.findFirst({
      where: { id, deletedAt: null },
    });

    if (!existing) {
      return NextResponse.json(
        { error: "対象のページが見つかりません" },
        { status: 404 }
      );
    }

    await prisma.monitoredPage.update({
      where: { id },
      data: { deletedAt: new Date() },
    });

    return NextResponse.json(
      { message: "ページを削除しました" },
      { status: 200 }
    );
  } catch (error) {
    console.error("Failed to delete page:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}
