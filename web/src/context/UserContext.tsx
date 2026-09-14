import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError } from '../api/client'
import type { User } from '../api/types'
import { STORAGE_KEY, UserContext } from './user-context'

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // On first load, re-hydrate whichever user id we last remembered — if the
  // backend no longer knows them (e.g. a fresh DB), fall back to onboarding
  // instead of getting stuck on a dead id.
  useEffect(() => {
    const storedId = localStorage.getItem(STORAGE_KEY)
    if (!storedId) {
      setLoading(false)
      return
    }
    api
      .getUser(storedId)
      .then(setUser)
      .catch(() => localStorage.removeItem(STORAGE_KEY))
      .finally(() => setLoading(false))
  }, [])

  const createAccount = async (email: string, name: string) => {
    setError(null)
    try {
      const created = await api.createUser(email, name)
      localStorage.setItem(STORAGE_KEY, created.id)
      setUser(created)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create your account.')
      throw err
    }
  }

  const signOut = () => {
    localStorage.removeItem(STORAGE_KEY)
    setUser(null)
  }

  const value = useMemo(
    () => ({ user, loading, error, createAccount, signOut }),
    [user, loading, error],
  )

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>
}
