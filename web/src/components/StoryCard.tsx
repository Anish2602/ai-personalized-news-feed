import { useState } from 'react'
import type { FeedItem, InteractionType } from '../api/types'
import { relativeTime } from '../lib/time'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'

const REACTIONS: { type: InteractionType; label: string; icon: string }[] = [
  { type: 'LIKE', label: 'Like', icon: '\u{1F44D}' },
  { type: 'DISLIKE', label: 'Dislike', icon: '\u{1F44E}' },
  { type: 'SAVE', label: 'Save', icon: '\u{1F516}' },
  { type: 'SKIP', label: 'Skip', icon: '\u{23ED}' },
]

const FEATURE_LABELS: Record<string, string> = {
  semantic: 'Semantic match',
  freshness: 'Freshness',
  popularity: 'Popularity',
  source_quality: 'Source quality',
  diversity: 'Diversity',
}

interface StoryCardProps {
  item: FeedItem
  activeReaction?: InteractionType
  onReact: (type: InteractionType) => void
  onRead: () => void
}

export function StoryCard({ item, activeReaction, onReact, onRead }: StoryCardProps) {
  const [showBreakdown, setShowBreakdown] = useState(false)

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex flex-wrap items-center gap-2">
        {item.topics.map((topic) => (
          <Badge key={topic} tone="indigo">
            {topic}
          </Badge>
        ))}
        {item.article_count > 1 && (
          <Badge tone="emerald">{item.article_count} sources covering this</Badge>
        )}
        <span className="ml-auto text-xs font-medium text-slate-400" title="Ranking score">
          {(item.score * 100).toFixed(0)}
        </span>
      </div>

      <h2 className="mt-3 text-lg font-semibold leading-snug text-slate-900">
        {item.canonical_title}
      </h2>

      {item.summary && (
        <p className="mt-2 line-clamp-4 text-sm leading-relaxed text-slate-600">{item.summary}</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-400">
        <span>{item.sources.join(', ')}</span>
        <span aria-hidden>&middot;</span>
        <span>{relativeTime(item.published_at)}</span>
      </div>

      {item.features && (
        <div className="mt-3">
          <button
            onClick={() => setShowBreakdown((v) => !v)}
            className="text-xs font-medium text-indigo-600 hover:text-indigo-500"
          >
            {showBreakdown ? 'Hide' : 'Why am I seeing this?'}
          </button>
          {showBreakdown && (
            <dl className="mt-2 space-y-1 rounded-lg bg-slate-50 p-3">
              {Object.entries(item.features).map(([key, value]) => (
                <div key={key} className="flex items-center gap-2 text-xs">
                  <dt className="w-28 shrink-0 text-slate-500">{FEATURE_LABELS[key] ?? key}</dt>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-indigo-400"
                      style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}
                    />
                  </div>
                  <dd className="w-10 text-right font-mono text-slate-500">
                    {value.toFixed(2)}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
        {REACTIONS.map(({ type, label, icon }) => (
          <Button
            key={type}
            size="sm"
            variant={type === 'DISLIKE' ? 'danger' : 'secondary'}
            active={activeReaction === type}
            onClick={() => onReact(type)}
          >
            <span aria-hidden>{icon}</span>
            {label}
          </Button>
        ))}
        <a
          href={item.primary_article_url}
          target="_blank"
          rel="noreferrer"
          onClick={onRead}
          className="ml-auto text-sm font-medium text-indigo-600 hover:text-indigo-500"
        >
          Read full story &rarr;
        </a>
      </div>
    </article>
  )
}
