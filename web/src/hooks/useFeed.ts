import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { FeedItem, InteractionType } from '../api/types'

const PAGE_SIZE = 10

export function useFeed(userId: string | null, debug: boolean) {
  const [items, setItems] = useState<FeedItem[]>([])
  const [coldStart, setColdStart] = useState(false)
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // story_id -> the interaction the viewer just fired, for optimistic button state
  const [reactions, setReactions] = useState<Record<string, InteractionType>>({})

  const load = useCallback(
    async (opts: { append: boolean; cursor?: string | null }) => {
      if (!userId) return
      if (opts.append) setLoadingMore(true)
      else setLoading(true)
      setError(null)
      try {
        const page = await api.getFeed(userId, { cursor: opts.cursor, limit: PAGE_SIZE, debug })
        setItems((prev) => (opts.append ? [...prev, ...page.items] : page.items))
        setCursor(page.next_cursor)
        setColdStart(page.cold_start)
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Could not load the feed.')
      } finally {
        if (opts.append) setLoadingMore(false)
        else setLoading(false)
      }
    },
    [userId, debug],
  )

  useEffect(() => {
    setReactions({})
    void load({ append: false, cursor: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, debug])

  const loadMore = useCallback(() => {
    if (cursor) void load({ append: true, cursor })
  }, [cursor, load])

  const refresh = useCallback(() => {
    setReactions({})
    void load({ append: false, cursor: null })
  }, [load])

  const react = useCallback(
    async (item: FeedItem, type: InteractionType) => {
      if (!userId) return
      setReactions((prev) => ({ ...prev, [item.story_id]: type }))
      try {
        await api.recordInteraction(userId, item.primary_article_id, type)
      } catch {
        // Revert the optimistic mark if the write didn't actually happen.
        setReactions((prev) => {
          const next = { ...prev }
          delete next[item.story_id]
          return next
        })
      }
    },
    [userId],
  )

  return {
    items,
    coldStart,
    loading,
    loadingMore,
    error,
    hasMore: cursor !== null,
    reactions,
    loadMore,
    refresh,
    react,
  }
}
