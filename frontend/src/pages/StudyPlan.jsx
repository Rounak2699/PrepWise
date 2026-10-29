import { useEffect, useState } from 'react'
import { Check, RefreshCw } from 'lucide-react'
import AppShell from '../components/AppShell'
import Button from '../components/Button'
import { Card, ErrorNote, FullPageSpinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { api, ApiError } from '../lib/api'
import { ALL_TOPICS_BY_CATEGORY, topicLabel } from '../lib/taxonomy'

export default function StudyPlan() {
  const { user } = useAuth()
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [editMinutes, setEditMinutes] = useState('60')
  const [form, setForm] = useState({
    goal: 'General placement',
    target_role: user?.target_role || 'Software Developer',
    daily_minutes: '60',
    duration_days: '30',
    preferred_days: 'daily',
    current_level: 'intermediate',
    target_topics: user?.preferences?.preferred_topics || [],
  })

  async function loadPlan() {
    try {
      setPlan(await api.currentStudyPlan())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load your study plan.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    api.currentStudyPlan()
      .then((currentPlan) => {
        if (active) {
          setPlan(currentPlan)
          if (currentPlan) setEditMinutes(String(currentPlan.daily_minutes))
        }
      })
      .catch((err) => {
        if (active) setError(err instanceof ApiError ? err.message : 'Could not load your study plan.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  function toggleTopic(topic) {
    update('target_topics', form.target_topics.includes(topic)
      ? form.target_topics.filter((item) => item !== topic)
      : [...form.target_topics, topic])
  }

  async function createPlan(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const created = await api.createStudyPlan({
        ...form,
        daily_minutes: Number(form.daily_minutes),
        duration_days: Number(form.duration_days),
      })
      setPlan(created)
      setEditMinutes(String(created.daily_minutes))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create your study plan.')
    } finally {
      setSaving(false)
    }
  }

  async function updatePlan(payload) {
    setError('')
    try {
      setPlan(await api.updateStudyPlan(plan.id, payload))
      if (payload.status === 'paused') setPlan(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update your study plan.')
    }
  }

  async function completeTask(taskId) {
    setError('')
    try {
      await api.completeStudyTask(taskId)
      await loadPlan()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not complete the task.')
    }
  }

  async function rebalance() {
    setError('')
    try {
      setPlan(await api.regenerateStudyPlan(plan.id))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not rebalance the plan.')
    }
  }

  if (loading) return <FullPageSpinner />

  return (
    <AppShell>
      <h1 className="font-display text-3xl font-semibold text-ink-900 mb-2">Your study plan</h1>
      <p className="text-sm text-ink-500 mb-6">A daily plan that fits your time and adapts to your progress.</p>
      <ErrorNote>{error}</ErrorNote>

      {!plan ? (
        <Card className="p-6 mt-5">
          <h2 className="font-display text-xl font-semibold text-ink-900 mb-4">Build a personalized plan</h2>
          <form onSubmit={createPlan} className="grid md:grid-cols-2 gap-4">
            <Field label="Goal">
              <input value={form.goal} onChange={(e) => update('goal', e.target.value)} required maxLength={80} />
            </Field>
            <Field label="Target role">
              <input value={form.target_role} onChange={(e) => update('target_role', e.target.value)} required maxLength={120} />
            </Field>
            <Field label="Daily time">
              <select value={form.daily_minutes} onChange={(e) => update('daily_minutes', e.target.value)}>
                <option value="30">30 minutes</option><option value="60">60 minutes</option><option value="90">90 minutes</option>
              </select>
            </Field>
            <Field label="Plan duration">
              <select value={form.duration_days} onChange={(e) => update('duration_days', e.target.value)}>
                {[14, 30, 60, 90].map((days) => <option key={days} value={days}>{days} days</option>)}
              </select>
            </Field>
            <Field label="Preferred days">
              <select value={form.preferred_days} onChange={(e) => update('preferred_days', e.target.value)}>
                <option value="daily">Daily</option><option value="weekdays">Weekdays</option>
              </select>
            </Field>
            <Field label="Current level">
              <select value={form.current_level} onChange={(e) => update('current_level', e.target.value)}>
                <option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option>
              </select>
            </Field>
            <fieldset className="md:col-span-2">
              <legend className="text-xs text-ink-500 mb-2">Topics to include (optional)</legend>
              <div className="flex flex-wrap gap-2">
                {Object.values(ALL_TOPICS_BY_CATEGORY).flat().map((topic) => {
                  const active = form.target_topics.includes(topic)
                  return (
                    <button key={topic} type="button" onClick={() => toggleTopic(topic)}
                      className={`rounded-full border px-3 py-1.5 text-sm ${active ? 'border-amber-500 bg-amber-100 text-amber-600' : 'border-ink-200 text-ink-600'}`}>
                      {active && <Check size={12} className="inline mr-1" />}{topicLabel(topic)}
                    </button>
                  )
                })}
              </div>
            </fieldset>
            <Button className="md:col-span-2" disabled={saving}>{saving ? 'Building plan…' : 'Create my plan'}</Button>
          </form>
        </Card>
      ) : (
        <>
          <Card className="p-5 mt-5 mb-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-amber-600">{plan.goal}</p>
                <h2 className="font-display text-xl font-semibold text-ink-900">{plan.target_role}</h2>
                <p className="text-sm text-ink-500">{plan.daily_minutes} min/day · {plan.start_date} to {plan.end_date}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={rebalance}><RefreshCw size={15} /> Rebalance</Button>
                <select
                  aria-label="Daily study time"
                  value={editMinutes}
                  onChange={(event) => setEditMinutes(event.target.value)}
                  className="rounded-xl border border-ink-200 bg-paper-50 px-3 text-sm text-ink-800"
                >
                  <option value="30">30 min/day</option>
                  <option value="60">60 min/day</option>
                  <option value="90">90 min/day</option>
                </select>
                <Button variant="outline" onClick={() => updatePlan({ daily_minutes: Number(editMinutes) })}>Save</Button>
                <Button variant="ghost" onClick={() => updatePlan({ status: 'paused' })}>Pause</Button>
              </div>
            </div>
          </Card>
          <div className="flex flex-col gap-3">
            {plan.days.map((day) => (
              <Card key={day.id} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs text-ink-500">{day.date} · {day.estimated_minutes} min</p>
                    <h3 className="font-medium text-ink-900">{day.focus}</h3>
                    <p className="text-xs text-ink-500 mt-1">{day.reason}</p>
                  </div>
                  <span className="text-xs text-ink-500 capitalize">{day.status.replace('_', ' ')}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {day.tasks.map((task) => (
                    <div key={task.id} className="flex items-center gap-2 rounded-lg bg-paper-100 px-3 py-2 text-sm">
                      <span className="capitalize text-ink-700">{task.task_type}: {topicLabel(task.topic)}</span>
                      <span className="text-xs text-ink-500">{task.estimated_minutes} min</span>
                      {task.status !== 'completed' && (
                        <button className="text-xs text-amber-600 underline" onClick={() => completeTask(task.id)}>Complete</button>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </AppShell>
  )
}

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs text-ink-500">
      {label}
      {children.type === 'input'
        ? <input className="rounded-lg border border-ink-200 bg-paper-50 px-3 py-2 text-sm text-ink-900" {...children.props} />
        : <select className="rounded-lg border border-ink-200 bg-paper-50 px-3 py-2 text-sm text-ink-900" {...children.props}>{children.props.children}</select>}
    </label>
  )
}
