// Mirrors app/schemas/*.py — kept intentionally minimal (only what the UI uses).

export interface User {
  id: string
  email: string
  name: string
  created_at: string
  updated_at: string
}

export interface UserInterest {
  name: string
  weight: number
  created_at: string
}

export type InteractionType = 'VIEW' | 'CLICK' | 'LIKE' | 'DISLIKE' | 'SAVE' | 'SKIP' | 'SHARE'

export interface RankFeatures {
  semantic: number
  freshness: number
  popularity: number
  source_quality: number
  diversity: number
  topic_affinity: number
}

export interface FeedItem {
  story_id: string
  canonical_title: string
  summary: string | null
  topics: string[]
  sources: string[]
  article_count: number
  published_at: string | null
  score: number
  primary_article_id: string
  primary_article_url: string
  features: RankFeatures | null
  contributions: Record<string, number> | null
}

export interface FeedResponse {
  items: FeedItem[]
  next_cursor: string | null
  cold_start: boolean
}

export interface StoryArticleRef {
  id: string
  title: string
  url: string
  source: string
  published_at: string | null
}

export interface StoryDetail {
  id: string
  canonical_title: string
  summary: string | null
  key_points: string[]
  topics: string[]
  created_at: string
  updated_at: string
  article_count: number
  sources: string[]
  articles: StoryArticleRef[]
}

export interface SourceReport {
  source: string
  fetched: number
  inserted: number
  duplicates: number
  invalid: number
  error: string | null
}

export interface IngestResult {
  status: 'completed' | 'queued'
  reports?: SourceReport[]
  task_id?: string
}
