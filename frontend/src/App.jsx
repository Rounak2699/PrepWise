import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { RedirectIfAuthed, RequireAuth } from './components/guards'
import { AuthProvider } from './context/AuthContext'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Onboarding from './pages/Onboarding'
import Profile from './pages/Profile'
import Progress from './pages/Progress'
import Register from './pages/Register'
import Result from './pages/Result'
import TakeTest from './pages/TakeTest'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
          <Route path="/register" element={<RedirectIfAuthed><Register /></RedirectIfAuthed>} />
          <Route path="/onboarding" element={<RequireAuth requireOnboarded={false}><Onboarding /></RequireAuth>} />

          <Route path="/" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="/test" element={<RequireAuth><TakeTest /></RequireAuth>} />
          <Route path="/result/:testId" element={<RequireAuth><Result /></RequireAuth>} />
          <Route path="/progress" element={<RequireAuth><Progress /></RequireAuth>} />
          <Route path="/profile" element={<RequireAuth><Profile /></RequireAuth>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
