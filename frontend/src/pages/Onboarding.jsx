import { Check } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { ErrorNote } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { api, ApiError } from '../lib/api'
import { ALL_TOPICS_BY_CATEGORY, topicLabel } from '../lib/taxonomy'

const YEARS = [
  { value: 'second-year', label: 'Second year' },
  { value: 'third-year', label: 'Third year' },
  { value: 'pre-final-year', label: 'Pre-final year' },
  { value: 'final-year', label: 'Final year' },
]

const DIFFICULTIES = [
  { value: 'easy', label: 'Just starting out' },
  { value: 'medium', label: 'Comfortable with basics' },
  { value: 'hard', label: 'Preparing seriously' },
  { value: 'expert', label: 'Interview-ready, sharpening' },
]

export default function Onboarding() {
  const { refreshUser } = useAuth()
  const navigate = useNavigate()
  const [branch, setBranch] = useState('')
  const [academicYear, setAcademicYear] = useState('final-year')
  const [graduationYear, setGraduationYear] = useState(new Date().getFullYear() + 1)
  const [targetRole, setTargetRole] = useState('')
  const [difficulty, setDifficulty] = useState('medium')
  const [topics, setTopics] = useState(['dsa', 'quantitative'])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function toggleTopic(t) {
    setTopics((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]))
  }

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    if (topics.length === 0) {
      setError('Pick at least one topic so we can build your daily test.')
      return
    }
    setLoading(true)
    try {
      await api.updateMe({
        academic_year: academicYear,
        branch: branch || null,
        graduation_year: Number(graduationYear),
        target_role: targetRole || null,
        preferences: { difficulty, preferred_topics: topics },
      })
      await refreshUser()
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save your preferences.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-paper-100 flex items-center justify-center p-6">
      <div className="w-full max-w-xl rise-in">
        <p className="text-xs font-medium text-amber-600 mb-2">Step 1 of 1</p>
        <h1 className="font-display text-3xl font-semibold text-ink-900 mb-2">Set up your prep</h1>
        <p className="text-sm text-ink-500 mb-8">
          This tunes your daily test — you can change it anytime from your profile.
        </p>

        <form onSubmit={onSubmit} className="flex flex-col gap-8">
          <section>
            <h2 className="text-sm font-semibold text-ink-800 mb-3">Where are you in college?</h2>
            <div className="grid grid-cols-2 gap-2">
              {YEARS.map((y) => (
                <ChoiceCard key={y.value} selected={academicYear === y.value} onClick={() => setAcademicYear(y.value)}>
                  {y.label}
                </ChoiceCard>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-3 mt-3">
              <label className="flex flex-col gap-1.5">
                <span className="text-xs text-ink-500">Branch (optional)</span>
                <input
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="e.g. CSE"
                  className="px-3 py-2 rounded-lg border border-ink-200 bg-paper-50 text-sm focus:outline-none focus:ring-2 focus:ring-ink-800/20"
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs text-ink-500">Graduation year</span>
                <input
                  type="number"
                  value={graduationYear}
                  onChange={(e) => setGraduationYear(e.target.value)}
                  min={2020}
                  max={2040}
                  className="px-3 py-2 rounded-lg border border-ink-200 bg-paper-50 text-sm focus:outline-none focus:ring-2 focus:ring-ink-800/20"
                />
              </label>
            </div>
            <label className="flex flex-col gap-1.5 mt-3">
              <span className="text-xs text-ink-500">Target role (optional)</span>
              <input
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. SDE, Data Analyst"
                className="px-3 py-2 rounded-lg border border-ink-200 bg-paper-50 text-sm focus:outline-none focus:ring-2 focus:ring-ink-800/20"
              />
            </label>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-ink-800 mb-3">How would you rate your current level?</h2>
            <div className="grid grid-cols-2 gap-2">
              {DIFFICULTIES.map((d) => (
                <ChoiceCard key={d.value} selected={difficulty === d.value} onClick={() => setDifficulty(d.value)}>
                  {d.label}
                </ChoiceCard>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-ink-800 mb-1">Which topics should we focus on?</h2>
            <p className="text-xs text-ink-500 mb-3">Pick as many as you like — we'll weight your daily test toward these.</p>
            {Object.entries(ALL_TOPICS_BY_CATEGORY).map(([group, list]) => (
              <div key={group} className="mb-3">
                <p className="text-xs font-medium text-ink-400 uppercase tracking-wide mb-2">{group}</p>
                <div className="flex flex-wrap gap-2">
                  {list.map((t) => (
                    <TopicChip key={t} selected={topics.includes(t)} onClick={() => toggleTopic(t)}>
                      {topicLabel(t)}
                    </TopicChip>
                  ))}
                </div>
              </div>
            ))}
          </section>

          <ErrorNote>{error}</ErrorNote>

          <Button type="submit" size="lg" disabled={loading}>
            {loading ? 'Saving…' : 'Start my streak'}
          </Button>
        </form>
      </div>
    </div>
  )
}

function ChoiceCard({ selected, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-left px-3.5 py-2.5 rounded-xl border text-sm font-medium transition-colors ${
        selected ? 'border-ink-900 bg-ink-900 text-paper-50' : 'border-ink-200 bg-paper-50 text-ink-700 hover:border-ink-400'
      }`}
    >
      {children}
    </button>
  )
}

function TopicChip({ selected, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
        selected ? 'border-amber-500 bg-amber-100 text-amber-600' : 'border-ink-200 text-ink-600 hover:border-ink-400'
      }`}
    >
      {selected && <Check size={13} />}
      {children}
    </button>
  )
}
