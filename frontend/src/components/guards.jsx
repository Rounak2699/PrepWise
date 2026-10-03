import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { FullPageSpinner } from './ui'

export function RequireAuth({ children, requireOnboarded = true }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <FullPageSpinner />
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (requireOnboarded && !user.onboarded) return <Navigate to="/onboarding" replace />
  return children
}

export function RedirectIfAuthed({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <FullPageSpinner />
  if (user) return <Navigate to={user.onboarded ? '/' : '/onboarding'} replace />
  return children
}
