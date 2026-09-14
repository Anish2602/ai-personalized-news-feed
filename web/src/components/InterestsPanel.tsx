import { useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { UserInterest } from '../api/types'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Spinner } from './ui/Spinner'

export function InterestsPanel({ userId, onClose }: { userId: string; onClose: () => void }) {
  const [interests, setInterests] = useState<UserInterest[]>([])
  const [loading, setLoading] = useState(true)
  const [newInterest, setNewInterest] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listInterests(userId)
      .then(setInterests)
      .catch(() => setError('Could not load interests.'))
      .finally(() => setLoading(false))
  }, [userId])

  const addInterest = async () => {
    const name = newInterest.trim()
    if (!name) return
    setSaving(true)
    setError(null)
    try {
      const updated = await api.assignInterests(userId, [{ name, weight: 2 }])
      setInterests(updated)
      setNewInterest('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save that interest.')
    } finally {
      setSaving(false)
    }
  }

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
          Interests seed the topic column; your ranked feed is mostly driven by what you like,
          save, or skip.
        </p>

        <div className="mt-4 flex min-h-8 flex-wrap gap-2">
          {loading ? (
            <Spinner className="h-4 w-4" />
          ) : interests.length === 0 ? (
            <span className="text-sm text-slate-400">No interests yet.</span>
          ) : (
            interests.map((i) => (
              <Badge key={i.name} tone="indigo">
                {i.name}
              </Badge>
            ))
          )}
        </div>

        <div className="mt-4 flex gap-2">
          <input
            value={newInterest}
            onChange={(e) => setNewInterest(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addInterest()}
            placeholder="e.g. Cloud, Cybersecurity"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          <Button variant="primary" size="sm" onClick={addInterest} disabled={saving}>
            Add
          </Button>
        </div>
        {error && <p className="mt-2 text-xs text-rose-600">{error}</p>}
      </div>
    </div>
  )
}
