import { useState } from 'react'
import { Brain, Tag, AlignLeft, Users, TrendingUp, Key, ChevronDown, ChevronUp, Loader2, Sparkles, BarChart2, FileText, Zap } from 'lucide-react'
import { mlApi } from '../services/api'
import { useQuery } from '@tanstack/react-query'
import { documentsApi } from '../services/api'
import { formatScore, scoreColor } from '../utils/formatters'
import clsx from 'clsx'
import toast from 'react-hot-toast'

function SectionCard({ icon: Icon, title, color, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 p-4 hover:bg-surface-800/50 transition-colors">
        <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center flex-shrink-0`}><Icon className="w-4 h-4 text-white" /></div>
        <span className="font-semibold text-white flex-1 text-left">{title}</span>
        {open ? <ChevronUp className="w-4 h-4 text-surface-200" /> : <ChevronDown className="w-4 h-4 text-surface-200" />}
      </button>
      {open && <div className="px-4 pb-4 pt-1 border-t border-surface-800">{children}</div>}
    </div>
  )
}

function ClassificationResult({ data }) {
  if (!data) return null
  return (
    <div className="space-y-3 pt-3">
      <div className="flex items-center gap-3"><span className="text-2xl font-bold text-white">{data.top_label}</span><span className={clsx('text-sm font-mono font-semibold', scoreColor(data.top_score))}>{formatScore(data.top_score)}</span></div>
      <div className="space-y-2">
        {(data.all_labels || []).map((item) => (
          <div key={item.label} className="flex items-center gap-3">
            <span className="text-xs text-surface-200 w-28 truncate">{item.label}</span>
            <div className="flex-1 h-2 bg-surface-800 rounded-full overflow-hidden"><div className="h-full bg-brand-500 rounded-full transition-all" style={{ width: `${Math.round(item.score * 100)}%` }} /></div>
            <span className="text-xs text-surface-200 w-10 text-right font-mono">{Math.round(item.score * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function SummaryResult({ data }) {
  if (!data) return null
  return (
    <div className="pt-3 space-y-2">
      <p className="text-sm text-surface-100 leading-relaxed">{data.summary}</p>
      <div className="flex items-center gap-4 text-xs text-surface-200"><span className="capitalize">{data.mode} summary</span><span>{data.word_count} words</span></div>
    </div>
  )
}

function KeywordsResult({ data }) {
  if (!data) return null
  const keywords = data.keywords || []
  return (
    <div className="pt-3 space-y-3">
      <div className="flex flex-wrap gap-2">
        {keywords.slice(0, 20).map((kw, i) => (
          <span key={kw.keyword} className="px-2.5 py-1 rounded-full text-xs font-medium bg-brand-600/20 text-brand-300 border border-brand-500/30" style={{ opacity: 0.4 + (1 - i / keywords.length) * 0.6 }}>{kw.keyword}</span>
        ))}
      </div>
    </div>
  )
}

function EntitiesResult({ data }) {
  if (!data) return null
  const byType = data.by_type || {}
  const typeColors = { Person: 'bg-amber-500/20 text-amber-300 border-amber-500/30', Organization: 'bg-blue-500/20 text-blue-300 border-blue-500/30', Date: 'bg-purple-500/20 text-purple-300 border-purple-500/30', Money: 'bg-green-500/20 text-green-300 border-green-500/30', Percent: 'bg-orange-500/20 text-orange-300 border-orange-500/30' }
  return (
    <div className="pt-3 space-y-3">
      {Object.entries(byType).map(([type, names]) => (
        <div key={type}>
          <p className="text-xs font-medium text-surface-200 mb-1.5">{type}</p>
          <div className="flex flex-wrap gap-1.5">{names.map((name) => <span key={name} className={`px-2 py-0.5 rounded-full text-xs border ${typeColors[type] || 'bg-surface-700 text-surface-200 border-surface-600'}`}>{name}</span>)}</div>
        </div>
      ))}
    </div>
  )
}

function SentimentResult({ data }) {
  if (!data) return null
  const isPos = data.label === 'POSITIVE', isNeg = data.label === 'NEGATIVE'
  const color = isPos ? 'text-emerald-400' : isNeg ? 'text-red-400' : 'text-yellow-400'
  return (
    <div className="pt-3 space-y-3">
      <div className="flex items-center gap-3"><span className={clsx('text-2xl font-bold', color)}>{isPos ? '😊 Positive' : isNeg ? '😞 Negative' : '😐 Neutral'}</span><span className="text-sm text-surface-200 font-mono">{formatScore(data.score)}</span></div>
      <div className="flex items-center gap-2"><span className="text-xs text-surface-200 w-16">Positive</span><div className="flex-1 h-2 bg-surface-800 rounded-full overflow-hidden"><div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.round((data.breakdown?.positive || 0) * 100)}%` }} /></div></div>
      <div className="flex items-center gap-2"><span className="text-xs text-surface-200 w-16">Negative</span><div className="flex-1 h-2 bg-surface-800 rounded-full overflow-hidden"><div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.round((data.breakdown?.negative || 0) * 100)}%` }} /></div></div>
    </div>
  )
}

function StatsResult({ data }) {
  if (!data) return null
  const s = data.stats || {}, r = data.readability || {}
  const items = [{ label: 'Words', value: s.word_count }, { label: 'Sentences', value: s.sentence_count }, { label: 'Paragraphs', value: s.paragraph_count }, { label: 'Reading Time', value: `${s.reading_time_min} min` }, { label: 'Readability', value: r.level }, { label: 'FK Score', value: r.score }]
  return <div className="pt-3 grid grid-cols-2 sm:grid-cols-3 gap-3">{items.map((item) => <div key={item.label} className="bg-surface-800 rounded-lg p-3"><p className="text-xs text-surface-200">{item.label}</p><p className="text-sm font-semibold text-white mt-0.5 truncate">{item.value || '—'}</p></div>)}</div>
}

export default function MLInsightsPage() {
  const { data: docsData } = useQuery({ queryKey: ['documents'], queryFn: () => documentsApi.list() })
  const readyDocs = (docsData?.data || []).filter((d) => d.status === 'ready')
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState({})
  const [results, setResults] = useState({})

  const docText = inputText

  const runML = async (type) => {
    if (!docText.trim()) { toast.error('Enter text first'); return }
    setLoading((l) => ({ ...l, [type]: true }))
    try {
      let res
      if (type === 'classify') res = await mlApi.classify({ text: docText })
      if (type === 'summarize') res = await mlApi.summarize({ text: docText, mode: 'extractive', max_sentences: 5 })
      if (type === 'keywords') res = await mlApi.keywords({ text: docText, top_n: 20 })
      if (type === 'entities') res = await mlApi.entities({ text: docText })
      if (type === 'sentiment') res = await mlApi.sentiment({ text: docText })
      if (type === 'stats') res = await mlApi.stats({ text: docText })
      setResults((r) => ({ ...r, [type]: res.data }))
    } catch (err) { toast.error(`${type} failed`) } finally { setLoading((l) => ({ ...l, [type]: false })) }
  }

  const runAll = async () => { for (const t of ['classify', 'summarize', 'keywords', 'entities', 'sentiment', 'stats']) await runML(t) }
  const anyLoading = Object.values(loading).some(Boolean)

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-white flex items-center gap-2"><Brain className="w-6 h-6 text-brand-400" /> ML Insights</h1><p className="text-surface-200 text-sm mt-0.5">AI-powered document analysis</p></div>
        <button onClick={runAll} disabled={anyLoading || !docText.trim()} className="btn-primary">{anyLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}Analyse All</button>
      </div>

      <div className="card p-4 bg-brand-600/5 border-brand-500/20">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs">
          {[{ label: 'Zero-Shot Classification', sub: 'BART-large-MNLI' }, { label: 'Named Entity Recognition', sub: 'BERT-base-NER' }, { label: 'Cross-Encoder Re-ranking', sub: 'MiniLM-L6' }, { label: 'HyDE Query Rewriting', sub: 'GPT-3.5/Mistral' }].map((item) => (
            <div key={item.label} className="space-y-1"><p className="text-white font-medium leading-tight">{item.label}</p><p className="text-surface-200">{item.sub}</p></div>
          ))}
        </div>
      </div>

      <div className="card p-4 space-y-3">
        <p className="text-sm font-medium text-white">Input Text</p>
        {readyDocs.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <span className="text-xs text-surface-200 self-center">Quick fill:</span>
            {readyDocs.slice(0, 5).map((doc) => (
              <button key={doc.id} onClick={() => { setSelectedDoc(doc); setInputText(`Document Title: ${doc.title}\n\nThis document contains ${doc.chunk_count} chunks across ${doc.page_count} pages.`) }} className={clsx('text-xs px-3 py-1.5 rounded-full border transition-colors truncate max-w-[180px]', selectedDoc?.id === doc.id ? 'bg-brand-600/20 border-brand-500 text-brand-300' : 'border-surface-700 text-surface-200 hover:border-surface-600')}>
                <FileText className="w-3 h-3 inline mr-1" />{doc.title}
              </button>
            ))}
          </div>
        )}
        <textarea value={inputText} onChange={(e) => { setInputText(e.target.value); setSelectedDoc(null) }} placeholder="Paste any text here to analyse it…" rows={6} className="input-field resize-none font-mono text-xs" />
        <div className="flex justify-between items-center text-xs text-surface-200">
          <span>{inputText.split(/\s+/).filter(Boolean).length} words</span>
          {inputText && <button onClick={() => { setInputText(''); setSelectedDoc(null); setResults({}) }} className="hover:text-white">Clear</button>}
        </div>
      </div>

      <div className="space-y-3">
        <SectionCard icon={Tag} title="Document Classification" color="bg-brand-600">
          <div className="flex justify-end pt-2"><button onClick={() => runML('classify')} disabled={loading.classify} className="btn-secondary text-xs py-1.5">{loading.classify ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}Run</button></div>
          {results.classify ? <ClassificationResult data={results.classify} /> : <p className="text-xs text-surface-200 pt-2">Zero-shot classification using BART-large-MNLI</p>}
        </SectionCard>

        <SectionCard icon={AlignLeft} title="Summarization" color="bg-violet-600">
          <div className="flex justify-end pt-2"><button onClick={() => runML('summarize')} disabled={loading.summarize} className="btn-secondary text-xs py-1.5">{loading.summarize ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}Run</button></div>
          {results.summarize ? <SummaryResult data={results.summarize} /> : <p className="text-xs text-surface-200 pt-2">Extractive TF-IDF + abstractive BART-large-CNN</p>}
        </SectionCard>

        <SectionCard icon={Key} title="Keyword Extraction" color="bg-amber-600">
          <div className="flex justify-end pt-2"><button onClick={() => runML('keywords')} disabled={loading.keywords} className="btn-secondary text-xs py-1.5">{loading.keywords ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}Run</button></div>
          {results.keywords ? <KeywordsResult data={results.keywords} /> : <p className="text-xs text-surface-200 pt-2">TF-IDF + YAKE statistical keyphrase mining</p>}
        </SectionCard>

        <SectionCard icon={Users} title="Named Entity Recognition" color="bg-emerald-600">
          <div className="flex justify-end pt-2"><button onClick={() => runML('entities')} disabled={loading.entities} className="btn-secondary text-xs py-1.5">{loading.entities ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}Run</button></div>
          {results.entities ? <EntitiesResult data={results.entities} /> : <p className="text-xs text-surface-200 pt-2">BERT-base-NER — persons, orgs, dates, money</p>}
        </SectionCard>

        <SectionCard icon={TrendingUp} title="Sentiment Analysis" color="bg-rose-600">
          <div className="flex justify-end pt-2"><button onClick={() => runML('sentiment')} disabled={loading.sentiment} className="btn-secondary text-xs py-1.5">{loading.sentiment ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}Run</button></div>
          {results.sentiment ? <SentimentResult data={results.sentiment} /> : <p className="text-xs text-surface-200 pt-2">DistilBERT fine-tuned on SST-2</p>}
        </SectionCard>

        <SectionCard icon={BarChart2} title="Text Statistics & Readability" color="bg-cyan-600">
          <div className="flex justify-end pt-2"><button onClick={() => runML('stats')} disabled={loading.stats} className="btn-secondary text-xs py-1.5">{loading.stats ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}Run</button></div>
          {results.stats ? <StatsResult data={results.stats} /> : <p className="text-xs text-surface-200 pt-2">Word count, Flesch-Kincaid readability</p>}
        </SectionCard>
      </div>
    </div>
  )
}
