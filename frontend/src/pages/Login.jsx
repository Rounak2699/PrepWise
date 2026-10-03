import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { ErrorNote } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/api'
import AuthLayout from './AuthLayout'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate(location.state?.from || '/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not log in. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Pick up your streak where you left off."
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field label="Email" type="email" value={email} onChange={setEmail} autoFocus required />
        <Field label="Password" type="password" value={password} onChange={setPassword} required />
        <ErrorNote>{error}</ErrorNote>
        <Button type="submit" size="lg" disabled={loading} className="mt-2">
          {loading ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
      <p className="text-sm text-ink-500 mt-6 text-center">
        New here?{' '}
        <Link to="/register" className="text-ink-900 font-medium underline underline-offset-2">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  )
}

export function Field({ label, type = 'text', value, onChange, ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-ink-700">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3.5 py-2.5 rounded-xl border border-ink-200 bg-paper-50 text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-2 focus:ring-ink-800/20 focus:border-ink-500 transition"
        {...props}
      />
    </label>
  )
}
