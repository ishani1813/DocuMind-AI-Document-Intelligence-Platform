import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, DollarSign, Clock, CheckCircle, AlertTriangle, Zap, TrendingUp, Database, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { llmopsApi } from '../services/api'
import { formatCost, formatMs, formatRelative } from '../utils/formatters'
import clsx from 'clsx'

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4']

function MetricCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center flex-shrink-0`}><Icon className="w-4 h-4 text-white" /></div>
        <span className="text-xs text-surface-200">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-surface-200 mt-1">{sub}</p>}
    </div>
  )
}

function AlertBadge({ severity }) {
  const config = {
    critical: 'bg-red-500/20 text-red-300 border-red-500/30',
    warning: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    info: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  }
  return <span className={clsx('badge border', config[severity] || config.info)}>{severity}</span>
}

function CallLogRow({ call }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="border-b border-surface-800 last:border-0">
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center gap-3 p-3 hover:bg-surface-800/50 transition-colors text-left">
        <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', call.success ? 'bg-emerald-500' : 'bg-red-500')} />
        <span className="text-xs font-mono text-surface-200 w-32 truncate">{call.operation}</span>
        <span className="text-xs text-brand-300 w-32 truncate">{call.model}</span>
        <span className="text-xs text-surface-200 ml-auto flex-shrink-0">{formatMs(call.latency_ms)}</span>
        <span className="text-xs text-emerald-400 w-16 text-right flex-shrink-0">{formatCost(call.estimated_cost_usd)}</span>
        <span className="text-[10px] text-surface-200 w-20 text-right flex-shrink-0">{formatRelative(call.created_at)}</span>
        {expanded ? <ChevronUp className="w-3 h-3 text-surface-200" /> : <ChevronDown className="w-3 h-3 text-surface-200" />}
      </button>
      {expanded && (
        <div className="px-3 pb-3 pl-8 space-y-1.5 animate-slide-up">
          <div className="flex gap-4 text-xs">
            <span className="text-surface-200">Tokens: <span className="text-white">{call.total_tokens}</span></span>
            {call.used_hyde && <span className="text-violet-400">HyDE used</span>}
            {call.used_rerank && <span className="text-cyan-400">Re-ranked</span>}
          </div>
          {call.error_message && <p className="text-xs text-red-400">{call.error_message}</p>}
        </div>
      )}
    </div>
  )
}

export default function LLMOpsPage() {
  const [hours, setHours] = useState(24)

  const { data: overview, refetch: refetchOverview } = useQuery({ queryKey: ['llmops-overview', hours], queryFn: () => llmopsApi.overview(hours) })
  const { data: latency } = useQuery({ queryKey: ['llmops-latency', hours], queryFn: () => llmopsApi.latency(hours) })
  const { data: costByModel } = useQuery({ queryKey: ['llmops-cost-model', hours], queryFn: () => llmopsApi.costByModel(hours) })
  const { data: timeseries } = useQuery({ queryKey: ['llmops-timeseries', hours], queryFn: () => llmopsApi.costTimeseries(hours) })
  const { data: recentCalls } = useQuery({ queryKey: ['llmops-calls'], queryFn: () => llmopsApi.recentCalls(30), refetchInterval: 10000 })
  const { data: alerts } = useQuery({ queryKey: ['llmops-alerts'], queryFn: () => llmopsApi.alerts(), refetchInterval: 15000 })

  const m = overview?.data
  const l = latency?.data
  const costModels = costByModel?.data || []
  const ts = (timeseries?.data || []).map((t) => ({ ...t, time: new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }))
  const calls = recentCalls?.data || []
  const activeAlerts = alerts?.data || []

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Activity className="w-6 h-6 text-brand-400" /> LLMOps Dashboard</h1>
          <p className="text-surface-200 text-sm mt-0.5">Observability for every LLM call — cost, latency, quality, and experiments</p>
        </div>
        <div className="flex items-center gap-2">
          {[6, 24, 72, 168].map((h) => (
            <button key={h} onClick={() => setHours(h)} className={clsx('text-xs px-3 py-1.5 rounded-lg border transition-colors', hours === h ? 'bg-brand-600/20 border-brand-500 text-brand-300' : 'border-surface-700 text-surface-200 hover:border-surface-600')}>
              {h < 24 ? `${h}h` : `${h/24}d`}
            </button>
          ))}
          <button onClick={() => refetchOverview()} className="btn-ghost"><RefreshCw className="w-4 h-4" /></button>
        </div>
      </div>

      {/* Alerts banner */}
      {activeAlerts.length > 0 && (
        <div className="card p-4 border-yellow-500/30 bg-yellow-500/5">
          <div className="flex items-center gap-2 mb-3"><AlertTriangle className="w-4 h-4 text-yellow-400" /><span className="text-sm font-medium text-white">{activeAlerts.length} Active Alert{activeAlerts.length > 1 ? 's' : ''}</span></div>
          <div className="space-y-2">
            {activeAlerts.slice(0, 5).map((alert) => (
              <div key={alert.id} className="flex items-center gap-3 text-sm">
                <AlertBadge severity={alert.severity} />
                <span className="text-surface-100 flex-1">{alert.message}</span>
                <span className="text-xs text-surface-200">{formatRelative(alert.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={Zap} label="Total Calls" value={m?.total_calls ?? '—'} sub={`Last ${hours}h`} color="bg-brand-600" />
        <MetricCard icon={DollarSign} label="Total Cost" value={m ? formatCost(m.total_cost_usd) : '—'} sub={`${m?.total_tokens?.toLocaleString() || 0} tokens`} color="bg-emerald-600" />
        <MetricCard icon={Clock} label="Avg Latency" value={m ? formatMs(m.avg_latency_ms) : '—'} sub={l ? `P95: ${formatMs(l.p95)}` : ''} color="bg-violet-600" />
        <MetricCard icon={CheckCircle} label="Success Rate" value={m ? `${m.success_rate}%` : '—'} sub="Request success" color="bg-cyan-600" />
      </div>

      {/* Latency percentiles */}
      {l && (
        <div className="card p-5">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2"><Clock className="w-4 h-4 text-brand-400" /> Latency Percentiles</h2>
          <div className="grid grid-cols-3 gap-4">
            {[{ label: 'P50', value: l.p50, color: 'text-emerald-400' }, { label: 'P95', value: l.p95, color: 'text-yellow-400' }, { label: 'P99', value: l.p99, color: 'text-red-400' }].map((p) => (
              <div key={p.label} className="bg-surface-800 rounded-lg p-4 text-center">
                <p className="text-xs text-surface-200 mb-1">{p.label}</p>
                <p className={clsx('text-xl font-bold font-mono', p.color)}>{formatMs(p.value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost timeseries */}
        <div className="card p-5">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-emerald-400" /> Cost Over Time</h2>
          {ts.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={ts}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
                <Line type="monotone" dataKey="cost_usd" stroke="#10b981" strokeWidth={2} dot={false} name="Cost ($)" />
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-surface-200 text-center py-16">No data yet — make some LLM calls to see trends</p>}
        </div>

        {/* Cost by model */}
        <div className="card p-5">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2"><Database className="w-4 h-4 text-violet-400" /> Cost by Model</h2>
          {costModels.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={costModels} dataKey="cost_usd" nameKey="model" cx="50%" cy="50%" outerRadius={80} label={({ model, cost_usd }) => `${model}: ${formatCost(cost_usd)}`} labelLine={false}>
                  {costModels.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-surface-200 text-center py-16">No data yet</p>}
        </div>
      </div>

      {/* Model breakdown table */}
      {costModels.length > 0 && (
        <div className="card overflow-hidden">
          <div className="p-4 border-b border-surface-800"><h2 className="font-semibold text-white">Model Breakdown</h2></div>
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-surface-200 border-b border-surface-800"><th className="px-4 py-2">Model</th><th className="px-4 py-2">Calls</th><th className="px-4 py-2">Tokens</th><th className="px-4 py-2">Cost</th></tr></thead>
            <tbody>
              {costModels.map((m, i) => (
                <tr key={i} className="border-b border-surface-800 last:border-0">
                  <td className="px-4 py-2.5 text-white">{m.model}</td>
                  <td className="px-4 py-2.5 text-surface-200">{m.calls}</td>
                  <td className="px-4 py-2.5 text-surface-200">{m.tokens.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-emerald-400 font-mono">{formatCost(m.cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Recent calls log */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-surface-800 flex items-center justify-between">
          <h2 className="font-semibold text-white">Recent LLM Calls</h2>
          <span className="text-xs text-surface-200">Live · auto-refreshes every 10s</span>
        </div>
        {calls.length === 0 ? (
          <p className="text-sm text-surface-200 text-center py-12">No calls logged yet — use Chat or ML Insights to generate activity</p>
        ) : (
          <div className="max-h-96 overflow-y-auto">{calls.map((call) => <CallLogRow key={call.id} call={call} />)}</div>
        )}
      </div>
    </div>
  )
}
