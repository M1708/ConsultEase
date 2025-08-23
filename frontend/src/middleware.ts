import { createMiddlewareClient } from "@supabase/auth-helpers-nextjs";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const supabase = createMiddlewareClient({ req, res });

  const {
    data: { session },
  } = await supabase.auth.getSession();

  // Public routes that don't require authentication
  const publicPaths = ["/login", "/"];
  const isPublicPath = publicPaths.some((path) =>
    req.nextUrl.pathname.startsWith(path)
  );

  // If user is not signed in and trying to access protected route
  if (!session && !isPublicPath) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  // If user is signed in and trying to access login page
  if (session && req.nextUrl.pathname === "/login") {
    return NextResponse.redirect(new URL("/chat", req.url));
  }

  // If user is signed in and on home page, redirect to chat
  if (session && req.nextUrl.pathname === "/") {
    return NextResponse.redirect(new URL("/chat", req.url));
  }

  return res;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
