import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateServiceInput } from "@/lib/validations";

// Task 2.1: GET /api/services - List Services
export async function GET() {
  try {
    const services = await prisma.service.findMany({
      where: { deletedAt: null },
      orderBy: { createdAt: "asc" },
      include: {
        _count: {
          select: {
            pages: { where: { deletedAt: null } },
          },
        },
      },
    });

    return NextResponse.json({ services }, { status: 200 });
  } catch (error) {
    console.error("Failed to fetch services:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}

// Task 2.2: POST /api/services - Create Service
export async function POST(request: NextRequest) {
  try {
    const data = await request.json();

    const validation = validateServiceInput(data);
    if (!validation.valid) {
      return NextResponse.json(
        { error: "入力内容に誤りがあります", fields: validation.fields },
        { status: 400 }
      );
    }

    const service = await prisma.service.create({
      data: {
        name: data.name,
        displayName: data.displayName,
        baseUrl: data.baseUrl,
        isActive: data.isActive ?? true,
      },
    });

    return NextResponse.json({ service }, { status: 201 });
  } catch (error: unknown) {
    if (
      error &&
      typeof error === "object" &&
      "code" in error &&
      error.code === "P2002"
    ) {
      return NextResponse.json(
        {
          error: "このサービス名は既に使用されています",
          fields: { name: "このサービス名は既に使用されています" },
        },
        { status: 409 }
      );
    }

    console.error("Failed to create service:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}
