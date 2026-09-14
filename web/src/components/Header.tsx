import { useState } from 'react'
import { api, ApiError } from '../api/client'
import { useUser } from '../hooks/useUser'
import { Button } from './ui/Button'
import { Spinner } from './ui/Spinner'

interface HeaderProps {
  debug: boolean
  onToggleDebug: () => void
  onOpenInterests: () => void
  onRefresh: () => void
}

export function Header({ debug, onToggleDebug, onOpenInterests, onRefresh }: HeaderProps) {
  const { user, signOut } = useUser()
  const [ingesting, setIngesting] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

  const runIngest = async () => {
    setIngesting(true)
    setStatus(null)
    try {
      const result = await api.triggerIngest({ runSync: true })
      const inserted = (result.reports ?? []).reduce((sum, r) => sum + r.inserted, 0)
      setStatus(inserted > 0 ? `Pulled in ${inserted} new articles.` : 'No new articles found.')
      onRefresh()
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : 'Ingest failed.')
    } finally {
      setIngesting(false)
    }
  }

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-2xl items-center gap-3 px-4 py-3">
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-semibold text-slate-900">
            AI Personalized News Feed
          </h1>
          {user && <p className="truncate text-xs text-slate-500">{user.email}</p>}
        </div>

        <Button size="sm" onClick={onOpenInterests}>
          Interests
        </Button>
        <Button size="sm" active={debug} onClick={onToggleDebug}>
          Debug
        </Button>
        <Button size="sm" onClick={runIngest} disabled={ingesting}>
          {ingesting ? <Spinner className="h-4 w-4" /> : 'Ingest news'}
        </Button>
        <Button size="sm" variant="ghost" onClick={signOut}>
          Sign out
        </Button>
      </div>
      {status && (
        <div className="mx-auto max-w-2xl px-4 pb-2 text-xs text-slate-500">{status}</div>
      )}
    </header>
  )
}
