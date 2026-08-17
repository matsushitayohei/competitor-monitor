export { auth as middleware } from "@/lib/auth";

export const config = {
  matcher: [
    // Protect all routes except login, API auth, and static assets
    "/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)",
  ],
};
