import { create } from "zustand";
import { AuthState, User } from "@/types/auth";
import { supabase } from "@/lib/supabase";
import { authApi } from "@/lib/api";
import { redisSessionManager } from "@/lib/redis-session";

interface AuthStore extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  initialize: () => Promise<void>;
  clearError: () => void;
  updateUser: (user: User) => void;
  sessionId: string | null;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  isAuthenticated: false,
  user: null,
  loading: true,
  error: null,
  sessionId: null,

  login: async (email: string, password: string) => {
    try {
      //console.log("A. Starting login process");
      set({ loading: true, error: null });

      //console.log("B. Calling direct auth API");

      // Use direct API call instead of Supabase client
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_SUPABASE_URL}/auth/v1/token?grant_type=password`,
        {
          method: "POST",
          headers: {
            apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email,
            password,
          }),
        }
      );

      const authData = await response.json();
      //console.log("C. Direct auth response:", authData);

      if (!response.ok || authData.error) {
        throw new Error(authData.error?.message || "Authentication failed");
      }

      if (!authData.user || !authData.access_token) {
        throw new Error("No user or token returned from authentication");
      }

      localStorage.setItem("supabase_token", authData.access_token);

      //console.log("D. Getting user profile from backend");
      const userData = await authApi.getUserProfile(authData.user.id);
      //console.log("E. Backend response:", userData);

      //console.log("F. Setting auth state");
      set({
        isAuthenticated: true,
        user: userData,
        loading: false,
        error: null,
      });

      console.log("F2. Getting Redis session");
      const sessionData = await redisSessionManager.getSession(
        authData.access_token
      );
      if (sessionData) {
        console.log("F3. Setting session ID:", sessionData.sessionId);
        set((state) => ({ ...state, sessionId: sessionData.sessionId }));
      }

      //console.log("G. Updating last login");
      await authApi.updateLastLogin(userData.user_id);
      //console.log("H. Login process complete");
    } catch (error) {
      //console.log("Z. Login error caught:", error);
      set({
        isAuthenticated: false,
        user: null,
        sessionId: null,
        loading: false,
        error: error instanceof Error ? error.message : "Login failed",
      });
      throw error;
    }
  },

  logout: async () => {
    try {
      set({ loading: true });

      // Get token from localStorage (since we're using direct API)
      const token = localStorage.getItem("supabase_token");

      // Invalidate Redis session
      if (token) {
        console.log("Invalidating Redis session");
        await redisSessionManager.invalidateSession(token);
      }

      // Clear localStorage
      localStorage.removeItem("supabase_token");

      // Note: Skip Supabase signOut since we used direct API
      // const { error } = await supabase.auth.signOut();

      set({
        isAuthenticated: false,
        user: null,
        sessionId: null,
        loading: false,
        error: null,
      });
    } catch (error) {
      console.error("Logout failed:", error);
      set({ loading: false });
    }
  },

  initialize: async () => {
    try {
      console.log("INIT: Starting initialization");

      // Skip initialization if already authenticated
      const currentState = get();
      if (currentState.isAuthenticated && currentState.user) {
        console.log("INIT: Already authenticated, skipping");
        return;
      }

      set({ loading: true });

      const {
        data: { session },
        error,
      } = await supabase.auth.getSession();

      console.log("INIT: Supabase session:", session);

      if (error) {
        console.log("INIT: Error:", error);
        throw error;
      }

      if (session?.user) {
        console.log("INIT: Found session user, getting profile");
        const userData = await authApi.getUserProfile(session.user.id);
        console.log("INIT: Setting authenticated state");

        set({
          isAuthenticated: true,
          user: userData,
          loading: false,
          error: null,
        });
      } else {
        console.log("INIT: No session found, setting unauthenticated");
        set({
          isAuthenticated: false,
          user: null,
          sessionId: null,
          loading: false,
          error: null,
        });
      }
    } catch (error) {
      console.log("INIT: Caught error:", error);
      set({
        isAuthenticated: false,
        user: null,
        sessionId: null,
        loading: false,
        error: null,
      });
    }
  },

  clearError: () => set({ error: null }),

  updateUser: (user: User) => set({ user }),
}));

// Listen for auth changes
supabase.auth.onAuthStateChange(async (event, session) => {
  const store = useAuthStore.getState();

  if (event === "SIGNED_OUT" || !session) {
    useAuthStore.setState({
      isAuthenticated: false,
      user: null,
      sessionId: null,
      loading: false,
    });
  } else if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED") {
    if (session.user && !store.user) {
      try {
        const userData = await authApi.getUserProfile(session.user.id);

        useAuthStore.setState({
          isAuthenticated: true,
          user: userData,
          loading: false,
        });
      } catch (error) {
        console.error("Failed to fetch user profile:", error);
      }
    }
  }
});
