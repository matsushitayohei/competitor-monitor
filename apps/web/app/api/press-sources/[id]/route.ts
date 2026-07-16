import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validatePressSourceInput } from "@/lib/press-validations";

// PUT /api/press-sources/[id] - Update press source
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;

    const existing = await prisma.pressSource.findFirst({
      where: { id, deletedAt: null },
    });

    if (!existing) {
      return NextResponse.json(
        { error: "対象のプレスソースが見つかりません" },
        { status: 404 }
      );
    }

    const data = await request.json();

    const validation = validatePressSourceInput(data, { partial: true });
    if (!validation.valid) {
      return NextResponse.json(
        { error: "入力内容に誤りがあります", fields: validation.errors },
        { status: 400 }
      );
    }

    // Check for duplicate URL if URL is being changed
    if (data.url !== undefined && data.url !== existing.url) {
      const conflict = await prisma.pressSource.findFirst({
        where: {
          url: data.url,
          deletedAt: null,
          id: { not: id },
        },
      });

      if (conflict) {
        return NextResponse.json(
          {
            error: "このURLは既に登録されています",
            fields: { url: "このURLは既に登録されています" },
          },
          { status: 409 }
        );
      }
    }

    // Check for duplicate name if name is being changed
    if (data.name !== undefined && data.name !== existing.name) {
      const conflict = await prisma.pressSource.findFirst({
        where: {
          name: data.name,
          deletedAt: null,
          id: { not: id },
        },
      });

      if (conflict) {
        return NextResponse.json(
          {
            error: "この名前は既に使用されています",
            fields: { name: "この名前は既に使用されています" },
          },
          { status: 409 }
        );
      }
    }

    const source = await prisma.pressSource.update({
      where: { id },
      data: {
        ...(data.name !== undefined && { name: data.name }),
        ...(data.url !== undefined && { url: data.url }),
        ...(data.isActive !== undefined && { isActive: data.isActive }),
      },
    });

    return NextResponse.json({ source }, { status: 200 });
  } catch (error) {
    console.error("Failed to update press source:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}

// DELETE /api/press-sources/[id] - Soft delete press source
export async function DELETE(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;

    const existing = await prisma.pressSource.findFirst({
      where: { id, deletedAt: null },
    });

    if (!existing) {
      return NextResponse.json(
        { error: "対象のプレスソースが見つかりません" },
        { status: 404 }
      );
    }

    await prisma.pressSource.update({
      where: { id },
      data: { deletedAt: new Date() },
    });

    return NextResponse.json(
      { message: "プレスソースを削除しました" },
      { status: 200 }
    );
  } catch (error) {
    console.error("Failed to delete press source:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}
