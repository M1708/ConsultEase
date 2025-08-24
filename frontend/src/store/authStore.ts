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

      //console.log("B. Calling Supabase auth");

      // Use Supabase client for proper session management
      const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authError) {
        throw new Error(authError.message || "Authentication failed");
      }

      if (!authData.user || !authData.session) {
        throw new Error("No user or session returned from authentication");
      }

      localStorage.setItem("supabase_token", authData.session.access_token);

      console.log("Supabase auth successful, session created automatically");

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

      // Run session and last login updates in parallel (non-blocking)
      Promise.all([
        redisSessionManager.getSession(authData.session.access_token).then(sessionData => {
          if (sessionData) {
            console.log("F3. Setting session ID:", sessionData.sessionId);
            set((state) => ({ ...state, sessionId: sessionData.sessionId }));
          }
        }),
        authApi.updateLastLogin(userData.user_id)
      ]).catch(error => {
        console.warn("Non-critical post-login operations failed:", error);
        // Don't fail the login for these secondary operations
      });
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

      // Get token from localStorage
      const token = localStorage.getItem("supabase_token");

      // Clear localStorage immediately for faster UI response
      localStorage.removeItem("supabase_token");

      // Update UI state immediately for instant feedback
      set({
        isAuthenticated: false,
        user: null,
        sessionId: null,
        loading: false,
        error: null,
      });

      // Run cleanup operations in parallel (non-blocking)
      Promise.all([
        // Invalidate Redis session (non-blocking)
        token ? redisSessionManager.invalidateSession(token).catch(err => 
          console.warn("Redis session invalidation failed:", err)
        ) : Promise.resolve(),
        
        // Clear Supabase session (non-blocking)
        supabase.auth.signOut().catch(err => 
          console.warn("Supabase signOut failed:", err)
        )
      ]).catch(error => {
        console.warn("Non-critical logout cleanup failed:", error);
        // Don't fail the logout for these secondary operations
      });

    } catch (error) {
      console.error("Logout failed:", error);
      set({ loading: false });
    }
  },

  initialize: async () => {
    try {
      console.log("INIT: Starting initialization");

      // Skip initialization if already authenticated or already loading
      const currentState = get();
      if (currentState.isAuthenticated && currentState.user) {
        console.log("INIT: Already authenticated, skipping");
        return;
      }
      
      if (currentState.loading) {
        console.log("INIT: Already loading, skipping");
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
