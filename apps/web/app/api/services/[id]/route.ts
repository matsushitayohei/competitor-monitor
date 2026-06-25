import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateServiceInput } from "@/lib/validations";

// Task 2.3: PUT /api/services/[id] - Update Service
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;

    const existing = await prisma.service.findFirst({
      where: { id, deletedAt: null },
    });

    if (!existing) {
      return NextResponse.json(
        { error: "対象のサービスが見つかりません" },
        { status: 404 }
      );
    }

    const data = await request.json();

    const validation = validateServiceInput(data, { partial: true });
    if (!validation.valid) {
      return NextResponse.json(
        { error: "入力内容に誤りがあります", fields: validation.fields },
        { status: 400 }
      );
    }

    // Check name uniqueness if name is being changed
    if (data.name !== undefined && data.name !== existing.name) {
      const conflict = await prisma.service.findFirst({
        where: {
          name: data.name,
          deletedAt: null,
          id: { not: id },
        },
      });

      if (conflict) {
        return NextResponse.json(
          {
            error: "このサービス名は既に使用されています",
            fields: { name: "このサービス名は既に使用されています" },
          },
          { status: 409 }
        );
      }
    }

    const service = await prisma.service.update({
      where: { id },
      data: {
        ...(data.name !== undefined && { name: data.name }),
        ...(data.displayName !== undefined && {
          displayName: data.displayName,
        }),
        ...(data.baseUrl !== undefined && { baseUrl: data.baseUrl }),
        ...(data.isActive !== undefined && { isActive: data.isActive }),
      },
    });

    return NextResponse.json({ service }, { status: 200 });
  } catch (error) {
    console.error("Failed to update service:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}

// Task 2.4: DELETE /api/services/[id] - Soft Delete Service
export async function DELETE(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;

    const existing = await prisma.service.findFirst({
      where: { id, deletedAt: null },
    });

    if (!existing) {
      return NextResponse.json(
        { error: "対象のサービスが見つかりません" },
        { status: 404 }
      );
    }

    const now = new Date();

    await prisma.$transaction([
      prisma.service.update({
        where: { id },
        data: { deletedAt: now },
      }),
      prisma.monitoredPage.updateMany({
        where: { serviceId: id, deletedAt: null },
        data: { deletedAt: now },
      }),
    ]);

    return NextResponse.json(
      { message: "サービスを削除しました" },
      { status: 200 }
    );
  } catch (error) {
    console.error("Failed to delete service:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}
