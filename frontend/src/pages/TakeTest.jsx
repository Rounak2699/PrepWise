import { AlertTriangle, Check, ChevronLeft, ChevronRight, Flag, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { Card, FullPageSpinner, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { categoryLabel } from '../lib/taxonomy'

const OPTION_LETTERS = ['A', 'B', 'C', 'D']

export default function TakeTest() {
  const navigate = useNavigate()
  const [testId, setTestId] = useState(null)
  const [questions, setQuestions] = useState(null)
  const [answers, setAnswers] = useState({}) // question_id -> letter | null
  const [marked, setMarked] = useState({}) // question_id -> bool
  const [current, setCurrent] = useState(0)
  const [remaining, setRemaining] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [error, setError] = useState('')

  const timeSpent = useRef({})
  const activeSince = useRef(Date.now())
  const submittedRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const daily = await api.dailyChallenge()
      if (daily.status === 'submitted') {
        navigate(`/result/${daily.test_id}`, { replace: true })
        return
      }
      const started = await api.startTest(daily.test_id)
      if (cancelled) return
      setTestId(daily.test_id)
      setQuestions(started.questions)
      setRemaining(started.remaining_seconds)
      const initAnswers = {}, initMarked = {}, initTime = {}
      for (const q of started.questions) {
        initAnswers[q.id] = q.selected_answer
        initMarked[q.id] = q.marked_for_review
        initTime[q.id] = q.time_spent_seconds || 0
      }
      setAnswers(initAnswers)
      setMarked(initMarked)
      timeSpent.current = initTime
      activeSince.current = Date.now()
    }
    load()
    return () => { cancelled = true }
  }, [navigate])

  // Countdown timer
  useEffect(() => {
    if (remaining === null || submittedRef.current) return
    if (remaining <= 0) {
      handleSubmit(true)
      return
    }
    const t = setTimeout(() => setRemaining((r) => r - 1), 1000)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining])

  const flushCurrentTime = useCallback(() => {
    if (!questions) return
    const q = questions[current]
    const elapsed = Math.round((Date.now() - activeSince.current) / 1000)
    timeSpent.current[q.id] = (timeSpent.current[q.id] || 0) + elapsed
    activeSince.current = Date.now()
    return q
  }, [questions, current])

  const persist = useCallback((questionId, overrides = {}) => {
    const payload = {
      question_id: questionId,
      selected_answer: overrides.selected_answer !== undefined ? overrides.selected_answer : answers[questionId] ?? null,
      marked_for_review: overrides.marked_for_review !== undefined ? overrides.marked_for_review : !!marked[questionId],
      time_spent_seconds: Math.min(timeSpent.current[questionId] || 0, 3600),
    }
    api.saveResponse(testId, payload).catch(() => {})
  }, [testId, answers, marked])

  function selectAnswer(letter) {
    const q = questions[current]
    setAnswers((a) => ({ ...a, [q.id]: letter }))
    const elapsed = Math.round((Date.now() - activeSince.current) / 1000)
    timeSpent.current[q.id] = (timeSpent.current[q.id] || 0) + elapsed
    activeSince.current = Date.now()
    persist(q.id, { selected_answer: letter })
  }

  function toggleMark() {
    const q = questions[current]
    setMarked((m) => {
      const next = !m[q.id]
      persist(q.id, { marked_for_review: next })
      return { ...m, [q.id]: next }
    })
  }

  function goTo(index) {
    if (index < 0 || index >= questions.length || index === current) return
    const q = flushCurrentTime()
    persist(q.id)
    setCurrent(index)
  }

  async function handleSubmit(auto = false) {
    if (submittedRef.current) return
    submittedRef.current = true
    setSubmitting(true)
    try {
      const q = flushCurrentTime()
      if (q) persist(q.id)
      await new Promise((r) => setTimeout(r, 150)) // let the last autosave land
      await api.submitTest(testId)
      navigate(`/result/${testId}`, { replace: true, state: { autoSubmitted: auto } })
    } catch (err) {
      submittedRef.current = false
      setSubmitting(false)
      setError('Could not submit your test. Check your connection and try again.')
    }
  }

  const stats = useMemo(() => {
    if (!questions) return { answered: 0, markedCount: 0, unanswered: 0 }
    const answered = questions.filter((q) => answers[q.id]).length
    const markedCount = questions.filter((q) => marked[q.id]).length
    return { answered, markedCount, unanswered: questions.length - answered }
  }, [questions, answers, marked])

  if (!questions) return <FullPageSpinner />

  const q = questions[current]
  const mins = Math.floor((remaining ?? 0) / 60)
  const secs = (remaining ?? 0) % 60
  const timeLow = remaining !== null && remaining < 60

  return (
    <div className="min-h-screen bg-paper-100 flex flex-col">
      <header className="sticky top-0 z-10 bg-paper-50 border-b border-ink-200 px-4 md:px-8 py-3 flex items-center justify-between">
        <div>
          <p className="text-xs text-ink-500">Question {current + 1} of {questions.length}</p>
          <p className="text-sm font-medium text-ink-900">{categoryLabel(q.category)}</p>
        </div>
        <div className={`font-display text-2xl font-semibold tabular-nums ${timeLow ? 'text-brick-600' : 'text-ink-900'}`}>
          {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
        </div>
      </header>

      <div className="flex-1 max-w-5xl w-full mx-auto px-4 md:px-8 py-8 grid md:grid-cols-[1fr_240px] gap-8">
        <div>
          <Card className="p-6 md:p-8">
            <p className="text-xs uppercase tracking-wide text-ink-400 mb-3">{q.difficulty}</p>
            <p className="font-display text-xl text-ink-900 leading-relaxed mb-6 whitespace-pre-wrap">{q.prompt}</p>
            <div className="flex flex-col gap-2.5">
              {q.options.map((opt, i) => {
                const letter = OPTION_LETTERS[i]
                const selected = answers[q.id] === letter
                return (
                  <button
                    key={letter}
                    onClick={() => selectAnswer(letter)}
                    className={`flex items-start gap-3 text-left px-4 py-3 rounded-xl border transition-colors ${
                      selected ? 'border-ink-900 bg-ink-900 text-paper-50' : 'border-ink-200 hover:border-ink-400'
                    }`}
                  >
                    <span className={`shrink-0 w-6 h-6 rounded-full text-xs font-semibold flex items-center justify-center ${
                      selected ? 'bg-amber-500 text-ink-950' : 'bg-ink-100 text-ink-600'
                    }`}>
                      {letter}
                    </span>
                    <span className="text-sm leading-relaxed">{opt}</span>
                  </button>
                )
              })}
            </div>
          </Card>

          <div className="flex items-center justify-between mt-5">
            <Button variant="outline" onClick={() => goTo(current - 1)} disabled={current === 0}>
              <ChevronLeft size={16} /> Previous
            </Button>
            <button
              onClick={toggleMark}
              className={`flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-lg transition-colors ${
                marked[q.id] ? 'text-amber-600 bg-amber-100' : 'text-ink-500 hover:bg-ink-100'
              }`}
            >
              <Flag size={15} /> {marked[q.id] ? 'Marked for review' : 'Mark for review'}
            </button>
            {current === questions.length - 1 ? (
              <Button variant="accent" onClick={() => setConfirmOpen(true)}>Submit test</Button>
            ) : (
              <Button onClick={() => goTo(current + 1)}>Next <ChevronRight size={16} /></Button>
            )}
          </div>
          {error && <p className="text-sm text-brick-600 mt-3">{error}</p>}
        </div>

        <div>
          <p className="text-xs font-medium text-ink-500 mb-2 uppercase tracking-wide">Question palette</p>
          <div className="grid grid-cols-6 md:grid-cols-5 gap-2 mb-4">
            {questions.map((qq, i) => {
              const answered = !!answers[qq.id]
              const isMarked = marked[qq.id]
              const isCurrent = i === current
              return (
                <button
                  key={qq.id}
                  onClick={() => goTo(i)}
                  className={`relative w-9 h-9 rounded-lg text-xs font-semibold flex items-center justify-center transition-colors ${
                    isCurrent ? 'ring-2 ring-offset-1 ring-ink-800' : ''
                  } ${
                    isMarked ? 'bg-amber-400 text-ink-950' : answered ? 'bg-ink-900 text-paper-50' : 'bg-ink-100 text-ink-500'
                  }`}
                >
                  {i + 1}
                </button>
              )
            })}
          </div>
          <div className="flex flex-col gap-1.5 text-xs text-ink-500">
            <Legend swatch="bg-ink-900" label={`Answered (${stats.answered})`} />
            <Legend swatch="bg-amber-400" label={`Marked (${stats.markedCount})`} />
            <Legend swatch="bg-ink-100" label={`Unanswered (${stats.unanswered})`} />
          </div>
        </div>
      </div>

      {confirmOpen && (
        <ConfirmSubmit
          stats={stats}
          total={questions.length}
          onCancel={() => setConfirmOpen(false)}
          onConfirm={() => handleSubmit(false)}
          submitting={submitting}
        />
      )}
    </div>
  )
}

