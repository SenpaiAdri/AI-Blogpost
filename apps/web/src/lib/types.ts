import type { Database, Json } from './database.types'

export type { Json }

// Extract the row types directly from the generated schema
export type Post = Omit<Database['public']['Tables']['posts']['Row'], 'source_url'> & {
  // Override source_url back to Source[] instead of generic Json
  source_url: Source[] | null
  // Adding the optional relation that components expect
  tags?: Tag[]
}

export type Tag = Database['public']['Tables']['tags']['Row']

export interface PostRow extends Omit<Post, 'tags'> {
  post_tags: {
    tags: Tag
  }[] | null
}

export interface Source {
  name: string
  url: string
}

