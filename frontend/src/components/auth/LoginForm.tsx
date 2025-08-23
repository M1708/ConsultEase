// frontend/components/auth/LoginForm.tsx
export const LoginForm = () => {
  return (
    <div className="w-full max-w-md mx-auto p-8">
      <h2 className="text-2xl font-bold mb-4">Login</h2>
      <div className="text-center">
        <div className="w-6 h-6 mx-auto animate-spin">
          <svg fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </div>
      </div>
    </div>
  );
};
/*
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/useAuth";
import { Eye, EyeOff, LogIn } from "lucide-react";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export const LoginForm = () => {
  const router = useRouter();
  const { login, loading, error, clearError } = useAuth();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    try {
      clearError();
      await login(data.email, data.password);
      router.push("/chat");
    } catch (error) {
      if (error instanceof Error) {
        if (error.message.includes("Invalid login credentials")) {
          setError("email", { message: "Invalid email or password" });
          setError("password", { message: "Invalid email or password" });
        } else {
          setError("email", { message: error.message });
        }
      }
    }
  };

  return (
    <div className="w-full max-w-md space-y-8">
      <div className="text-center">
        <div className="mx-auto h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center">
          <LogIn className="h-6 w-6 text-blue-600" />
        </div>
        <h2 className="mt-6 text-3xl font-bold text-gray-900">
          Welcome to ConsultEase
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Sign in to access your AI-powered consulting workspace
        </p>
      </div>

      <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            <p className="text-sm">{error}</p>
          </div>
        )}

        <Input
          label="Email address"
          type="email"
          autoComplete="email"
          {...register("email")}
          error={errors.email?.message}
          placeholder="admin@consultease.com"
        />

        <div className="relative">
          <Input
            label="Password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            {...register("password")}
            error={errors.password?.message}
            placeholder="Enter your password"
          />
          <button
            type="button"
            className="absolute right-3 top-9 text-gray-400 hover:text-gray-600"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? (
              <EyeOff className="h-5 w-5" />
            ) : (
              <Eye className="h-5 w-5" />
            )}
          </button>
        </div>

        <Button
          type="submit"
          className="w-full"
          loading={loading}
          disabled={loading}
        >
          {loading ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <div className="mt-6">
        <div className="text-center">
          <p className="text-sm text-gray-600">
            Demo credentials available for testing
          </p>
          <div className="mt-2 text-xs text-gray-500">
            <p>Admin: admin@consultease.com</p>
            <p>Manager: manager@consultease.com</p>
            <p>Employee: alice.johnson@consultease.com</p>
          </div>
        </div>
      </div>
    </div>
  );
};
*/
