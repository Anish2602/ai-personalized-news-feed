import { useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { UserInterest } from '../api/types'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Spinner } from './ui/Spinner'

export function InterestsPanel({ userId, onClose }: { userId: string; onClose: () => void }) {
  const [interests, setInterests] = useState<UserInterest[]>([])
  const [taxonomy, setTaxonomy] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [newInterest, setNewInterest] = useState('')
  const [saving, setSaving] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.listInterests(userId), api.getTaxonomy()])
      .then(([userInterests, { topics }]) => {
        setInterests(userInterests)
        setTaxonomy(topics)
      })
      .catch(() => setError('Could not load interests.'))
      .finally(() => setLoading(false))
  }, [userId])

  const addInterest = async (name: string, weight = 2) => {
    const trimmed = name.trim()
    if (!trimmed) return
    setSaving(trimmed)
    setError(null)
    try {
      const updated = await api.assignInterests(userId, [{ name: trimmed, weight }])
      setInterests(updated)
      setNewInterest('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save that interest.')
    } finally {
      setSaving(null)
    }
  }

  const removeInterest = async (name: string) => {
    setSaving(name)
    setError(null)
    try {
      await api.removeInterest(userId, name)
      setInterests((prev) => prev.filter((i) => i.name !== name))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not remove that interest.')
    } finally {
      setSaving(null)
    }
  }

  const activeNames = new Set(interests.map((i) => i.name))
  const suggestions = taxonomy.filter((t) => !activeNames.has(t))

  return (
    <div className="fixed inset-0 z-20 flex items-start justify-center bg-slate-900/30 px-4 pt-24">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">Your interests</h2>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          Interests directly boost matching stories in your feed (see "Interest match" under
          Debug) — on top of what you like, save, or skip.
        </p>

        <p className="mt-4 text-xs font-medium text-slate-700">Active</p>
        <div className="mt-1.5 flex min-h-8 flex-wrap gap-2">
          {loading ? (
            <Spinner className="h-4 w-4" />
          ) : interests.length === 0 ? (
            <span className="text-sm text-slate-400">None yet — pick a topic below.</span>
          ) : (
            interests.map((i) => (
              <Badge key={i.name} tone="indigo">
                <span className="inline-flex items-center gap-1">
                  {i.name}
                  <button
                    onClick={() => removeInterest(i.name)}
                    disabled={saving !== null}
                    aria-label={`Remove ${i.name}`}
                    className="text-indigo-500 hover:text-indigo-800 disabled:opacity-50"
                  >
                    {saving === i.name ? '…' : '✕'}
                  </button>
                </span>
              </Badge>
            ))
          )}
        </div>

        {!loading && suggestions.length > 0 && (
          <>
            <p className="mt-4 text-xs font-medium text-slate-700">
              Topics (only these can match a story)
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {suggestions.map((topic) => (
                <button
                  key={topic}
                  onClick={() => addInterest(topic)}
                  disabled={saving !== null}
                  className="rounded-full border border-slate-200 px-2.5 py-0.5 text-xs text-slate-600 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 disabled:opacity-50"
                >
                  {saving === topic ? '…' : `+ ${topic}`}
                </button>
              ))}
            </div>
          </>
        )}

        <p className="mt-4 text-xs font-medium text-slate-700">Or type your own</p>
        <div className="mt-1.5 flex gap-2">
          <input
            value={newInterest}
            onChange={(e) => setNewInterest(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addInterest(newInterest)}
            placeholder="won't affect ranking unless it matches a topic above"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          <Button
            variant="primary"
            size="sm"
            onClick={() => addInterest(newInterest)}
            disabled={saving !== null}
          >
            Add
          </Button>
        </div>
        {error && <p className="mt-2 text-xs text-rose-600">{error}</p>}
      </div>
    </div>
  )
}
