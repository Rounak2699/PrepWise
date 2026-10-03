export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="min-h-screen bg-paper-100 flex">
      <div className="hidden lg:flex lg:w-5/12 bg-ink-900 text-paper-50 flex-col justify-between p-12">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-amber-500 text-ink-950 font-display font-semibold flex items-center justify-center text-lg">P</div>
          <span className="font-display text-xl font-semibold">Prepwise</span>
        </div>
        <div className="max-w-sm">
          <p className="font-display text-3xl leading-snug mb-4">
            A little sharper, every single day.
          </p>
          <p className="text-ink-300 text-sm leading-relaxed">
            Twelve questions a day across aptitude and core CS, scored instantly,
            with an AI coach that tells you exactly what to fix next before placement season.
          </p>
        </div>
        <p className="text-ink-400 text-xs">Built for pre-final and final-year students.</p>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm rise-in">
          <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
            <div className="w-8 h-8 rounded-lg bg-ink-900 text-amber-400 font-display font-semibold flex items-center justify-center text-lg">P</div>
            <span className="font-display text-lg font-semibold text-ink-900">Prepwise</span>
          </div>
          <h1 className="font-display text-2xl font-semibold text-ink-900 mb-1.5">{title}</h1>
          <p className="text-sm text-ink-500 mb-8">{subtitle}</p>
          {children}
        </div>
      </div>
    </div>
  )
}
