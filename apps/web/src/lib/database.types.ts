export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      posts: {
        Row: {
          id: string
          created_at: string
          slug: string
          title: string
          tldr: string[] | null
          content: string | null
          excerpt: string | null
          cover_image: string | null
          is_published: boolean
          published_at: string | null
          source_url: Json | null
          ai_model: string | null
        }
        Insert: {
          id?: string
          created_at?: string
          slug: string
          title: string
          tldr?: string[] | null
          content?: string | null
          excerpt?: string | null
          cover_image?: string | null
          is_published?: boolean
          published_at?: string | null
          source_url?: Json | null
          ai_model?: string | null
        }
        Update: {
          id?: string
          created_at?: string
          slug?: string
          title?: string
          tldr?: string[] | null
          content?: string | null
          excerpt?: string | null
          cover_image?: string | null
          is_published?: boolean
          published_at?: string | null
          source_url?: Json | null
          ai_model?: string | null
        }
        Relationships: []
      }
      tags: {
        Row: {
          id: number
          created_at: string
          name: string
          slug: string
        }
        Insert: {
          id?: number
          created_at?: string
          name: string
          slug: string
        }
        Update: {
          id?: number
          created_at?: string
          name?: string
          slug?: string
        }
        Relationships: []
      }
      post_tags: {
        Row: {
          post_id: string
          tag_id: number
          created_at: string
        }
        Insert: {
          post_id: string
          tag_id: number
          created_at?: string
        }
        Update: {
          post_id?: string
          tag_id?: number
          created_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "post_tags_post_id_fkey"
            columns: ["post_id"]
            referencedRelation: "posts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "post_tags_tag_id_fkey"
            columns: ["tag_id"]
            referencedRelation: "tags"
            referencedColumns: ["id"]
          }
        ]
      }
      ai_generation_logs: {
        Row: {
          id: string
          created_at: string
          topic: string
          source_name: string | null
          source_url: string | null
          status: string
          selected_model: string | null
          failure_reason: string | null
          output_json: Json | null
          validated: boolean
        }
        Insert: {
          id?: string
          created_at?: string
          topic: string
          source_name?: string | null
          source_url?: string | null
          status: string
          selected_model?: string | null
          failure_reason?: string | null
          output_json?: Json | null
          validated?: boolean
        }
        Update: {
          id?: string
          created_at?: string
          topic?: string
          source_name?: string | null
          source_url?: string | null
          status?: string
          selected_model?: string | null
          failure_reason?: string | null
          output_json?: Json | null
          validated?: boolean
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
