import { useQuery } from '@tanstack/react-query'
import { FileText, MessageSquare, Users, Search, ArrowRight, TrendingUp, Brain, Activity } from 'lucide-react'
import { Link } from 'react-router-dom'
import { documentsApi, chatApi, workspacesApi, llmopsApi } from '../services/api'
import useAuthStore from '../store/authStore'
import { formatRelative, formatCost } from '../utils/formatters'

function StatCard({ icon: Icon, label, value, color, to }) {
  return (
    <Link to={to} className="card p-5 flex items-center gap-4 hover:border-surface-700 transition-colors group">
      <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center flex-shrink-0`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-2xl font-bold text-white">{value ?? '—'}</p>
        <p className="text-sm text-surface-200">{label}</p>
      </div>
      <ArrowRight className="w-4 h-4 text-surface-200 group-hover:text-white group-hover:translate-x-0.5 transition-all" />
    </Link>
  )
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const { data: docs } = useQuery({ queryKey: ['documents'], queryFn: () => documentsApi.list() })
  const { data: sessions } = useQuery({ queryKey: ['chatSessions'], queryFn: () => chatApi.listSessions() })
  const { data: workspaces } = useQuery({ queryKey: ['workspaces'], queryFn: () => workspacesApi.list() })
  const { data: llmMetrics } = useQuery({ queryKey: ['llmops-overview'], queryFn: () => llmopsApi.overview(24), retry: false })

  const documents = docs?.data || []
  const chats = sessions?.data || []
  const ws = workspaces?.data || []
  const metrics = llmMetrics?.data

  const readyDocs = documents.filter((d) => d.status === 'ready')
  const recentDocs = [...documents].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5)
  const recentChats = [...chats].slice(0, 4)
  const firstName = user?.full_name?.split(' ')[0] || 'there'

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Welcome back, {firstName}</h1>
          <p className="text-surface-200 text-sm mt-0.5">Here's what's happening with your documents</p>
        </div>
        <Link to="/documents" className="btn-primary hidden sm:flex"><FileText className="w-4 h-4" />Upload Document</Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={FileText} label="Documents" value={documents.length} color="bg-brand-600" to="/documents" />
        <StatCard icon={TrendingUp} label="Processed" value={readyDocs.length} color="bg-emerald-600" to="/documents" />
        <StatCard icon={MessageSquare} label="Chats" value={chats.length} color="bg-violet-600" to="/chat" />
        <StatCard icon={Users} label="Workspaces" value={ws.length} color="bg-amber-600" to="/workspaces" />
      </div>

      {metrics && (
        <Link to="/llmops" className="card p-4 flex items-center gap-6 hover:border-surface-700 transition-colors">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-brand-400" />
            <span className="text-sm font-medium text-white">LLM Activity (24h)</span>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <span className="text-surface-200">{metrics.total_calls} calls</span>
            <span className="text-surface-200">{metrics.avg_latency_ms}ms avg</span>
            <span className="text-emerald-400">{formatCost(metrics.total_cost_usd)}</span>
            <span className="text-surface-200">{metrics.success_rate}% success</span>
          </div>
          <ArrowRight className="w-4 h-4 text-surface-200 ml-auto" />
        </Link>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { to: '/documents', icon: FileText, title: 'Upload PDF', desc: 'Add documents to your library', color: 'text-brand-400' },
          { to: '/chat', icon: MessageSquare, title: 'Chat with AI', desc: 'Ask questions about your documents', color: 'text-violet-400' },
          { to: '/search', icon: Search, title: 'Semantic Search', desc: 'Find content across all documents', color: 'text-emerald-400' },
        ].map(({ to, icon: Icon, title, desc, color }) => (
          <Link key={to} to={to} className="card p-5 hover:border-surface-700 transition-colors group">
            <Icon className={`w-6 h-6 ${color} mb-3`} />
            <h3 className="font-semibold text-white text-sm">{title}</h3>
            <p className="text-xs text-surface-200 mt-1">{desc}</p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Recent Documents</h2>
            <Link to="/documents" className="text-xs text-brand-400 hover:text-brand-300">View all</Link>
          </div>
          {recentDocs.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="w-8 h-8 text-surface-200 mx-auto mb-2" />
              <p className="text-sm text-surface-200">No documents yet</p>
              <Link to="/documents" className="text-xs text-brand-400 hover:underline mt-1 inline-block">Upload your first PDF →</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {recentDocs.map((doc) => (
                <div key={doc.id} className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0"><FileText className="w-4 h-4 text-brand-400" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{doc.title}</p>
                    <p className="text-xs text-surface-200">{formatRelative(doc.created_at)}</p>
                  </div>
                  <span className={`status-${doc.status}`}>{doc.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Recent Conversations</h2>
            <Link to="/chat" className="text-xs text-brand-400 hover:text-brand-300">View all</Link>
          </div>
          {recentChats.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-8 h-8 text-surface-200 mx-auto mb-2" />
              <p className="text-sm text-surface-200">No conversations yet</p>
              <Link to="/chat" className="text-xs text-brand-400 hover:underline mt-1 inline-block">Start chatting →</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {recentChats.map((chat) => (
                <Link key={chat.id} to={`/chat/${chat.id}`} className="flex items-center gap-3 group">
                  <div className="w-8 h-8 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0"><Brain className="w-4 h-4 text-violet-400" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate group-hover:text-brand-300 transition-colors">{chat.title}</p>
                    <p className="text-xs text-surface-200">{chat.message_count} messages · {formatRelative(chat.updated_at)}</p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
