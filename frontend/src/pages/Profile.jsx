import { Check } from 'lucide-react'
import { useState } from 'react'
import AppShell from '../components/AppShell'
import Button from '../components/Button'
import { Card, ErrorNote } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { api, ApiError } from '../lib/api'
import { ALL_TOPICS_BY_CATEGORY, topicLabel } from '../lib/taxonomy'

const YEARS = ['second-year', 'third-year', 'pre-final-year', 'final-year']
const DIFFICULTIES = ['easy', 'medium', 'hard', 'expert']

export default function Profile() {
  const { user, refreshUser } = useAuth()
  const [form, setForm] = useState({
    branch: user.branch || '',
    academic_year: user.academic_year || 'final-year',
    graduation_year: user.graduation_year || new Date().getFullYear() + 1,
    target_role: user.target_role || '',
    difficulty: user.preferences.difficulty,
    daily_question_count: user.preferences.daily_question_count,
    preferred_topics: user.preferences.preferred_topics,
  })
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
    setSaved(false)
  }

  function toggleTopic(t) {
    set('preferred_topics', form.preferred_topics.includes(t)
      ? form.preferred_topics.filter((x) => x !== t)
      : [...form.preferred_topics, t])
  }

  async function onSave() {
    setError('')
    setLoading(true)
    try {
      await api.updateMe({
        branch: form.branch || null,
        academic_year: form.academic_year,
        graduation_year: Number(form.graduation_year),
        target_role: form.target_role || null,
        preferences: {
          difficulty: form.difficulty,
          daily_question_count: Number(form.daily_question_count),
          preferred_topics: form.preferred_topics,
        },
      })
      await refreshUser()
      setSaved(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save changes.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl font-semibold text-ink-900 mb-1">Profile</h1>
      <p className="text-sm text-ink-500 mb-8">{user.name} · {user.email}</p>

      <Card className="p-6 mb-6">
        <h2 className="text-sm font-semibold text-ink-800 mb-4">Academic details</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <LabeledSelect label="Year" value={form.academic_year} onChange={(v) => set('academic_year', v)} options={YEARS.map((y) => ({ value: y, label: topicLabel(y) }))} />
          <LabeledInput label="Branch" value={form.branch} onChange={(v) => set('branch', v)} placeholder="e.g. CSE" />
          <LabeledInput label="Graduation year" type="number" value={form.graduation_year} onChange={(v) => set('graduation_year', v)} />
          <LabeledInput label="Target role" value={form.target_role} onChange={(v) => set('target_role', v)} placeholder="e.g. SDE" />
        </div>
      </Card>

      <Card className="p-6 mb-6">
        <h2 className="text-sm font-semibold text-ink-800 mb-4">Daily test preferences</h2>
        <div className="grid md:grid-cols-2 gap-4 mb-5">
          <LabeledSelect label="Difficulty" value={form.difficulty} onChange={(v) => set('difficulty', v)} options={DIFFICULTIES.map((d) => ({ value: d, label: topicLabel(d) }))} />
          <LabeledSelect
            label="Questions per day"
            value={String(form.daily_question_count)}
            onChange={(v) => set('daily_question_count', v)}
            options={[10, 11, 12, 13, 14, 15].map((n) => ({ value: String(n), label: `${n} questions` }))}
          />
        </div>
        <p className="text-xs font-medium text-ink-500 mb-2">Focus topics</p>
        {Object.entries(ALL_TOPICS_BY_CATEGORY).map(([group, list]) => (
          <div key={group} className="mb-3">
            <p className="text-xs font-medium text-ink-400 uppercase tracking-wide mb-2">{group}</p>
            <div className="flex flex-wrap gap-2">
              {list.map((t) => {
                const selected = form.preferred_topics.includes(t)
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleTopic(t)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                      selected ? 'border-amber-500 bg-amber-100 text-amber-600' : 'border-ink-200 text-ink-600 hover:border-ink-400'
                    }`}
                  >
                    {selected && <Check size={13} />}
                    {topicLabel(t)}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </Card>

      <ErrorNote>{error}</ErrorNote>
      <div className="flex items-center gap-3 mt-4">
        <Button onClick={onSave} disabled={loading}>{loading ? 'Saving…' : 'Save changes'}</Button>
        {saved && <span className="text-sm text-moss-600 flex items-center gap-1"><Check size={15} /> Saved</span>}
      </div>
    </AppShell>
  )
}

function LabeledInput({ label, value, onChange, ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs text-ink-500">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2 rounded-lg border border-ink-200 bg-paper-50 text-sm focus:outline-none focus:ring-2 focus:ring-ink-800/20"
        {...props}
      />
    </label>
  )
}

function LabeledSelect({ label, value, onChange, options }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs text-ink-500">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2 rounded-lg border border-ink-200 bg-paper-50 text-sm focus:outline-none focus:ring-2 focus:ring-ink-800/20"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  )
}
