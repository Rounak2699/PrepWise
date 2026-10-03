import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { Card, FullPageSpinner, ProgressBar } from '../components/ui'
import { api } from '../lib/api'

export default function Progress() {
  const navigate = useNavigate()
  const [progress, setProgress] = useState(null)
  const [topics, setTopics] = useState(null)
  const [history, setHistory] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const [p, t, h] = await Promise.all([api.progress(), api.topicProgress(), api.history(30)])
      if (cancelled) return
      setProgress(p)
      setTopics(t)
      setHistory(h)
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (!progress) return <FullPageSpinner />

  const chartData = progress.trend.map((t) => ({ date: t.date.slice(5), pct: t.percentage }))
  const sortedTopics = [...topics].sort((a, b) => a.accuracy - b.accuracy)

  return (
    <AppShell streak={progress.current_streak}>
      <h1 className="font-display text-3xl font-semibold text-ink-900 mb-8">Your progress</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <Stat label="Tests completed" value={progress.tests_completed} />
        <Stat label="Longest streak" value={`${progress.longest_streak}d`} />
        <Stat label="Questions attempted" value={progress.questions_attempted} />
        <Stat label="Overall accuracy" value={`${progress.overall_accuracy}%`} />
      </div>

      <Card className="p-5 mb-8">
        <h2 className="text-sm font-semibold text-ink-800 mb-4">Score trend</h2>
        {chartData.length < 2 ? (
          <p className="text-sm text-ink-500 py-10 text-center">Complete a few more tests to see your trend.</p>
        ) : (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ece9e0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#5b6f9c' }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#5b6f9c' }} axisLine={false} tickLine={false} width={36} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: '1px solid #dbe1ee', fontSize: 13 }}
                  formatter={(v) => [`${v}%`, 'Score']}
                />
                <Line type="monotone" dataKey="pct" stroke="#b9832a" strokeWidth={2.5} dot={{ r: 3, fill: '#b9832a' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <div className="mb-8">
        <h2 className="font-display text-xl font-semibold text-ink-900 mb-3">Topic breakdown</h2>
        {sortedTopics.length === 0 ? (
          <Card className="p-6 text-sm text-ink-500">No attempts yet.</Card>
        ) : (
          <Card className="p-5 flex flex-col gap-4">
            {sortedTopics.map((t) => (
              <div key={t.topic}>
                <div className="flex justify-between text-sm mb-1.5">
                  <div>
                    <span className="font-medium text-ink-800">{t.label}</span>
                    <span className="text-ink-400 text-xs ml-2">{t.category_label}</span>
                  </div>
                  <span className="text-ink-500">{t.correct}/{t.attempted} · {t.accuracy}%</span>
                </div>
                <ProgressBar value={t.accuracy} tone={t.accuracy >= 70 ? 'moss' : t.accuracy >= 40 ? 'amber' : 'brick'} />
              </div>
            ))}
          </Card>
        )}
      </div>

      <div>
        <h2 className="font-display text-xl font-semibold text-ink-900 mb-3">Test history</h2>
        <Card className="divide-y divide-ink-200">
          {history.length === 0 && <p className="p-6 text-sm text-ink-500">No tests yet.</p>}
          {history.map((h) => (
            <button
              key={h.test_id}
              onClick={() => h.status === 'submitted' && navigate(`/result/${h.test_id}`)}
              className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-ink-100/60 transition-colors first:rounded-t-2xl last:rounded-b-2xl"
            >
              <span className="text-sm font-medium text-ink-900">{h.date}</span>
              {h.status === 'submitted' ? (
                <span className="text-sm text-ink-600">{h.score}/{h.total} · {h.accuracy}%</span>
              ) : (
                <span className="text-xs text-ink-400 capitalize">{h.status.replace('_', ' ')}</span>
              )}
            </button>
          ))}
        </Card>
      </div>
    </AppShell>
  )
}

function Stat({ label, value }) {
  return (
    <Card className="p-4">
      <p className="text-xl font-semibold text-ink-900 font-display">{value}</p>
      <p className="text-xs text-ink-500 mt-0.5">{label}</p>
    </Card>
  )
}
