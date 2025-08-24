export interface User {
  user_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  full_name: string;
  role: UserRole;
  status: UserStatus;
  phone: string | null;
  avatar_url: string | null;
  department: string | null;
  job_title: string | null;
  hire_date: string | null;
  last_login: string | null;
  password_reset_required: boolean;
  two_factor_enabled: boolean;
  preferences: Record<string, unknown>;
  permissions: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type UserRole =
  | "super_admin"
  | "admin"
  | "manager"
  | "employee"
  | "client"
  | "viewer";
export type UserStatus = "active" | "inactive" | "suspended" | "pending";
