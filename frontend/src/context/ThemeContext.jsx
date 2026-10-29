import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useAuth } from './AuthContext'

const STORAGE_KEY = 'pp_theme'
const ThemeContext = createContext(null)

function readStoredTheme() {
  const saved = localStorage.getItem(STORAGE_KEY)
  return ['light', 'dark', 'system'].includes(saved) ? saved : 'system'
}

export function ThemeProvider({ children }) {
  const { user } = useAuth()
  const [theme, setThemeState] = useState(readStoredTheme)

  useEffect(() => {
    if (!user) return
    let active = true
    api.theme().then(({ theme: savedTheme }) => {
      if (active && ['light', 'dark', 'system'].includes(savedTheme)) {
        setThemeState(savedTheme)
        localStorage.setItem(STORAGE_KEY, savedTheme)
      }
    }).catch((error) => {
      console.error('Could not load saved theme preference.', error)
    })
    return () => { active = false }
  }, [user])

  useEffect(() => {
    const root = document.documentElement
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const applyTheme = () => {
      root.dataset.theme = theme === 'system' ? (media.matches ? 'dark' : 'light') : theme
      root.style.colorScheme = root.dataset.theme
    }
    applyTheme()
    media.addEventListener('change', applyTheme)
    return () => media.removeEventListener('change', applyTheme)
  }, [theme])

  const setTheme = useCallback(async (nextTheme) => {
    if (!['light', 'dark', 'system'].includes(nextTheme)) {
      throw new Error('Choose light, dark, or system theme.')
    }
    const previousTheme = theme
    setThemeState(nextTheme)
    localStorage.setItem(STORAGE_KEY, nextTheme)
    if (!user) return
    try {
      await api.updateTheme(nextTheme)
    } catch (error) {
      setThemeState(previousTheme)
      localStorage.setItem(STORAGE_KEY, previousTheme)
      throw error
    }
  }, [theme, user])

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used within ThemeProvider')
  return context
}
