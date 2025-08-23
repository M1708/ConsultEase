"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetEmail, setResetEmail] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const { login, error: authError } = useAuth();
  const router = useRouter();

  useEffect(() => {
    console.log("ENV CHECK:");
    console.log("SUPABASE_URL:", process.env.NEXT_PUBLIC_SUPABASE_URL);
    console.log(
      "SUPABASE_KEY:",
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? "Present" : "Missing"
    );
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    console.log("1. Login attempt:", { email, password });

    try {
      await login(email, password);
      console.log("2. Login successful, redirecting...");
      router.push("/chat");
    } catch (error) {
      console.log("3. Login failed:", error);
      setMessage("Login failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      // This will connect to Supabase later
      // For now, just show success message
      await new Promise((resolve) => setTimeout(resolve, 1000)); // Simulate API call
      setMessage("Password reset link sent to your email!");
    } catch (error) {
      setMessage("Error sending reset email. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (showForgotPassword) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#f9fafb",
          padding: "1rem",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: "400px",
            padding: "2rem",
            backgroundColor: "white",
            borderRadius: "8px",
            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
          }}
        >
          <h2
            style={{
              fontSize: "1.5rem",
              fontWeight: "bold",
              textAlign: "center",
              marginBottom: "1.5rem",
              color: "#1f2937",
            }}
          >
            Reset Password
          </h2>

          {message && (
            <div
              style={{
                padding: "12px",
                marginBottom: "1rem",
                borderRadius: "6px",
                backgroundColor: message.includes("Error")
                  ? "#fef2f2"
                  : "#f0f9ff",
                color: message.includes("Error") ? "#dc2626" : "#1d4ed8",
                border: `1px solid ${
                  message.includes("Error") ? "#fecaca" : "#bfdbfe"
                }`,
                fontSize: "14px",
              }}
            >
              {message}
            </div>
          )}

          <form
            onSubmit={handleForgotPassword}
            style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
          >
            <input
              type="email"
              placeholder="Enter your email address"
              value={resetEmail}
              onChange={(e) => setResetEmail(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "12px",
                border: "1px solid #d1d5db",
                borderRadius: "6px",
                fontSize: "16px",
                boxSizing: "border-box",
              }}
            />
            <button
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                backgroundColor: loading ? "#9ca3af" : "#2563eb",
                color: "white",
                padding: "12px",
                borderRadius: "6px",
                border: "none",
                fontSize: "16px",
                fontWeight: "600",
                cursor: loading ? "not-allowed" : "pointer",
                boxSizing: "border-box",
              }}
            >
              {loading ? "Sending..." : "Send Reset Link"}
            </button>
          </form>

          <div style={{ textAlign: "center", marginTop: "1.5rem" }}>
            <button
              onClick={() => setShowForgotPassword(false)}
              style={{
                background: "none",
                border: "none",
                color: "#2563eb",
                textDecoration: "underline",
                cursor: "pointer",
                fontSize: "14px",
              }}
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#f9fafb",
        padding: "1rem",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "400px",
          padding: "2rem",
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        }}
      >
        <h2
          style={{
            fontSize: "1.5rem",
            fontWeight: "bold",
            textAlign: "center",
            marginBottom: "1.5rem",
            color: "#1f2937",
          }}
        >
          Login to ConsultEase
        </h2>

        {(message || authError) && (
          <div
            style={{
              padding: "12px",
              marginBottom: "1rem",
              borderRadius: "6px",
              backgroundColor: "#fef2f2",
              color: "#dc2626",
              border: "1px solid #fecaca",
              fontSize: "14px",
            }}
          >
            {message || authError}
          </div>
        )}

        <form
          onSubmit={handleLogin}
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{
              width: "100%",
              padding: "12px",
              border: "1px solid #d1d5db",
              borderRadius: "6px",
              fontSize: "16px",
              boxSizing: "border-box",
            }}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{
              width: "100%",
              padding: "12px",
              border: "1px solid #d1d5db",
              borderRadius: "6px",
              fontSize: "16px",
              boxSizing: "border-box",
            }}
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              backgroundColor: loading ? "#9ca3af" : "#2563eb",
              color: "white",
              padding: "12px",
              borderRadius: "6px",
              border: "none",
              fontSize: "16px",
              fontWeight: "600",
              cursor: loading ? "not-allowed" : "pointer",
              boxSizing: "border-box",
            }}
          >
            {loading ? "Signing In..." : "Sign In"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "1.5rem" }}>
          <button
            onClick={() => setShowForgotPassword(true)}
            style={{
              background: "none",
              border: "none",
              color: "#2563eb",
              textDecoration: "underline",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            Forgot your password?
          </button>
        </div>
      </div>
    </div>
  );
}
