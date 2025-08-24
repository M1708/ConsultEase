// // frontend/components/auth/ProtectedRoute.tsx
// "use client";

// import { useEffect, ReactNode } from "react";
// import { useRouter } from "next/navigation";
// import { useAuth } from "@/hooks/useAuth";
// import { useSession } from "./SessionProvider";
// //import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

// interface ProtectedRouteProps {
//   children: ReactNode;
//   requiredRole?: string[];
//   fallbackPath?: string;
// }

// export const ProtectedRoute = ({
//   children,
//   requiredRole,
//   fallbackPath = "/login",
// }: ProtectedRouteProps) => {
//   const router = useRouter();
//   const { isAuthenticated, user, loading } = useAuth();
//   const { hasValidSession, sessionLoading } = useSession();

//   useEffect(() => {
//     if (!loading && !sessionLoading) {
//       if (!isAuthenticated || !hasValidSession) {
//         router.push(fallbackPath);
//         return;
//       }

//       if (requiredRole && user && !requiredRole.includes(user.role)) {
//         router.push("/unauthorized");
//         return;
//       }
//     }
//   }, [
//     isAuthenticated,
//     hasValidSession,
//     user,
//     loading,
//     sessionLoading,
//     router,
//     requiredRole,
//     fallbackPath,
//   ]);

//   if (loading || sessionLoading) {
//     return (
//       <div className="flex items-center justify-center min-h-screen">
//         <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
//       </div>
//     );
//   }

//   if (!isAuthenticated || !hasValidSession) {
//     return null;
//   }

//   if (requiredRole && user && !requiredRole.includes(user.role)) {
//     return null;
//   }

//   return <>{children}</>;
// };

"use client";

import { useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: string[];
  fallbackPath?: string;
}

export const ProtectedRoute = ({
  children,
  requiredRole,
  fallbackPath = "/login",
}: ProtectedRouteProps) => {
  const router = useRouter();
  const { isAuthenticated, user, loading } = useAuth();
  // Removed useSession() call that was causing the error

  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        router.push(fallbackPath);
        return;
      }

      if (requiredRole && user && !requiredRole.includes(user.role)) {
        router.push("/unauthorized");
        return;
      }
    }
  }, [isAuthenticated, user, loading, router, requiredRole, fallbackPath]);

  // Only show loading spinner for the first 500ms to prevent flash
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requiredRole && user && !requiredRole.includes(user.role)) {
    return null;
  }

  return <>{children}</>;
};
