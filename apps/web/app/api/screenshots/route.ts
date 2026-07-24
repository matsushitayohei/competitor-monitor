import { NextRequest, NextResponse } from "next/server";

/**
 * Screenshot proxy API
 *
 * Proxies Vercel Blob Storage URLs to handle:
 * 1. Private blob URLs (not directly accessible from browser)
 * 2. Mixed public/private blob stores
 * 3. CORS or network issues with direct blob access
 *
 * The proxy adds authorization for private blobs and serves images
 * with proper cache headers.
 *
 * Usage: GET /api/screenshots?url=<encoded-blob-url>
 */
export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");

  if (!url) {
    return NextResponse.json({ error: "Missing url parameter" }, { status: 400 });
  }

  // Validate that the URL is from Vercel Blob Storage
  if (!url.includes(".blob.vercel-storage.com/")) {
    return NextResponse.json(
      { error: "Invalid URL: only Vercel Blob URLs are allowed" },
      { status: 403 }
    );
  }

  try {
    const headers: Record<string, string> = {};
    const token = process.env.BLOB_READ_WRITE_TOKEN;

    // Add authorization for private blobs, or always when token is available
    // (public blobs will also accept the token without issues)
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      headers,
      // Disable Next.js fetch cache for fresh data
      cache: "no-store",
    });

    if (!response.ok) {
      console.error(
        `[Screenshot Proxy] Failed to fetch: ${response.status} ${response.statusText} for URL: ${url}`
      );
      return NextResponse.json(
        { error: `Failed to fetch image: ${response.status}` },
        { status: response.status }
      );
    }

    const blob = await response.arrayBuffer();
    const contentType = response.headers.get("content-type") || "image/png";

    return new NextResponse(blob, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (error) {
    console.error("[Screenshot Proxy] Error:", error);
    return NextResponse.json(
      { error: "Failed to fetch screenshot" },
      { status: 500 }
    );
  }
}
