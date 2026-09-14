import { useFeed } from '../hooks/useFeed'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Spinner } from './ui/Spinner'
import { StoryCard } from './StoryCard'

// Mount this with `key={refreshToken}` from the parent so a manual refresh
// (or a fresh ingest) remounts the component and its `useFeed` state cleanly,
// rather than threading an imperative "refetch" prop through.
export function FeedList({ userId, debug }: { userId: string; debug: boolean }) {
  const { items, coldStart, loading, loadingMore, error, hasMore, reactions, loadMore, react } =
    useFeed(userId, debug)

  if (loading && items.length === 0) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  if (error && items.length === 0) {
    return <p className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{error}</p>
  }

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">
        No stories yet. Trigger an ingest from the header to pull in some news.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {coldStart && (
        <Badge tone="slate">
          Showing recent stories — set some interests or like a few articles to personalize
          this
        </Badge>
      )}
      {items.map((item) => (
        <StoryCard
          key={item.story_id}
          item={item}
          activeReaction={reactions[item.story_id]}
          onReact={(type) => void react(item, type)}
          onRead={() => void react(item, 'CLICK')}
        />
      ))}
      {hasMore && (
        <div className="flex justify-center pt-2">
          <Button onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? <Spinner className="h-4 w-4" /> : 'Load more'}
          </Button>
        </div>
      )}
    </div>
  )
}
