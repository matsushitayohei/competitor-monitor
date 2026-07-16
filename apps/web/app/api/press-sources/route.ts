import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validatePressSourceInput } from "@/lib/press-validations";

// GET /api/press-sources - List all active press sources
export async function GET() {
  try {
    const sources = await prisma.pressSource.findMany({
      where: { deletedAt: null },
      orderBy: { createdAt: "asc" },
    });

    return NextResponse.json({ sources }, { status: 200 });
  } catch (error) {
    console.error("Failed to fetch press sources:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}

// POST /api/press-sources - Create new press source
export async function POST(request: NextRequest) {
  try {
    const data = await request.json();

    const validation = validatePressSourceInput(data);
    if (!validation.valid) {
      return NextResponse.json(
        { error: "入力内容に誤りがあります", fields: validation.errors },
        { status: 400 }
      );
    }

    // Check for duplicate URL among active (non-deleted) sources
    const existingUrl = await prisma.pressSource.findFirst({
      where: {
        url: data.url,
        deletedAt: null,
      },
    });

    if (existingUrl) {
      return NextResponse.json(
        {
          error: "このURLは既に登録されています",
          fields: { url: "このURLは既に登録されています" },
        },
        { status: 409 }
      );
    }

    const source = await prisma.pressSource.create({
      data: {
        name: data.name,
        url: data.url,
        isActive: data.isActive ?? true,
      },
    });

    return NextResponse.json({ source }, { status: 201 });
  } catch (error: unknown) {
    if (
      error &&
      typeof error === "object" &&
      "code" in error &&
      error.code === "P2002"
    ) {
      return NextResponse.json(
        {
          error: "この名前は既に使用されています",
          fields: { name: "この名前は既に使用されています" },
        },
        { status: 409 }
      );
    }

    console.error("Failed to create press source:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}
