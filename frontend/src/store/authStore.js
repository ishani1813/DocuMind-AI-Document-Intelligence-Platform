import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../services/api'

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null, accessToken: null, refreshToken: null, isAuthenticated: false,

      login: async (email, password) => {
        const { data } = await api.post('/auth/login', { email, password })
        api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
        const me = await api.get('/auth/me')
        set({ accessToken: data.access_token, refreshToken: data.refresh_token, user: me.data, isAuthenticated: true })
        return me.data
      },

      register: async (email, full_name, password) => {
        await api.post('/auth/register', { email, full_name, password })
        return get().login(email, password)
      },

      logout: () => {
        delete api.defaults.headers.common['Authorization']
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
      },

      hydrate: () => {
        const { accessToken } = get()
        if (accessToken) api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
      },
    }),
    {
      name: 'documind-auth',
      partialize: (s) => ({ accessToken: s.accessToken, refreshToken: s.refreshToken, user: s.user, isAuthenticated: s.isAuthenticated }),
    }
  )
)

export default useAuthStore
