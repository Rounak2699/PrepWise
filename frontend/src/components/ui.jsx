export function Card({ className = '', children, ...props }) {
  return (
    <div className={`bg-paper-50 border border-ink-200 rounded-2xl ${className}`} {...props}>
      {children}
    </div>
  )
}

export function Spinner({ className = 'w-5 h-5' }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export function FullPageSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-100 text-ink-500">
      <Spinner className="w-8 h-8" />
    </div>
  )
}

export function Pill({ tone = 'neutral', children, className = '' }) {
  const tones = {
    neutral: 'bg-ink-100 text-ink-700',
    amber: 'bg-amber-100 text-amber-600',
    moss: 'bg-moss-100 text-moss-600',
    brick: 'bg-brick-100 text-brick-600',
  }
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${tones[tone]} ${className}`}>
      {children}
    </span>
  )
}

export function ProgressBar({ value, tone = 'ink' }) {
  const tones = { ink: 'bg-ink-800', amber: 'bg-amber-500', moss: 'bg-moss-500', brick: 'bg-brick-500' }
  return (
    <div className="w-full h-2 rounded-full bg-ink-100 overflow-hidden">
      <div
        className={`h-full rounded-full ${tones[tone]} transition-all duration-500`}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  )
}

export function ErrorNote({ children }) {
  if (!children) return null
  return (
    <div className="text-sm text-brick-600 bg-brick-100 rounded-lg px-3 py-2">
      {children}
    </div>
  )
}
