import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Upload, Trash2, RefreshCw, Eye, CheckCircle, XCircle, Loader2, X } from 'lucide-react'
import { documentsApi } from '../services/api'
import toast from 'react-hot-toast'
import { formatBytes, formatRelative, toastError } from '../utils/formatters'
import clsx from 'clsx'

function FilePreview({ file, status, onRemove }) {
  return (
    <div className="flex items-center gap-3 p-3 bg-surface-800 rounded-lg border border-surface-700">
      <div className="w-8 h-8 rounded-md bg-brand-600/20 flex items-center justify-center flex-shrink-0"><FileText className="w-4 h-4 text-brand-400" /></div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate">{file.name}</p>
        <p className="text-xs text-surface-200">{formatBytes(file.size)}</p>
      </div>
      {status === 'uploading' && <Loader2 className="w-4 h-4 text-brand-400 animate-spin flex-shrink-0" />}
      {status === 'done' && <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />}
      {status === 'error' && <span className="text-xs text-red-400">Failed</span>}
      {status === 'pending' && (
        <button onClick={() => onRemove(file)} className="text-surface-200 hover:text-red-400 transition-colors"><X className="w-4 h-4" /></button>
      )}
    </div>
  )
}

function UploadZone({ onUpload, disabled }) {
  const [queue, setQueue] = useState([])

  const processFiles = useCallback(async (acceptedFiles) => {
    if (!acceptedFiles?.length) return
    const entries = acceptedFiles.map((f) => ({ file: f, status: 'pending' }))
    setQueue((q) => [...q, ...entries])

    for (const entry of entries) {
      setQueue((q) => q.map((e) => e.file.name === entry.file.name ? { ...e, status: 'uploading' } : e))
      try {
        const formData = new FormData()
        formData.append('file', entry.file)
        formData.append('title', entry.file.name.replace(/\.pdf$/i, '').replace(/[_-]+/g, ' ').trim())
        await onUpload(formData)
        setQueue((q) => q.map((e) => e.file.name === entry.file.name ? { ...e, status: 'done' } : e))
      } catch {
        setQueue((q) => q.map((e) => e.file.name === entry.file.name ? { ...e, status: 'error' } : e))
      }
    }
    setTimeout(() => setQueue((q) => q.filter((e) => e.status !== 'done')), 2000)
  }, [onUpload])

  const onDrop = useCallback((accepted, rejected) => {
    if (rejected?.length) {
      rejected.forEach((r) => r.errors.forEach((e) => {
        if (e.code === 'file-too-large') toast.error(`${r.file.name} exceeds 50MB limit`)
        if (e.code === 'file-invalid-type') toast.error(`${r.file.name} is not a PDF`)
      }))
    }
    if (accepted?.length) processFiles(accepted)
  }, [processFiles])

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop, accept: { 'application/pdf': ['.pdf'] }, multiple: true, disabled, maxSize: 50 * 1024 * 1024,
  })

  const removeFromQueue = (file) => setQueue((q) => q.filter((e) => e.file.name !== file.name))

  return (
    <div className="space-y-3">
      <div {...getRootProps()} className={clsx(
        'relative border-2 border-dashed rounded-xl p-10 text-center transition-all duration-200 cursor-pointer',
        isDragActive && !isDragReject && 'border-brand-500 bg-brand-500/10',
        isDragReject && 'border-red-500 bg-red-500/10',
        !isDragActive && !disabled && 'border-surface-700 hover:border-surface-500 hover:bg-surface-800/40',
        disabled && 'opacity-50 cursor-not-allowed',
      )}>
        <input {...getInputProps()} />
        <div className={clsx('w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center', isDragActive ? 'bg-brand-600' : 'bg-surface-800')}>
          <Upload className={clsx('w-7 h-7', isDragActive ? 'text-white' : 'text-surface-200')} />
        </div>
        {isDragReject ? (
          <p className="text-red-400 font-medium">Only PDF files are accepted</p>
        ) : isDragActive ? (
          <p className="text-brand-300 font-semibold text-lg">Release to upload</p>
        ) : (
          <>
            <p className="text-white font-semibold text-base mb-1">Drag &amp; drop PDF files here</p>
            <p className="text-surface-200 text-sm">or <span className="text-brand-400">browse files</span> — PDF only, up to 50MB each</p>
          </>
        )}
      </div>
      {queue.length > 0 && (
        <div className="space-y-2">
          {queue.map((entry, i) => <FilePreview key={i} file={entry.file} status={entry.status} onRemove={removeFromQueue} />)}
        </div>
      )}
    </div>
  )
}

