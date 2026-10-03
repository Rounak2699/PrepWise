import { CheckCircle2, ChevronDown, Sparkles, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import Button from '../components/Button'
import { Card, FullPageSpinner, Pill, ProgressBar } from '../components/ui'
import { api } from '../lib/api'

export default function Result() {
  const { testId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [result, setResult] = useState(null)
  const [report, setReport] = useState(null)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const [r, rep] = await Promise.all([api.getResult(testId), api.report(testId).catch(() => null)])
      if (cancelled) return
      setResult(r)
      setReport(rep)
    }
    load()
    return () => { cancelled = true }
  }, [testId])

  if (!result) return <FullPageSpinner />

  return (
    <AppShell>
      {location.state?.autoSubmitted && (
        <div className="mb-6 text-sm text-amber-600 bg-amber-100 rounded-lg px-4 py-2.5">
          Time ran out, so we submitted your test automatically with what you'd answered.
        </div>
      )}

      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <p className="text-sm text-ink-500">{result.date}</p>
          <h1 className="font-display text-3xl font-semibold text-ink-900">
            {result.score} / {result.total} correct
          </h1>
        </div>
        <div className="flex gap-6 text-right">
          <MiniStat label="Accuracy" value={`${result.accuracy}%`} />
          <MiniStat label="Completion" value={`${result.completion}%`} />
          <MiniStat label="Avg. time" value={`${Math.round(result.average_time)}s`} />
        </div>
      </div>

      {report && (
        <Card className="p-6 mb-8 bg-ink-900 text-paper-50 border-none">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={16} className="text-amber-400" />
            <p className="text-xs font-medium uppercase tracking-wide text-amber-400">AI performance report</p>
          </div>
          <p className="text-sm leading-relaxed text-ink-100 mb-5">{report.summary}</p>
          <div className="grid md:grid-cols-2 gap-6">
            <ReportList title="Strengths" items={report.strengths} tone="moss" />
            <ReportList title="Focus areas" items={report.weaknesses} tone="brick" />
          </div>
          {report.recommendations?.length > 0 && (
            <div className="mt-5 pt-5 border-t border-ink-700">
              <p className="text-xs font-medium text-ink-400 mb-2 uppercase tracking-wide">Recommended next steps</p>
              <ul className="flex flex-col gap-1.5">
                {report.recommendations.map((r, i) => (
                  <li key={i} className="text-sm text-ink-100 flex gap-2">
                    <span className="text-amber-400">→</span> {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      <div className="mb-8">
        <h2 className="font-display text-xl font-semibold text-ink-900 mb-3">By topic</h2>
        <Card className="p-5 flex flex-col gap-4">
          {result.topics.map((t) => (
            <div key={t.topic}>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-ink-800">{t.label}</span>
                <span className="text-ink-500">{t.correct}/{t.attempted} · {t.accuracy}%</span>
              </div>
              <ProgressBar value={t.accuracy} tone={t.accuracy >= 70 ? 'moss' : t.accuracy >= 40 ? 'amber' : 'brick'} />
            </div>
          ))}
        </Card>
      </div>

      <div className="mb-4">
        <h2 className="font-display text-xl font-semibold text-ink-900 mb-3">Question review</h2>
        <Card className="divide-y divide-ink-200">
          {result.questions.map((q) => (
            <div key={q.id}>
              <button
                onClick={() => setExpanded(expanded === q.id ? null : q.id)}
                className="w-full flex items-center justify-between gap-3 px-5 py-3.5 text-left"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {q.is_correct ? (
                    <CheckCircle2 size={18} className="text-moss-600 shrink-0" />
                  ) : (
                    <XCircle size={18} className="text-brick-600 shrink-0" />
                  )}
                  <span className="text-sm text-ink-800 truncate">{q.sequence_no}. {q.prompt}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Pill>{q.category_label}</Pill>
                  <ChevronDown size={16} className={`text-ink-400 transition-transform ${expanded === q.id ? 'rotate-180' : ''}`} />
                </div>
              </button>
              {expanded === q.id && (
                <div className="px-5 pb-4 pl-11">
                  <div className="flex flex-col gap-1.5 mb-3">
                    {q.options.map((opt, i) => {
                      const letter = 'ABCD'[i]
                      const isCorrect = letter === q.correct_answer
                      const isChosen = letter === q.selected_answer
                      return (
                        <div
                          key={letter}
                          className={`text-sm px-3 py-2 rounded-lg border flex items-center gap-2 ${
                            isCorrect ? 'border-moss-500 bg-moss-100 text-moss-600' :
                            isChosen ? 'border-brick-500 bg-brick-100 text-brick-600' : 'border-ink-200 text-ink-600'
                          }`}
                        >
                          <span className="font-semibold">{letter}.</span> {opt}
                          {isChosen && !isCorrect && <span className="text-xs ml-auto">Your answer</span>}
                          {isCorrect && <span className="text-xs ml-auto">Correct answer</span>}
                        </div>
                      )
                    })}
                  </div>
                  <p className="text-sm text-ink-600 leading-relaxed"><span className="font-medium text-ink-800">Why: </span>{q.explanation}</p>
                </div>
              )}
            </div>
          ))}
        </Card>
      </div>

      <Button variant="outline" onClick={() => navigate('/')}>Back to dashboard</Button>
    </AppShell>
  )
}

function MiniStat({ label, value }) {
  return (
    <div>
      <p className="font-display text-xl font-semibold text-ink-900">{value}</p>
      <p className="text-xs text-ink-500">{label}</p>
    </div>
  )
}

function ReportList({ title, items, tone }) {
  if (!items?.length) return null
  const dot = tone === 'moss' ? 'bg-moss-500' : 'bg-brick-500'
  return (
    <div>
      <p className="text-xs font-medium text-ink-400 mb-2 uppercase tracking-wide">{title}</p>
      <ul className="flex flex-col gap-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-ink-100 flex gap-2">
            <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${dot}`} /> {item}
          </li>
        ))}
      </ul>
    </div>
  )
}
