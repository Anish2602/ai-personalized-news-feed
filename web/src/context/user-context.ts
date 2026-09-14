import { createContext } from 'react'
import type { User } from '../api/types'

export const STORAGE_KEY = 'newsfeed.userId'

export interface UserContextValue {
  user: User | null
  loading: boolean
  error: string | null
  createAccount: (email: string, name: string) => Promise<void>
  signOut: () => void
}

export const UserContext = createContext<UserContextValue | null>(null)
