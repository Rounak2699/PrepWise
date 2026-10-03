const VARIANTS = {
  primary: 'bg-ink-900 text-paper-50 hover:bg-ink-800 disabled:bg-ink-300',
  accent: 'bg-amber-500 text-ink-950 hover:bg-amber-400 disabled:bg-amber-100 disabled:text-ink-400',
  ghost: 'bg-transparent text-ink-700 hover:bg-ink-100 disabled:text-ink-300',
  outline: 'bg-transparent border border-ink-300 text-ink-800 hover:border-ink-500 hover:bg-ink-100 disabled:text-ink-300',
  danger: 'bg-transparent text-brick-600 hover:bg-brick-100 disabled:text-ink-300',
}

const SIZES = {
  sm: 'text-sm px-3 py-1.5 rounded-lg',
  md: 'text-sm px-4 py-2.5 rounded-xl',
  lg: 'text-base px-6 py-3 rounded-xl',
}

export default function Button({
  variant = 'primary', size = 'md', className = '', children, ...props
}) {
  return (
    <button
      className={`font-medium transition-colors duration-150 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
