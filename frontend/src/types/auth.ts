export interface User {
  user_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  full_name: string;
  role: string;
  status: string;
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

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  error: string | null;
}
