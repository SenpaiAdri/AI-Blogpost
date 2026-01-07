export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Post {
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
  source_url: Source[] | null
  ai_model: string | null
  tags?: Tag[]
}

export interface Source {
  name: string
  url: string
}

export interface Tag {
  id: number
  name: string
  slug: string
}
