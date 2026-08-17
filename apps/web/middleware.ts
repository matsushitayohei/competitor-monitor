export { auth as middleware } from "@/lib/auth";

export const config = {
  matcher: [
    // Protect all routes except login, API auth, backfill-dates, and static assets
    "/((?!login|api/auth|api/backfill-dates|_next/static|_next/image|favicon.ico).*)",
  ],
};
