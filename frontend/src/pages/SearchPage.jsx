import { useState } from 'react'
import { Search, Loader2, BookOpen, ChevronDown, ChevronUp, Sliders, X } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { searchApi, documentsApi } from '../services/api'
import { formatScore, scoreColor, scoreBarColor, truncate, toastError } from '../utils/formatters'
import toast from 'react-hot-toast'
import clsx from 'clsx'

function ResultCard({ result, index }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = result.chunk_text?.length > 280
  return (
    <div className="card hover:border-surface-700 transition-colors animate-slide-up" style={{ animationDelay: `${index * 50}ms` }}>
      <div className="h-0.5 rounded-t-xl overflow-hidden"><div className={clsx('h-full', scoreBarColor(result.relevance_score))} style={{ width: `${Math.round(result.relevance_score * 100)}%` }} /></div>
      <div className="p-4">
        <div className="flex items-start gap-3">
          <span className="w-6 h-6 rounded-full bg-brand-600/20 text-brand-300 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{index + 1}</span>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-sm font-semibold text-white truncate">{result.document_title}</span>
              <span className="text-xs text-surface-200 bg-surface-800 px-2 py-0.5 rounded-full flex-shrink-0">Page {result.page_number}</span>
              <span className={clsx('text-xs font-mono font-semibold flex-shrink-0', scoreColor(result.relevance_score))}>{formatScore(result.relevance_score)} match</span>
            </div>
            <p className="text-sm text-surface-100 leading-relaxed">{expanded || !isLong ? result.chunk_text : truncate(result.chunk_text, 280)}</p>
            {isLong && (
              <button onClick={() => setExpanded(!expanded)} className="mt-2 text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
                {expanded ? <><ChevronUp className="w-3 h-3" /> Show less</> : <><ChevronDown className="w-3 h-3" /> Read more</>}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [selectedDocIds, setSelectedDocIds] = useState([])
  const [showFilters, setShowFilters] = useState(false)
  const [results, setResults] = useState(null)
  const [isSearching, setIsSearching] = useState(false)
  const [lastQuery, setLastQuery] = useState('')

  const { data: docsData } = useQuery({ queryKey: ['documents'], queryFn: () => documentsApi.list() })
  const readyDocs = (docsData?.data || []).filter((d) => d.status === 'ready')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setIsSearching(true)
    setLastQuery(query.trim())
    try {
      const res = await searchApi.semantic({ query: query.trim(), top_k: topK, document_ids: selectedDocIds.length ? selectedDocIds : null })
      setResults(res.data)
    } catch (err) { toast.error(toastError(err)) } finally { setIsSearching(false) }
  }

  const toggleDoc = (id) => setSelectedDocIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Semantic Search</h1>
        <p className="text-surface-200 text-sm mt-0.5">Find passages across your documents using AI-powered vector similarity search</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-200 pointer-events-none" />
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="What are the key findings?" className="input-field pl-10 py-3" />
            {query && <button type="button" onClick={() => { setQuery(''); setResults(null) }} className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-200 hover:text-white"><X className="w-4 h-4" /></button>}
          </div>
          <button type="submit" className="btn-primary px-5 flex-shrink-0" disabled={isSearching || !query.trim()}>
            {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span className="hidden sm:inline">{isSearching ? 'Searching…' : 'Search'}</span>
          </button>
          <button type="button" onClick={() => setShowFilters(!showFilters)} className={clsx('btn-secondary flex-shrink-0', showFilters && 'border-brand-500 text-brand-300')}><Sliders className="w-4 h-4" /></button>
        </div>

        {showFilters && (
          <div className="card p-4 space-y-4 animate-slide-up">
            <div>
              <label className="block text-xs font-medium text-surface-100 mb-2">Results to return: <span className="text-brand-400 font-mono">{topK}</span></label>
              <input type="range" min={1} max={20} value={topK} onChange={(e) => setTopK(Number(e.target.value))} className="w-full accent-brand-500" />
            </div>
            {readyDocs.length > 0 && (
              <div>
                <p className="text-xs font-medium text-surface-100 mb-2">Scope to documents <span className="text-surface-200 font-normal">(empty = all)</span></p>
                <div className="flex flex-wrap gap-2">
                  {readyDocs.map((doc) => (
                    <button key={doc.id} type="button" onClick={() => toggleDoc(doc.id)} className={clsx('text-xs px-3 py-1.5 rounded-full border transition-colors max-w-[200px] truncate', selectedDocIds.includes(doc.id) ? 'bg-brand-600/20 border-brand-500 text-brand-300' : 'border-surface-700 text-surface-200 hover:border-surface-600')}>{doc.title}</button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </form>

      {results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-white">{results.total} result{results.total !== 1 ? 's' : ''}</h2>
              <p className="text-xs text-surface-200 mt-0.5">for <em className="text-brand-300 not-italic">"{lastQuery}"</em></p>
            </div>
          </div>
          {results.total === 0 ? (
            <div className="card p-12 text-center">
              <BookOpen className="w-10 h-10 text-surface-200 mx-auto mb-3" />
              <p className="font-medium text-white">No matching passages found</p>
              <p className="text-sm text-surface-200 mt-1">Try rephrasing, or upload more documents</p>
            </div>
          ) : (
            <div className="space-y-3">{results.results.map((r, i) => <ResultCard key={i} result={r} index={i} />)}</div>
          )}
        </div>
      )}

      {!results && !isSearching && (
        <div className="text-center py-24">
          <div className="w-16 h-16 rounded-2xl bg-surface-800 flex items-center justify-center mx-auto mb-4"><Search className="w-8 h-8 text-surface-200" /></div>
          <h3 className="font-semibold text-white mb-2">Semantic document search</h3>
          <p className="text-sm text-surface-200 max-w-sm mx-auto">No keyword matching — the AI understands the meaning of your query</p>
        </div>
      )}
    </div>
  )
}
