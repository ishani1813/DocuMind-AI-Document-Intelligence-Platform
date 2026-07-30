import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, Plus, Trash2, UserPlus, Loader2, ChevronRight, FolderOpen, FileText, Crown, X } from 'lucide-react'
import { workspacesApi } from '../services/api'
import useAuthStore from '../store/authStore'
import toast from 'react-hot-toast'
import { formatRelative, toastError } from '../utils/formatters'

function CreateWorkspaceModal({ onClose }) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const create = useMutation({
    mutationFn: () => workspacesApi.create({ name: name.trim(), description: desc.trim() || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['workspaces'] }); toast.success('Workspace created'); onClose() },
    onError: (err) => toast.error(toastError(err)),
  })
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
      <div className="card w-full max-w-md p-6 animate-slide-up">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-white">New Workspace</h2>
          <button onClick={onClose} className="text-surface-200 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-4">
          <div><label className="block text-sm font-medium text-surface-100 mb-1.5">Name *</label><input type="text" className="input-field" value={name} onChange={(e) => setName(e.target.value)} autoFocus /></div>
          <div><label className="block text-sm font-medium text-surface-100 mb-1.5">Description</label><textarea className="input-field resize-none" rows={3} value={desc} onChange={(e) => setDesc(e.target.value)} /></div>
          <div className="flex gap-3 pt-2">
            <button onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button onClick={() => create.mutate()} className="btn-primary flex-1 justify-center" disabled={!name.trim() || create.isPending}>
              {create.isPending && <Loader2 className="w-4 h-4 animate-spin" />}Create
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function InviteModal({ workspace, onClose }) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('member')
  const invite = useMutation({
    mutationFn: () => workspacesApi.invite(workspace.id, { email: email.trim(), role }),
    onSuccess: (res) => { toast.success(res.data.message || 'Member invited'); onClose() },
    onError: (err) => toast.error(toastError(err)),
  })
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
      <div className="card w-full max-w-md p-6 animate-slide-up">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-white">Invite to {workspace.name}</h2>
          <button onClick={onClose} className="text-surface-200 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-4">
          <div><label className="block text-sm font-medium text-surface-100 mb-1.5">Email</label><input type="email" className="input-field" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus /></div>
          <div>
            <label className="block text-sm font-medium text-surface-100 mb-1.5">Role</label>
            <select className="input-field" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="viewer">Viewer</option><option value="member">Member</option><option value="admin">Admin</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button onClick={() => invite.mutate()} className="btn-primary flex-1 justify-center" disabled={!email.trim() || invite.isPending}>
              {invite.isPending && <Loader2 className="w-4 h-4 animate-spin" />}<UserPlus className="w-4 h-4" />Invite
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function WorkspacesPage() {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const [showCreate, setShowCreate] = useState(false)
  const [inviteWs, setInviteWs] = useState(null)

  const { data, isLoading } = useQuery({ queryKey: ['workspaces'], queryFn: () => workspacesApi.list() })
  const deleteWs = useMutation({
    mutationFn: (id) => workspacesApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['workspaces'] }); toast.success('Workspace deleted') },
    onError: (err) => toast.error(toastError(err)),
  })

  const workspaces = data?.data || []

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-white">Workspaces</h1><p className="text-surface-200 text-sm mt-0.5">Organize documents and collaborate with your team</p></div>
        <button onClick={() => setShowCreate(true)} className="btn-primary"><Plus className="w-4 h-4" />New Workspace</button>
      </div>

      <div className="card p-4 border-brand-500/20 bg-brand-600/5 flex items-start gap-3">
        <Users className="w-5 h-5 text-brand-400 flex-shrink-0 mt-0.5" />
        <div><p className="text-sm font-medium text-white">Multi-user collaboration</p><p className="text-xs text-surface-200 mt-0.5">Create workspaces to share documents with teammates with role-based access.</p></div>
      </div>

      {isLoading && <div className="flex items-center justify-center py-16"><Loader2 className="w-8 h-8 text-brand-400 animate-spin" /></div>}

      {!isLoading && workspaces.length === 0 && (
        <div className="card p-16 text-center">
          <FolderOpen className="w-12 h-12 text-surface-200 mx-auto mb-3" />
          <h3 className="font-semibold text-white mb-1">No workspaces yet</h3>
          <p className="text-sm text-surface-200 mb-4">Create a workspace to collaborate with your team</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary mx-auto"><Plus className="w-4 h-4" />Create your first workspace</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {workspaces.map((ws) => {
          const isOwner = ws.owner_id === user?.id
          return (
            <div key={ws.id} className="card p-5 hover:border-surface-700 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-brand-600/20 flex items-center justify-center flex-shrink-0"><FolderOpen className="w-4 h-4 text-brand-400" /></div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-white truncate">{ws.name}</h3>
                    {isOwner && <span className="inline-flex items-center gap-1 text-[10px] text-amber-300"><Crown className="w-2.5 h-2.5" /> Owner</span>}
                  </div>
                </div>
                {isOwner && <button onClick={() => { if (confirm(`Delete "${ws.name}"?`)) deleteWs.mutate(ws.id) }} className="text-surface-200 hover:text-red-400 p-1 flex-shrink-0"><Trash2 className="w-4 h-4" /></button>}
              </div>
              {ws.description && <p className="text-xs text-surface-200 mb-3 line-clamp-2">{ws.description}</p>}
              <div className="flex items-center gap-4 mb-4">
                <div className="flex items-center gap-1.5 text-xs text-surface-200"><Users className="w-3.5 h-3.5" /><span>{ws.member_count} member{ws.member_count !== 1 ? 's' : ''}</span></div>
                <div className="flex items-center gap-1.5 text-xs text-surface-200"><FileText className="w-3.5 h-3.5" /><span>{ws.document_count} doc{ws.document_count !== 1 ? 's' : ''}</span></div>
                <div className="ml-auto text-[10px] text-surface-200">{formatRelative(ws.created_at)}</div>
              </div>
              <div className="flex items-center gap-2 pt-3 border-t border-surface-800">
                {isOwner && <button onClick={() => setInviteWs(ws)} className="btn-secondary text-xs py-1.5 flex-1 justify-center"><UserPlus className="w-3.5 h-3.5" />Invite</button>}
                <button className="btn-ghost text-xs py-1.5 flex-1 justify-center"><ChevronRight className="w-3.5 h-3.5" />View</button>
              </div>
            </div>
          )
        })}
      </div>

      {showCreate && <CreateWorkspaceModal onClose={() => setShowCreate(false)} />}
      {inviteWs && <InviteModal workspace={inviteWs} onClose={() => setInviteWs(null)} />}
    </div>
  )
}
