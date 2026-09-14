import type { Database, Json } from './database.types'

export type { Json }

// Extract the row types directly from the generated schema
export type Post = Omit<Database['public']['Tables']['posts']['Row'], 'source_url' | 'tldr'> & {
  // Override source_url back to Source[] instead of generic Json
  source_url: Source[] | null
  // tldr is jsonb in the DB but always a string array in practice
  // (see PostInsertModel in the ingest worker); keep the narrowed type
  // so components don't need Json guards.
  tldr: string[] | null
  // Adding the optional relation that components expect
  tags?: Tag[]
}

export type Tag = Database['public']['Tables']['tags']['Row']

export type Comment = Database['public']['Tables']['comments']['Row']

export type CommentAuthorType = 'human' | 'ai' | 'anonymous'

export type CommentStatus = 'pending' | 'approved' | 'rejected' | 'spam'

export interface PostRow extends Omit<Post, 'tags'> {
  post_tags: {
    tags: Tag
  }[] | null
}

export interface Source {
  name: string
  url: string
}

