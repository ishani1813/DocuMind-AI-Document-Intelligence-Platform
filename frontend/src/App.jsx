import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/authStore'
import AppLayout from './components/layout/AppLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import DocumentsPage from './pages/DocumentsPage'
import ChatPage from './pages/ChatPage'
import SearchPage from './pages/SearchPage'
import WorkspacesPage from './pages/WorkspacesPage'
import MLInsightsPage from './pages/MLInsightsPage'
import LLMOpsPage from './pages/LLMOpsPage'

function Protected({ children }) {
  const auth = useAuthStore((s) => s.isAuthenticated)
  return auth ? children : <Navigate to="/login" replace />
}

function Public({ children }) {
  const auth = useAuthStore((s) => s.isAuthenticated)
  return auth ? <Navigate to="/dashboard" replace /> : children
}

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate)
  useEffect(() => { hydrate() }, [hydrate])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login"    element={<Public><LoginPage /></Public>} />
        <Route path="/register" element={<Public><RegisterPage /></Public>} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/" element={<Protected><AppLayout /></Protected>}>
          <Route path="dashboard"  element={<DashboardPage />} />
          <Route path="documents"  element={<DocumentsPage />} />
          <Route path="chat"       element={<ChatPage />} />
          <Route path="chat/:id"   element={<ChatPage />} />
          <Route path="search"     element={<SearchPage />} />
          <Route path="workspaces" element={<WorkspacesPage />} />
          <Route path="ml"         element={<MLInsightsPage />} />
          <Route path="llmops"     element={<LLMOpsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