function Legend({ swatch, label }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-3 h-3 rounded ${swatch}`} />
      {label}
    </div>
  )
}

function ConfirmSubmit({ stats, total, onCancel, onConfirm, submitting }) {
  return (
    <div className="fixed inset-0 bg-ink-950/40 flex items-center justify-center p-4 z-20">
      <Card className="max-w-sm w-full p-6 rise-in">
        <div className="flex items-start justify-between mb-4">
          <h3 className="font-display text-xl font-semibold text-ink-900">Submit your test?</h3>
          <button onClick={onCancel} className="text-ink-400 hover:text-ink-700"><X size={18} /></button>
        </div>
        {stats.unanswered > 0 && (
          <div className="flex items-start gap-2 text-sm text-amber-600 bg-amber-100 rounded-lg px-3 py-2 mb-4">
            <AlertTriangle size={16} className="shrink-0 mt-0.5" />
            You still have {stats.unanswered} unanswered question{stats.unanswered > 1 ? 's' : ''}.
          </div>
        )}
        <div className="text-sm text-ink-600 mb-6 flex flex-col gap-1">
          <p className="flex justify-between"><span>Answered</span><span className="font-medium text-ink-900">{stats.answered} / {total}</span></p>
          <p className="flex justify-between"><span>Marked for review</span><span className="font-medium text-ink-900">{stats.markedCount}</span></p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onCancel} className="flex-1">Keep going</Button>
          <Button variant="accent" onClick={onConfirm} disabled={submitting} className="flex-1">
            {submitting ? <Spinner className="w-4 h-4" /> : <Check size={16} />}
            Submit
          </Button>
        </div>
      </Card>
    </div>
  )
}
