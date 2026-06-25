import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validatePageInput } from "@/lib/validations";

// Task 3.1: GET /api/services/[id]/pages - List Pages for Service
export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;

    const service = await prisma.service.findFirst({
      where: { id, deletedAt: null },
    });

    if (!service) {
      return NextResponse.json(
        { error: "対象のサービスが見つかりません" },
        { status: 404 }
      );
    }

    const pages = await prisma.monitoredPage.findMany({
      where: { serviceId: id, deletedAt: null },
      orderBy: { createdAt: "asc" },
    });

    return NextResponse.json({ pages }, { status: 200 });
  } catch (error) {
    console.error("Failed to fetch pages:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}

// Task 3.2: POST /api/services/[id]/pages - Create Monitored Page
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;

    const service = await prisma.service.findFirst({
      where: { id, deletedAt: null },
    });

    if (!service) {
      return NextResponse.json(
        { error: "対象のサービスが見つかりません" },
        { status: 404 }
      );
    }

    const data = await request.json();

    const validation = validatePageInput(data);
    if (!validation.valid) {
      return NextResponse.json(
        { error: "入力内容に誤りがあります", fields: validation.fields },
        { status: 400 }
      );
    }

    const page = await prisma.monitoredPage.create({
      data: {
        serviceId: id,
        url: data.url,
        pageType: data.pageType,
        device: data.device,
        isActive: data.isActive ?? true,
      },
    });

    return NextResponse.json({ page }, { status: 201 });
  } catch (error) {
    console.error("Failed to create page:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました" },
      { status: 500 }
    );
  }
}