const STATUS_CONFIG = {
  ready:      { cls: 'status-ready', icon: CheckCircle, label: 'Ready' },
  processing: { cls: 'status-processing', icon: Loader2, label: 'Processing' },
  pending:    { cls: 'status-pending', icon: Loader2, label: 'Pending' },
  failed:     { cls: 'status-failed', icon: XCircle, label: 'Failed' },
}

function StatusBadge({ status }) {
  const { cls, icon: Icon, label } = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  return <span className={cls}><Icon className={clsx('w-3 h-3 mr-1', ['processing','pending'].includes(status) && 'animate-spin')} />{label}</span>
}

export default function DocumentsPage() {
  const qc = useQueryClient()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list(),
    refetchInterval: (query) => {
      const docs = query.state.data?.data || []
      return docs.some((d) => ['processing', 'pending'].includes(d.status)) ? 3000 : false
    },
  })

  const uploadMutation = useMutation({
    mutationFn: (form) => documentsApi.upload(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['documents'] }); toast.success('Document uploaded — processing…') },
    onError: (err) => toast.error(toastError(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => documentsApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['documents'] }); toast.success('Document deleted') },
    onError: (err) => toast.error(toastError(err)),
  })

  const documents = data?.data || []
  const pendingCount = documents.filter((d) => ['processing', 'pending'].includes(d.status)).length

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Documents</h1>
          <p className="text-surface-200 text-sm mt-0.5">
            {documents.length} document{documents.length !== 1 ? 's' : ''}
            {pendingCount > 0 && <span className="ml-2 text-brand-400">· {pendingCount} processing…</span>}
          </p>
        </div>
        <button onClick={() => refetch()} className="btn-ghost"><RefreshCw className="w-4 h-4" /></button>
      </div>

      <UploadZone onUpload={(form) => uploadMutation.mutateAsync(form)} disabled={uploadMutation.isPending} />

      {isLoading ? (
        <div className="flex items-center justify-center py-16"><Loader2 className="w-8 h-8 text-brand-400 animate-spin" /></div>
      ) : documents.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText className="w-12 h-12 text-surface-200 mx-auto mb-3" />
          <h3 className="font-semibold text-white mb-1">No documents yet</h3>
          <p className="text-surface-200 text-sm">Upload a PDF to get started</p>
        </div>
      ) : (
        <div className="card divide-y divide-surface-800">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center gap-4 p-4 hover:bg-surface-800/50 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0"><FileText className="w-5 h-5 text-brand-400" /></div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-white truncate">{doc.title}</p>
                <div className="flex flex-wrap items-center gap-3 mt-0.5">
                  <span className="text-xs text-surface-200">{formatBytes(doc.file_size)}</span>
                  {doc.page_count > 0 && <span className="text-xs text-surface-200">{doc.page_count} pages</span>}
                  {doc.chunk_count > 0 && <span className="text-xs text-surface-200">{doc.chunk_count} chunks</span>}
                  <span className="text-xs text-surface-200">{formatRelative(doc.created_at)}</span>
                </div>
              </div>
              <StatusBadge status={doc.status} />
              <div className="flex items-center gap-2">
                {doc.s3_url && <a href={doc.s3_url} target="_blank" rel="noopener noreferrer" className="btn-ghost py-1.5 px-2"><Eye className="w-4 h-4" /></a>}
                <button onClick={() => { if (confirm(`Delete "${doc.title}"?`)) deleteMutation.mutate(doc.id) }} className="btn-ghost py-1.5 px-2 hover:text-red-400">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
