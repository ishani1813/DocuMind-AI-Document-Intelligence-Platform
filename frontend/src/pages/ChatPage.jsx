import { useState, useRef, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Brain, Sparkles, FileText } from 'lucide-react'
import { chatApi, documentsApi } from '../services/api'
import MessageBubble, { TypingIndicator } from '../components/chat/MessageBubble'
import ChatInput from '../components/chat/ChatInput'
import SessionList from '../components/chat/SessionList'
import { Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { toastError } from '../utils/formatters'

export default function ChatPage() {
  const { id: sessionId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const bottomRef = useRef(null)
  const [selectedDocIds, setSelectedDocIds] = useState([])
  const [sending, setSending] = useState(false)

  const { data: sessionsData } = useQuery({ queryKey: ['chatSessions'], queryFn: () => chatApi.listSessions() })
  const { data: messagesData, isLoading: loadingMsgs } = useQuery({
    queryKey: ['chatMessages', sessionId], queryFn: () => chatApi.getMessages(sessionId), enabled: !!sessionId,
  })
  const { data: docsData } = useQuery({ queryKey: ['documents'], queryFn: () => documentsApi.list() })

  const sessions = sessionsData?.data || []
  const messages = messagesData?.data || []
  const readyDocs = (docsData?.data || []).filter((d) => d.status === 'ready')

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, sending])

  const createSession = useMutation({
    mutationFn: () => chatApi.createSession({ title: 'New Conversation' }),
    onSuccess: (res) => { qc.invalidateQueries({ queryKey: ['chatSessions'] }); navigate(`/chat/${res.data.id}`) },
  })

  const deleteSession = useMutation({
    mutationFn: (id) => chatApi.deleteSession(id),
    onSuccess: (_, id) => { qc.invalidateQueries({ queryKey: ['chatSessions'] }); if (id === sessionId) navigate('/chat') },
  })

  const handleSend = async (content) => {
    setSending(true)
    const fakeId = `temp-${Date.now()}`
    qc.setQueryData(['chatMessages', sessionId], (old) => ({
      ...old, data: [...(old?.data || []), { id: fakeId, role: 'user', content, sources: null, created_at: new Date().toISOString(), _optimistic: true }],
    }))
    try {
      await chatApi.sendMessage(sessionId, { content, document_ids: selectedDocIds.length ? selectedDocIds : null })
      await qc.invalidateQueries({ queryKey: ['chatMessages', sessionId] })
      await qc.invalidateQueries({ queryKey: ['chatSessions'] })
    } catch (err) {
      toast.error(toastError(err))
      qc.setQueryData(['chatMessages', sessionId], (old) => ({ ...old, data: (old?.data || []).filter((m) => m.id !== fakeId) }))
    } finally { setSending(false) }
  }

  const toggleDoc = (id) => setSelectedDocIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])

  return (
    <div className="flex h-full overflow-hidden">
      <aside className="hidden md:flex flex-col w-64 border-r border-surface-800 bg-surface-900/50 flex-shrink-0">
        <SessionList sessions={sessions} activeId={sessionId} onNew={() => createSession.mutate()} onDelete={(id) => deleteSession.mutate(id)} isCreating={createSession.isPending} />
      </aside>

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {!sessionId ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-600 to-brand-800 flex items-center justify-center mb-6 shadow-2xl shadow-brand-900/50">
              <Sparkles className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Chat with your documents</h2>
            <p className="text-surface-200 text-sm max-w-md mb-2">Upload PDFs, then ask questions in natural language. Every answer includes source citations.</p>
            {readyDocs.length === 0 ? (
              <div className="mt-6 card p-5 text-left max-w-sm">
                <p className="text-sm font-medium text-white mb-1">No documents yet</p>
                <p className="text-xs text-surface-200 mb-3">Upload a PDF first, then start chatting.</p>
                <Link to="/documents" className="btn-primary text-sm"><FileText className="w-4 h-4" />Upload Documents</Link>
              </div>
            ) : (
              <button onClick={() => createSession.mutate()} className="btn-primary mt-6 px-6 py-2.5"><Sparkles className="w-4 h-4" />Start a conversation</button>
            )}
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
                {loadingMsgs && <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 text-brand-400 animate-spin" /></div>}
                {!loadingMsgs && messages.length === 0 && (
                  <div className="text-center py-16">
                    <Brain className="w-10 h-10 text-surface-200 mx-auto mb-3 opacity-50" />
                    <p className="text-surface-200 text-sm">Ask a question about your documents</p>
                  </div>
                )}
                {messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)}
                {sending && <TypingIndicator />}
                <div ref={bottomRef} />
              </div>
            </div>
            <ChatInput
              onSend={handleSend} isSending={sending} disabled={readyDocs.length === 0}
              readyDocs={readyDocs} selectedDocIds={selectedDocIds} onDocToggle={toggleDoc} onClearDocs={() => setSelectedDocIds([])}
              placeholder={readyDocs.length === 0 ? 'Upload documents first to start chatting…' : 'Ask a question about your documents…'}
            />
          </>
        )}
      </div>
    </div>
  )
}
