import { Building2, Flame, LayoutDashboard, LineChart, LogOut, RotateCcw, Sun, UserRound } from 'lucide-react'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/study-plan', label: 'Study plan', icon: Sun },
  { to: '/review', label: 'Review', icon: RotateCcw },
  { to: '/companies', label: 'Companies', icon: Building2 },
  { to: '/progress', label: 'Progress', icon: LineChart },
  { to: '/profile', label: 'Profile', icon: UserRound },
]

export default function AppShell({ children, streak = 0 }) {
  const { user, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const [themeError, setThemeError] = useState('')

  async function changeTheme(value) {
    setThemeError('')
    try {
      await setTheme(value)
    } catch {
      setThemeError('Could not save your theme preference.')
    }
  }

  return (
    <div className="min-h-screen bg-paper-100 flex">
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-ink-200 bg-paper-50 px-5 py-6">
        <div className="flex items-center gap-2 px-2 mb-8">
          <div className="w-8 h-8 rounded-lg bg-ink-900 text-amber-400 font-display font-semibold flex items-center justify-center text-lg">P</div>
          <span className="font-display text-lg font-semibold text-ink-900">Prepwise</span>
        </div>

        <nav className="flex flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive ? 'bg-ink-900 text-paper-50' : 'text-ink-600 hover:bg-ink-100'
                }`
              }
            >
              <Icon size={17} strokeWidth={2} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto flex flex-col gap-3">
          <label className="px-3 flex items-center justify-between gap-2 text-xs text-ink-500">
            <span>Appearance</span>
            <select
              aria-label="Theme"
              value={theme}
              onChange={(event) => changeTheme(event.target.value)}
              className="rounded-lg border border-ink-200 bg-paper-50 px-2 py-1 text-ink-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500"
            >
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>
          {themeError && <p role="alert" className="px-3 text-xs text-brick-600">{themeError}</p>}
          {streak > 0 && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-100 text-amber-600 text-sm font-medium">
              <Flame size={16} />
              {streak}-day streak
            </div>
          )}
          <div className="px-3">
            <p className="text-sm font-medium text-ink-900 truncate">{user?.name}</p>
            <p className="text-xs text-ink-500 truncate">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-ink-500 hover:bg-ink-100 hover:text-ink-800 transition-colors"
          >
            <LogOut size={16} />
            Log out
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0">
        <header className="md:hidden relative flex items-center justify-between px-4 py-3 border-b border-ink-200 bg-paper-50 sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-ink-900 text-amber-400 font-display font-semibold flex items-center justify-center text-sm">P</div>
            <span className="font-display font-semibold text-ink-900">Prepwise</span>
          </div>
          <nav className="flex items-center gap-1 overflow-x-auto">
            {NAV.map(({ to, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `p-2 rounded-lg ${isActive ? 'bg-ink-900 text-paper-50' : 'text-ink-500'}`
                }
              >
                <Icon size={18} />
              </NavLink>
            ))}
            <select
              aria-label="Theme"
              value={theme}
              onChange={(event) => changeTheme(event.target.value)}
              className="max-w-20 rounded-lg border border-ink-200 bg-paper-50 px-1 py-2 text-xs text-ink-800"
            >
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
            <button onClick={logout} className="p-2 rounded-lg text-ink-500">
              <LogOut size={18} />
            </button>
          </nav>
          {themeError && <p role="alert" className="absolute left-2 right-2 top-full rounded-lg bg-paper-50 px-3 py-2 text-xs text-brick-600 shadow">{themeError}</p>}
        </header>

        <main className="max-w-5xl mx-auto px-4 md:px-8 py-8">{children}</main>
      </div>
    </div>
  )
}
