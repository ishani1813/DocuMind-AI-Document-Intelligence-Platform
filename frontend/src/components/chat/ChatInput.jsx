import { useRef, useState } from 'react'
import { Send, Loader2, ChevronDown, ChevronUp, Filter } from 'lucide-react'
import clsx from 'clsx'

export default function ChatInput({ onSend, isSending, disabled, readyDocs = [], selectedDocIds = [], onDocToggle, onClearDocs, placeholder }) {
  const [value, setValue] = useState('')
  const [showFilter, setShowFilter] = useState(false)
  const ref = useRef(null)

  const submit = () => {
    const trimmed = value.trim()
    if (!trimmed || isSending || disabled) return
    onSend(trimmed)
    setValue('')
    ref.current?.focus()
  }

  const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }
  const autoResize = (e) => { e.target.style.height = 'auto'; e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px` }

  return (
    <div className="border-t border-surface-800 bg-surface-900/80 backdrop-blur-sm">
      {readyDocs.length > 0 && (
        <div className="px-4 pt-3 pb-0">
          <div className="flex items-center gap-2">
            <button onClick={() => setShowFilter(!showFilter)} className={clsx('flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border transition-colors', selectedDocIds.length > 0 ? 'border-brand-500 text-brand-300 bg-brand-600/10' : 'border-surface-700 text-surface-200 hover:border-surface-600')}>
              <Filter className="w-3 h-3" />{selectedDocIds.length > 0 ? `${selectedDocIds.length} doc${selectedDocIds.length > 1 ? 's' : ''}` : 'All docs'}
              {showFilter ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {selectedDocIds.length > 0 && <button onClick={onClearDocs} className="text-xs text-surface-200 hover:text-white">Clear</button>}
          </div>
          {showFilter && (
            <div className="flex flex-wrap gap-2 mt-2 pb-2 animate-slide-up">
              {readyDocs.map((doc) => (
                <button key={doc.id} onClick={() => onDocToggle(doc.id)} className={clsx('text-xs px-3 py-1 rounded-full border transition-colors truncate max-w-[200px]', selectedDocIds.includes(doc.id) ? 'bg-brand-600/20 border-brand-500 text-brand-300' : 'border-surface-700 text-surface-200 hover:border-surface-500')}>
                  {doc.title}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="flex items-end gap-3 p-4">
        <textarea ref={ref} value={value} onChange={(e) => { setValue(e.target.value); autoResize(e) }} onKeyDown={handleKeyDown} placeholder={placeholder} disabled={isSending || disabled} rows={1}
          className="flex-1 bg-surface-800 border border-surface-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-surface-200 resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-colors disabled:opacity-50 min-h-[44px] max-h-40 overflow-y-auto"
          style={{ height: '44px' }} />
        <button onClick={submit} disabled={!value.trim() || isSending || disabled} className="flex-shrink-0 w-11 h-11 rounded-xl bg-brand-600 hover:bg-brand-500 text-white flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
          {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
      <p className="text-center text-[10px] text-surface-200 pb-2">Enter to send · Shift+Enter for newline · Answers include source citations</p>
    </div>
  )
}
