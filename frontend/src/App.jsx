import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { RedirectIfAuthed, RequireAuth } from './components/guards'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Onboarding from './pages/Onboarding'
import Profile from './pages/Profile'
import Progress from './pages/Progress'
import Register from './pages/Register'
import Result from './pages/Result'
import Review from './pages/Review'
import Companies from './pages/Companies'
import StudyPlan from './pages/StudyPlan'
import TakeTest from './pages/TakeTest'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <Routes>
            <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
            <Route path="/register" element={<RedirectIfAuthed><Register /></RedirectIfAuthed>} />
            <Route path="/onboarding" element={<RequireAuth requireOnboarded={false}><Onboarding /></RequireAuth>} />

            <Route path="/" element={<RequireAuth><Dashboard /></RequireAuth>} />
            <Route path="/test" element={<RequireAuth><TakeTest /></RequireAuth>} />
            <Route path="/result/:testId" element={<RequireAuth><Result /></RequireAuth>} />
            <Route path="/progress" element={<RequireAuth><Progress /></RequireAuth>} />
            <Route path="/profile" element={<RequireAuth><Profile /></RequireAuth>} />
            <Route path="/study-plan" element={<RequireAuth><StudyPlan /></RequireAuth>} />
            <Route path="/review" element={<RequireAuth><Review /></RequireAuth>} />
            <Route path="/companies" element={<RequireAuth><Companies /></RequireAuth>} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ThemeProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
