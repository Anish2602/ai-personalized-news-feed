import { useState } from 'react'
import { FeedList } from './components/FeedList'
import { Header } from './components/Header'
import { InterestsPanel } from './components/InterestsPanel'
import { Onboarding } from './components/Onboarding'
import { UserProvider } from './context/UserContext'
import { useUser } from './hooks/useUser'
import { Spinner } from './components/ui/Spinner'

function Shell() {
  const { user, loading } = useUser()
  const [debug, setDebug] = useState(false)
  const [interestsOpen, setInterestsOpen] = useState(false)
  const [refreshToken, setRefreshToken] = useState(0)

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  if (!user) return <Onboarding />

  return (
    <div className="min-h-screen bg-slate-50">
      <Header
        debug={debug}
        onToggleDebug={() => setDebug((v) => !v)}
        onOpenInterests={() => setInterestsOpen(true)}
        onRefresh={() => setRefreshToken((n) => n + 1)}
      />
      <main className="mx-auto max-w-2xl px-4 py-6">
        <FeedList key={refreshToken} userId={user.id} debug={debug} />
      </main>
      {interestsOpen && (
        <InterestsPanel userId={user.id} onClose={() => setInterestsOpen(false)} />
      )}
    </div>
  )
}

export default function App() {
  return (
    <UserProvider>
      <Shell />
    </UserProvider>
  )
}
