import { useState } from 'react'
import type { FormEvent } from 'react'
import { useUser } from '../hooks/useUser'
import { Button } from './ui/Button'
import { Spinner } from './ui/Spinner'

export function Onboarding() {
  const { createAccount, error } = useUser()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await createAccount(email.trim(), name.trim())
    } catch {
      // surfaced via `error` from context
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">AI Personalized News Feed</h1>
        <p className="mt-1 text-sm text-slate-500">
          Create a reader profile to get a feed ranked just for you.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-slate-700">
              Name
            </label>
            <input
              id="name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ada Lovelace"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ada@example.com"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {error && <p className="text-sm text-rose-600">{error}</p>}

          <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
            {submitting ? <Spinner className="h-4 w-4 text-white" /> : 'Get my feed'}
          </Button>
        </form>
      </div>
    </div>
  )
}
