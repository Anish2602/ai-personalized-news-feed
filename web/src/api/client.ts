import type {
  FeedResponse,
  IngestResult,
  InteractionType,
  StoryDetail,
  User,
  UserInterest,
} from './types'

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  userId?: string
  params?: Record<string, string | number | boolean | undefined>
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`)
  for (const [key, value] of Object.entries(opts.params ?? {})) {
    if (value !== undefined) url.searchParams.set(key, String(value))
  }

  const headers: Record<string, string> = {}
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  if (opts.userId) headers['X-User-Id'] = opts.userId

  const res = await fetch(url, {
    method: opts.method ?? 'GET',
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  })

  if (!res.ok) {
    let code = 'unknown_error'
    let message = `Request failed with status ${res.status}`
    try {
      const payload = (await res.json()) as { error?: { code?: string; message?: string } }
      code = payload.error?.code ?? code
      message = payload.error?.message ?? message
    } catch {
      // response wasn't JSON — fall back to the generic message above
    }
    throw new ApiError(res.status, code, message)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  createUser: (email: string, name: string) =>
    request<User>('/users', { method: 'POST', body: { email, name } }),

  getUser: (userId: string) => request<User>(`/users/${userId}`),

  listInterests: (userId: string) => request<UserInterest[]>(`/users/${userId}/interests`),

  assignInterests: (userId: string, items: { name: string; weight: number }[]) =>
    request<UserInterest[]>(`/users/${userId}/interests`, { method: 'POST', body: { items } }),

  getFeed: (
    userId: string,
    opts: { cursor?: string | null; limit?: number; debug?: boolean } = {},
  ) =>
    request<FeedResponse>('/feed', {
      userId,
      params: {
        limit: opts.limit ?? 10,
        cursor: opts.cursor ?? undefined,
        debug: opts.debug ?? undefined,
      },
    }),

  getStory: (storyId: string) => request<StoryDetail>(`/stories/${storyId}`),

  recordInteraction: (userId: string, articleId: string, type: InteractionType) =>
    request(`/interactions`, {
      method: 'POST',
      body: { user_id: userId, article_id: articleId, interaction_type: type },
    }),

  triggerIngest: (opts: { feeds?: string[]; runSync?: boolean } = {}) =>
    request<IngestResult>('/admin/ingest', {
      method: 'POST',
      body: { feeds: opts.feeds, run_sync: opts.runSync ?? false },
    }),
}
