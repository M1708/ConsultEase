// frontend/components/UserProfile.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { User, LogOut, Settings, ChevronDown, Shield } from "lucide-react";

export const UserProfile = () => {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      router.push("/login");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  if (!user) return null;

  const roleColors = {
    super_admin: "bg-red-100 text-red-800",
    admin: "bg-purple-100 text-purple-800",
    manager: "bg-blue-100 text-blue-800",
    employee: "bg-green-100 text-green-800",
    client: "bg-orange-100 text-orange-800",
    viewer: "bg-gray-100 text-gray-800",
  };

  const roleIcons = {
    super_admin: <Shield className="h-3 w-3" />,
    admin: <Shield className="h-3 w-3" />,
    manager: <User className="h-3 w-3" />,
    employee: <User className="h-3 w-3" />,
    client: <User className="h-3 w-3" />,
    viewer: <User className="h-3 w-3" />,
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <div className="h-8 w-8 bg-gray-200 rounded-full flex items-center justify-center">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.full_name}
              className="h-8 w-8 rounded-full object-cover"
            />
          ) : (
            <User className="h-4 w-4 text-gray-600" />
          )}
        </div>

        <div className="hidden md:block text-left">
          <div className="text-sm font-medium text-gray-900">
            {user.full_name}
          </div>
          <div className="flex items-center gap-1">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                roleColors[user.role]
              }`}
            >
              {roleIcons[user.role]}
              {user.role.replace("_", " ")}
            </span>
          </div>
        </div>

        <ChevronDown
          className={`h-4 w-4 text-gray-500 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          {/* User Info */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 bg-gray-200 rounded-full flex items-center justify-center">
                {user.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.full_name}
                    className="h-12 w-12 rounded-full object-cover"
                  />
                ) : (
                  <User className="h-6 w-6 text-gray-600" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 truncate">
                  {user.full_name}
                </div>
                <div className="text-sm text-gray-500 truncate">
                  {user.email}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                      roleColors[user.role]
                    }`}
                  >
                    {roleIcons[user.role]}
                    {user.role.replace("_", " ")}
                  </span>
                  <span className="text-xs text-gray-500">{user.status}</span>
                </div>
              </div>
            </div>

            {/* Additional User Details */}
            {(user.department || user.job_title) && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                {user.job_title && (
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">Title:</span> {user.job_title}
                  </div>
                )}
                {user.department && (
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">Department:</span>{" "}
                    {user.department}
                  </div>
                )}
                {user.phone && (
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">Phone:</span> {user.phone}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Menu Items */}
          <div className="p-2">
            <button
              onClick={() => {
                setIsOpen(false);
                // Add settings navigation when implemented
                console.log("Settings clicked");
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <Settings className="h-4 w-4" />
              Settings & Preferences
            </button>

            <div className="border-t border-gray-200 my-2" />

            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-gray-200 bg-gray-50 rounded-b-lg">
            <div className="text-xs text-gray-500 text-center">
              Last login:{" "}
              {user.last_login
                ? new Date(user.last_login).toLocaleDateString()
                : "First time"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
