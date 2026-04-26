import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Missing Supabase environment variables: NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY')
}

// Standard client for public/user interactions (Respects RLS)
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Admin client for backend operations (Bypasses RLS)
// Only use this in API routes or server-side scripts!
export const supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey || supabaseAnonKey)
