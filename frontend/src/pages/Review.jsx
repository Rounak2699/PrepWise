import { useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import Button from '../components/Button'
import { Card, ErrorNote, FullPageSpinner } from '../components/ui'
import { api, ApiError } from '../lib/api'
import { topicLabel } from '../lib/taxonomy'

const RATINGS = [
  ['again', 'Again'],
  ['hard', 'Hard'],
  ['good', 'Good'],
  ['easy', 'Easy'],
]

export default function Review() {
  const [items, setItems] = useState(null)
  const [stats, setStats] = useState(null)
  const [active, setActive] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function load() {
    try {
      const [due, reviewStats] = await Promise.all([api.dueReviews(), api.reviewStats()])
      setItems(due)
      setStats(reviewStats)
      setActive(0)
      setResult(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load reviews.')
      setItems([])
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([api.dueReviews(), api.reviewStats()])
      .then(([due, reviewStats]) => {
        if (!active) return
        setItems(due)
        setStats(reviewStats)
      })
      .catch((err) => {
        if (!active) return
        setError(err instanceof ApiError ? err.message : 'Could not load reviews.')
        setItems([])
      })
    return () => { active = false }
  }, [])

  async function rate(resultValue) {
    const item = items[active]
    try {
      setError('')
      setResult(await api.submitReview(item.id, { result: resultValue }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save your review.')
    }
  }

  async function next() {
    await load()
  }

  if (items === null) return <FullPageSpinner />
  const item = items[active]

  return (
    <AppShell>
      <h1 className="font-display text-3xl font-semibold text-ink-900 mb-2">Spaced repetition</h1>
      <p className="text-sm text-ink-500 mb-6">Review concepts at increasing intervals to strengthen long-term recall.</p>
      <ErrorNote>{error}</ErrorNote>
      {stats && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <Stat label="Due now" value={stats.due} />
          <Stat label="Items tracked" value={stats.total} />
          <Stat label="Review attempts" value={stats.completed_attempts} />
        </div>
      )}
      {!item ? (
        <Card className="p-8 text-center">
          <h2 className="font-display text-xl font-semibold text-ink-900">You’re all caught up</h2>
          <p className="text-sm text-ink-500 mt-2">Questions from completed challenges will appear here when they are due.</p>
        </Card>
      ) : (
        <Card className="p-6">
          <p className="text-xs uppercase tracking-wide text-amber-600">{topicLabel(item.topic)} · {active + 1} of {items.length}</p>
          <h2 className="font-display text-xl text-ink-900 leading-relaxed my-4">{item.prompt}</h2>
          <div className="flex flex-col gap-2">
            {item.options.map((option, index) => (
              <div key={index} className="rounded-lg border border-ink-200 px-3 py-2 text-sm text-ink-700">
                {'ABCD'[index]}. {option}
              </div>
            ))}
          </div>
          {result ? (
            <div className="mt-5">
              <p className="text-sm text-ink-700">
                Correct answer: <strong>{result.correct_answer}</strong> · Next review in {result.interval_days} day(s).
              </p>
              <p className="text-sm text-ink-500 mt-2">{result.explanation}</p>
              <Button className="mt-5" onClick={next}>Next review</Button>
            </div>
          ) : (
            <div className="mt-5">
              <p className="text-xs text-ink-500 mb-2">How well did you recall it?</p>
              <div className="flex flex-wrap gap-2">
                {RATINGS.map(([value, label]) => (
                  <Button key={value} variant={value === 'again' ? 'outline' : 'primary'} onClick={() => rate(value)}>
                    {label}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </AppShell>
  )
}

function Stat({ label, value }) {
  return <Card className="p-4"><p className="text-xl font-display font-semibold text-ink-900">{value}</p><p className="text-xs text-ink-500">{label}</p></Card>
}
