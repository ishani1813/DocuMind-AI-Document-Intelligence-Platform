import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, FileText, MessageSquare, Search, Users, LogOut, ChevronLeft, ChevronRight, Brain, Menu, X, Sparkles, Activity } from 'lucide-react'
import useAuthStore from '../../store/authStore'
import { initials } from '../../utils/formatters'
import clsx from 'clsx'

const NAV = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/documents',  icon: FileText,        label: 'Documents' },
  { to: '/chat',       icon: MessageSquare,   label: 'Chat' },
  { to: '/search',     icon: Search,          label: 'Search' },
  { to: '/workspaces', icon: Users,           label: 'Workspaces' },
  { to: '/ml',         icon: Sparkles,        label: 'ML Insights' },
  { to: '/llmops',     icon: Activity,        label: 'LLMOps' },
]

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }
  const userInitials = initials(user?.full_name || '')

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={clsx('flex items-center gap-3 px-4 py-5 border-b border-surface-800', collapsed && 'px-3')}>
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
          <Brain className="w-4 h-4 text-white" />
        </div>
        {!collapsed && (
          <div>
            <span className="font-bold text-white text-base">DocuMind</span>
            <p className="text-[10px] text-surface-200 leading-tight">AI Document Intelligence</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) => clsx('sidebar-item', isActive && 'sidebar-item-active', collapsed && 'justify-center px-2')}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-surface-800">
        <div className={clsx('flex items-center gap-3', collapsed && 'justify-center')}>
          <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-xs font-semibold flex-shrink-0">
            {userInitials}
          </div>
          {!collapsed && (
            <>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
                <p className="text-xs text-surface-200 truncate">{user?.email}</p>
              </div>
              <button onClick={handleLogout} className="text-surface-200 hover:text-red-400 transition-colors p-1">
                <LogOut className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen bg-surface-950 overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className={clsx('hidden lg:flex flex-col bg-surface-900 border-r border-surface-800 transition-all duration-300 relative', collapsed ? 'w-16' : 'w-60')}>
        <SidebarContent />
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-surface-700 border border-surface-600 rounded-full flex items-center justify-center text-surface-200 hover:text-white z-10"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <aside className="relative w-64 bg-surface-900 border-r border-surface-800 flex flex-col z-10">
            <button onClick={() => setMobileOpen(false)} className="absolute top-3 right-3 text-surface-200 hover:text-white"><X className="w-5 h-5" /></button>
            <SidebarContent />
          </aside>
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-surface-800 bg-surface-900">
          <button onClick={() => setMobileOpen(true)} className="text-surface-200 hover:text-white"><Menu className="w-5 h-5" /></button>
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-brand-400" />
            <span className="font-bold text-white">DocuMind</span>
          </div>
        </header>
        <main className="flex-1 overflow-auto"><Outlet /></main>
      </div>
    </div>
  )
}
