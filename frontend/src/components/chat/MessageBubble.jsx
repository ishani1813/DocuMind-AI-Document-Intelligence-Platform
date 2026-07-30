import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Brain, User, BookOpen, ChevronDown, ChevronUp } from 'lucide-react'
import { formatRelative, formatScore, scoreColor, scoreBarColor, truncate } from '../../utils/formatters'
import clsx from 'clsx'

export function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 animate-fade-in">
      <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center flex-shrink-0"><Brain className="w-3.5 h-3.5 text-white" /></div>
      <div className="bg-surface-800 border border-surface-700 rounded-2xl rounded-bl-sm px-4 py-3.5">
        <div className="flex items-center gap-1.5">
          <span className="typing-dot w-1.5 h-1.5 bg-brand-400 rounded-full" />
          <span className="typing-dot w-1.5 h-1.5 bg-brand-400 rounded-full" />
          <span className="typing-dot w-1.5 h-1.5 bg-brand-400 rounded-full" />
        </div>
      </div>
    </div>
  )
}

function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = source.chunk_text?.length > 250
  return (
    <div className="bg-surface-900 border border-surface-700/60 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 bg-surface-800/60">
        <span className="w-5 h-5 rounded-full bg-brand-600/40 text-brand-300 text-[10px] font-bold flex items-center justify-center flex-shrink-0">{index + 1}</span>
        <p className="text-xs font-medium text-white truncate flex-1">{source.document_title}</p>
        <span className="text-[10px] text-surface-200 flex-shrink-0 bg-surface-700 px-1.5 py-0.5 rounded">p.{source.page_number}</span>
        <span className={clsx('text-[10px] font-mono font-semibold flex-shrink-0', scoreColor(source.relevance_score))}>{formatScore(source.relevance_score)}</span>
      </div>
      <div className="h-0.5 bg-surface-700"><div className={clsx('h-full', scoreBarColor(source.relevance_score))} style={{ width: `${Math.round(source.relevance_score * 100)}%` }} /></div>
      <div className="px-3 py-2.5">
        <p className="text-[11px] text-surface-200 leading-relaxed">{expanded || !isLong ? source.chunk_text : truncate(source.chunk_text, 250)}</p>
        {isLong && (
          <button onClick={() => setExpanded(!expanded)} className="mt-1.5 text-[10px] text-brand-400 hover:text-brand-300 flex items-center gap-0.5">
            {expanded ? <><ChevronUp className="w-3 h-3" /> Less</> : <><ChevronDown className="w-3 h-3" /> More</>}
          </button>
        )}
      </div>
    </div>
  )
}

function SourcePanel({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources?.length) return null
  return (
    <div className="w-full">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1.5 text-xs text-surface-200 hover:text-brand-300 transition-colors py-1">
        <BookOpen className="w-3.5 h-3.5" /><span>{sources.length} source{sources.length > 1 ? 's' : ''} cited</span>
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {open && <div className="mt-2 space-y-2 animate-slide-up">{sources.map((src, i) => <SourceCard key={i} source={src} index={i} />)}</div>}
    </div>
  )
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={clsx('flex items-end gap-2.5 animate-slide-up', isUser && 'flex-row-reverse')}>
      <div className={clsx('w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mb-5', isUser ? 'bg-surface-700' : 'bg-brand-600')}>
        {isUser ? <User className="w-3.5 h-3.5 text-white" /> : <Brain className="w-3.5 h-3.5 text-white" />}
      </div>
      <div className={clsx('max-w-[80%] flex flex-col', isUser ? 'items-end' : 'items-start')}>
        <div className={clsx('px-4 py-3 rounded-2xl text-sm leading-relaxed', isUser ? 'bg-brand-600 text-white rounded-br-sm' : 'bg-surface-800 border border-surface-700 text-surface-100 rounded-bl-sm', message._optimistic && 'opacity-70')}>
          {isUser ? <p className="whitespace-pre-wrap">{message.content}</p> : <div className="prose-chat"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown></div>}
        </div>
        {!isUser && message.sources?.length > 0 && <div className="mt-2 w-full"><SourcePanel sources={message.sources} /></div>}
        <p className={clsx('text-[10px] text-surface-200 mt-1.5 px-1', isUser ? 'text-right' : 'text-left')}>{formatRelative(message.created_at)}</p>
      </div>
    </div>
  )
}
