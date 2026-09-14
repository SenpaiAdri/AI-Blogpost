export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      ai_generation_logs: {
        Row: {
          created_at: string
          failure_reason: string | null
          id: string
          output_json: Json | null
          selected_model: string | null
          source_name: string
          source_url: string
          status: string
          topic: string
          validated: boolean
        }
        Insert: {
          created_at?: string
          failure_reason?: string | null
          id?: string
          output_json?: Json | null
          selected_model?: string | null
          source_name: string
          source_url: string
          status: string
          topic: string
          validated?: boolean
        }
        Update: {
          created_at?: string
          failure_reason?: string | null
          id?: string
          output_json?: Json | null
          selected_model?: string | null
          source_name?: string
          source_url?: string
          status?: string
          topic?: string
          validated?: boolean
        }
        Relationships: []
      }
      comments: {
        Row: {
          ai_model: string | null
          author_name: string | null
          author_type: string
          author_user_id: string | null
          body: string
          created_at: string
          id: string
          moderated_at: string | null
          moderated_by: string | null
          parent_id: string | null
          post_id: string
          status: string
        }
        Insert: {
          ai_model?: string | null
          author_name?: string | null
          author_type: string
          author_user_id?: string | null
          body: string
          created_at?: string
          id?: string
          moderated_at?: string | null
          moderated_by?: string | null
          parent_id?: string | null
          post_id: string
          status?: string
        }
        Update: {
          ai_model?: string | null
          author_name?: string | null
          author_type?: string
          author_user_id?: string | null
          body?: string
          created_at?: string
          id?: string
          moderated_at?: string | null
          moderated_by?: string | null
          parent_id?: string | null
          post_id?: string
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "comments_parent_id_fkey"
            columns: ["parent_id"]
            isOneToOne: false
            referencedRelation: "comments"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "comments_post_id_fkey"
            columns: ["post_id"]
            isOneToOne: false
            referencedRelation: "posts"
            referencedColumns: ["id"]
          },
        ]
      }
      post_moderation_events: {
        Row: {
          action: string
          created_at: string
          created_by: string
          id: string
          new_is_published: boolean
          post_id: string
          previous_is_published: boolean
          reason: string | null
        }
        Insert: {
          action: string
          created_at?: string
          created_by: string
          id?: string
          new_is_published: boolean
          post_id: string
          previous_is_published: boolean
          reason?: string | null
        }
        Update: {
          action?: string
          created_at?: string
          created_by?: string
          id?: string
          new_is_published?: boolean
          post_id?: string
          previous_is_published?: boolean
          reason?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "post_moderation_events_post_id_fkey"
            columns: ["post_id"]
            isOneToOne: false
            referencedRelation: "posts"
            referencedColumns: ["id"]
          },
        ]
      }
      post_tags: {
        Row: {
          post_id: string
          tag_id: number
        }
        Insert: {
          post_id: string
          tag_id: number
        }
        Update: {
          post_id?: string
          tag_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "post_tags_post_id_fkey"
            columns: ["post_id"]
            isOneToOne: false
            referencedRelation: "posts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "post_tags_tag_id_fkey"
            columns: ["tag_id"]
            isOneToOne: false
            referencedRelation: "tags"
            referencedColumns: ["id"]
          },
        ]
      }
      posts: {
        Row: {
          ai_model: string | null
          content: string | null
          cover_image: string | null
          created_at: string
          excerpt: string | null
          id: string
          is_published: boolean | null
          published_at: string | null
          slug: string
          source_url: Json | null
          title: string
          tldr: Json | null
          updated_at: string
        }
        Insert: {
          ai_model?: string | null
          content?: string | null
          cover_image?: string | null
          created_at?: string
          excerpt?: string | null
          id?: string
          is_published?: boolean | null
          published_at?: string | null
          slug: string
          source_url?: Json | null
          title: string
          tldr?: Json | null
          updated_at?: string
        }
        Update: {
          ai_model?: string | null
          content?: string | null
          cover_image?: string | null
          created_at?: string
          excerpt?: string | null
          id?: string
          is_published?: boolean | null
          published_at?: string | null
          slug?: string
          source_url?: Json | null
          title?: string
          tldr?: Json | null
          updated_at?: string
        }
        Relationships: []
      }
      rss_sources: {
        Row: {
          created_at: string
          error_count: number | null
          id: string
          is_active: boolean
          last_fetched_at: string | null
          name: string
          url: string
        }
        Insert: {
          created_at?: string
          error_count?: number | null
          id?: string
          is_active?: boolean
          last_fetched_at?: string | null
          name: string
          url: string
        }
        Update: {
          created_at?: string
          error_count?: number | null
          id?: string
          is_active?: boolean
          last_fetched_at?: string | null
          name?: string
          url?: string
        }
        Relationships: []
      }
      tags: {
        Row: {
          id: number
          name: string
          slug: string
        }
        Insert: {
          id?: number
          name: string
          slug: string
        }
        Update: {
          id?: number
          name?: string
          slug?: string
        }
        Relationships: []
      }
      topic_guidance: {
        Row: {
          created_at: string
          created_by: string
          deactivated_at: string | null
          deactivated_by: string | null
          expires_at: string
          id: string
          keyword: string
          normalized_keyword: string
          status: string
          weight: number
        }
        Insert: {
          created_at?: string
          created_by: string
          deactivated_at?: string | null
          deactivated_by?: string | null
          expires_at: string
          id?: string
          keyword: string
          normalized_keyword: string
          status?: string
          weight?: number
        }
        Update: {
          created_at?: string
          created_by?: string
          deactivated_at?: string | null
          deactivated_by?: string | null
          expires_at?: string
          id?: string
          keyword?: string
          normalized_keyword?: string
          status?: string
          weight?: number
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
