import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, MessageSquare, Loader2 } from 'lucide-react'
import { formatRelative } from '../../utils/formatters'
import clsx from 'clsx'

export default function SessionList({ sessions = [], activeId, onNew, onDelete, isCreating }) {
  const navigate = useNavigate()
  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-surface-800">
        <button onClick={onNew} disabled={isCreating} className="btn-primary w-full justify-center py-2">
          {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}New Chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {sessions.length === 0 ? (
          <div className="text-center py-10 px-3">
            <MessageSquare className="w-7 h-7 text-surface-200 mx-auto mb-2 opacity-50" />
            <p className="text-xs text-surface-200">No conversations yet</p>
          </div>
        ) : sessions.map((s) => (
          <div key={s.id} onClick={() => navigate(`/chat/${s.id}`)} className={clsx('group flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg cursor-pointer transition-colors', s.id === activeId ? 'bg-brand-600/20 border border-brand-500/30' : 'hover:bg-surface-800')}>
            <MessageSquare className={clsx('w-3.5 h-3.5 flex-shrink-0', s.id === activeId ? 'text-brand-400' : 'text-surface-200')} />
            <div className="flex-1 min-w-0">
              <p className={clsx('text-xs font-medium truncate', s.id === activeId ? 'text-brand-300' : 'text-surface-100')}>{s.title}</p>
              <p className="text-[10px] text-surface-200 mt-0.5">{s.message_count} msg{s.message_count !== 1 ? 's' : ''} · {formatRelative(s.updated_at)}</p>
            </div>
            <button onClick={(e) => { e.stopPropagation(); onDelete(s.id) }} className="opacity-0 group-hover:opacity-100 text-surface-200 hover:text-red-400 transition-all p-0.5 flex-shrink-0"><Trash2 className="w-3.5 h-3.5" /></button>
          </div>
        ))}
      </div>
    </div>
  )
}
