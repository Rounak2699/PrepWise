import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { ErrorNote } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/api'
import AuthLayout from './AuthLayout'
import { Field } from './Login'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setLoading(true)
    try {
      await register(name, email, password)
      navigate('/onboarding', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create your account. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Start your streak"
      subtitle="Two minutes to set up, then one daily test to stay sharp."
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field label="Full name" value={name} onChange={setName} autoFocus required />
        <Field label="Email" type="email" value={email} onChange={setEmail} required />
        <Field label="Password" type="password" value={password} onChange={setPassword} required minLength={8} />
        <ErrorNote>{error}</ErrorNote>
        <Button type="submit" size="lg" disabled={loading} className="mt-2">
          {loading ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
      <p className="text-sm text-ink-500 mt-6 text-center">
        Already have an account?{' '}
        <Link to="/login" className="text-ink-900 font-medium underline underline-offset-2">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
