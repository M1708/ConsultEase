// // frontend/lib/supabase.ts
// import { createClient } from "@supabase/supabase-js";

// const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
// const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

// if (!supabaseUrl || !supabaseAnonKey) {
//   throw new Error("Missing Supabase environment variables");
// }

// console.log("Creating Supabase client with:", {
//   supabaseUrl,
//   hasKey: !!supabaseAnonKey,
// });

// console.log("Supabase URL:", supabaseUrl);
// console.log("Supabase Anon Key:", supabaseAnonKey ? "Present" : "Missing");

// export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
//   auth: {
//     autoRefreshToken: true,
//     persistSession: true,
//     detectSessionInUrl: false, // Changed from true to false
//   },
//   global: {
//     headers: {
//       "X-Client-Info": "consultease-frontend",
//     },
//   },
// });

// console.log("Supabase client created, testing connection...");

// console.log("Supabase client created:", supabase);

// // Types for Supabase Auth
// export type AuthUser = {
//   id: string;
//   email: string;
//   email_confirmed_at: string | null;
//   last_sign_in_at: string | null;
// };

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

// Configuration for middleware compatibility
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true, // Enable for middleware
    autoRefreshToken: true, // Enable for session management
    detectSessionInUrl: false,
  },
});

console.log("Fresh Supabase client created");
