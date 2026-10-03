import { ArrowRight, CheckCircle2, Clock, Flame, ListChecks, Target } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import Button from '../components/Button'
import { Card, FullPageSpinner, Pill } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [challenge, setChallenge] = useState(null)
  const [progress, setProgress] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const [c, p, h] = await Promise.all([api.dailyChallenge(), api.progress(), api.history(5)])
      if (cancelled) return
      setChallenge(c)
      setProgress(p)
      setHistory(h)
      setLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (loading) return <FullPageSpinner />

  const firstName = user?.name?.split(' ')[0]
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <AppShell streak={progress?.current_streak}>
      <p className="text-sm text-ink-500 mb-1">{greeting}, {firstName}</p>
      <h1 className="font-display text-3xl font-semibold text-ink-900 mb-8">Ready to keep the streak alive?</h1>

      <ChallengeCard challenge={challenge} onGo={() => navigate('/test')} onReview={() => navigate(`/result/${challenge.test_id}`)} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
        <StatCard icon={Flame} label="Current streak" value={progress.current_streak} suffix="days" tone="amber" />
        <StatCard icon={ListChecks} label="Tests completed" value={progress.tests_completed} />
        <StatCard icon={Target} label="Overall accuracy" value={`${progress.overall_accuracy}%`} />
        <StatCard icon={Clock} label="Avg. time / question" value={`${Math.round(progress.average_time)}s`} />
      </div>

      <div className="mt-10">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display text-xl font-semibold text-ink-900">Recent activity</h2>
          <button onClick={() => navigate('/progress')} className="text-sm text-ink-500 hover:text-ink-800 flex items-center gap-1">
            View all <ArrowRight size={14} />
          </button>
        </div>
        {history.length === 0 ? (
          <Card className="p-6 text-sm text-ink-500">No tests yet — finish today's challenge to see it here.</Card>
        ) : (
          <Card className="divide-y divide-ink-200">
            {history.map((h) => (
              <button
                key={h.test_id}
                onClick={() => h.status === 'submitted' && navigate(`/result/${h.test_id}`)}
                className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-ink-100/60 transition-colors first:rounded-t-2xl last:rounded-b-2xl"
              >
                <div>
                  <p className="text-sm font-medium text-ink-900">{h.date}</p>
                  <p className="text-xs text-ink-500 capitalize">{h.status.replace('_', ' ')}</p>
                </div>
                {h.status === 'submitted' ? (
                  <div className="text-right">
                    <p className="text-sm font-semibold text-ink-900">{h.score}/{h.total}</p>
                    <p className="text-xs text-ink-500">{h.accuracy}% accuracy</p>
                  </div>
                ) : (
                  <Pill>{h.status.replace('_', ' ')}</Pill>
                )}
              </button>
            ))}
          </Card>
        )}
      </div>
    </AppShell>
  )
}

function ChallengeCard({ challenge, onGo, onReview }) {
  const isSubmitted = challenge.status === 'submitted'
  const isInProgress = challenge.status === 'in_progress'

  return (
    <Card className="p-7 bg-ink-900 text-paper-50 border-none relative overflow-hidden">
      <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full bg-amber-500/10" />
      <div className="relative flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div>
          <p className="text-xs font-medium text-amber-400 mb-2 uppercase tracking-wide">Today's Challenge</p>
          {isSubmitted ? (
            <>
              <h3 className="font-display text-2xl font-semibold mb-1 flex items-center gap-2">
                <CheckCircle2 className="text-moss-500" size={22} /> Done for today
              </h3>
              <p className="text-ink-300 text-sm">Great work — come back tomorrow for a fresh set.</p>
            </>
          ) : isInProgress ? (
            <>
              <h3 className="font-display text-2xl font-semibold mb-1">You're mid-test</h3>
              <p className="text-ink-300 text-sm">{challenge.total_questions} questions · pick up right where you left off.</p>
            </>
          ) : (
            <>
              <h3 className="font-display text-2xl font-semibold mb-1">{challenge.total_questions} questions, {Math.round(challenge.duration_seconds / 60)} minutes</h3>
              <p className="text-ink-300 text-sm">Aptitude and core CS, tuned to your weak spots.</p>
            </>
          )}
        </div>
        <Button
          variant="accent"
          size="lg"
          onClick={isSubmitted ? onReview : onGo}
          className="shrink-0"
        >
          {isSubmitted ? 'View result' : isInProgress ? 'Resume test' : 'Start test'}
          <ArrowRight size={16} />
        </Button>
      </div>
    </Card>
  )
}

function StatCard({ icon: Icon, label, value, suffix, tone }) {
  return (
    <Card className="p-4">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-3 ${tone === 'amber' ? 'bg-amber-100 text-amber-600' : 'bg-ink-100 text-ink-600'}`}>
        <Icon size={16} />
      </div>
      <p className="text-xl font-semibold text-ink-900 font-display">
        {value}{suffix && <span className="text-sm text-ink-400 ml-1 font-sans">{suffix}</span>}
      </p>
      <p className="text-xs text-ink-500 mt-0.5">{label}</p>
    </Card>
  )
}
