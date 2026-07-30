import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Brain, Loader2 } from 'lucide-react'
import useAuthStore from '../store/authStore'
import toast from 'react-hot-toast'
import { toastError } from '../utils/formatters'

export default function RegisterPage() {
  const [form, setForm] = useState({ email: '', full_name: '', password: '', confirm: '' })
  const [loading, setLoading] = useState(false)
  const { register } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirm) { toast.error('Passwords do not match'); return }
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await register(form.email, form.full_name, form.password)
      toast.success('Account created! Welcome to DocuMind.')
      navigate('/dashboard')
    } catch (err) {
      toast.error(toastError(err))
    } finally { setLoading(false) }
  }

  const f = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl" />
      </div>
      <div className="w-full max-w-md relative">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-brand-600 mb-4">
            <Brain className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create account</h1>
          <p className="text-surface-200 text-sm mt-1">Get started with DocuMind</p>
        </div>
        <div className="card p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-100 mb-1.5">Full Name</label>
              <input type="text" className="input-field" placeholder="Jane Doe" value={form.full_name} onChange={f('full_name')} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-100 mb-1.5">Email</label>
              <input type="email" className="input-field" placeholder="you@example.com" value={form.email} onChange={f('email')} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-100 mb-1.5">Password</label>
              <input type="password" className="input-field" placeholder="Min 8 characters" value={form.password} onChange={f('password')} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-100 mb-1.5">Confirm Password</label>
              <input type="password" className="input-field" placeholder="Repeat password" value={form.confirm} onChange={f('confirm')} required />
            </div>
            <button type="submit" className="btn-primary w-full justify-center py-2.5" disabled={loading}>
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>
          <p className="text-center text-sm text-surface-200 mt-4">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
