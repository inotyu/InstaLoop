import axios from 'axios'

// Configuração base do axios
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

class AuthService {
  constructor() {
    // Token armazenado APENAS em memória - nunca em localStorage/sessionStorage
    this.accessToken = null
    this.user = null
    this.csrfToken = null

    // Configurar axios base
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    // Configurar interceptor para refresh automático
    this.setupInterceptors()
  }

  // Getters e setters seguros
  setToken(token) {
    this.accessToken = token
    if (token) {
      this.api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete this.api.defaults.headers.common['Authorization']
    }
  }

  getToken() {
    return this.accessToken
  }

  setUser(userData) {
    this.user = userData
  }

  getUser() {
    return this.user
  }

  // Limpar todos os dados (logout)
  clearAuth() {
    this.setToken(null)
    this.setUser(null)
    this.csrfToken = null
  }

  // Setup de interceptors para refresh automático
  setupInterceptors() {
    // Interceptor de request
    this.api.interceptors.request.use(
      (config) => {
        // Adicionar CSRF token se disponível
        if (this.csrfToken && config.method !== 'get') {
          config.headers['X-Csrf-Token'] = this.csrfToken
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Interceptor de response
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config

        // Se for erro 401 e não for retry de refresh e não for request de refresh E não for request 2FA
        if (error.response?.status === 401 && 
            !originalRequest._retry && 
            !originalRequest.url?.includes('/auth/refresh') &&
            !originalRequest.url?.includes('/admin123/verify-2fa') &&
            !originalRequest._retryCount) {
          
          // Limitar a 3 tentativas de refresh
          originalRequest._retryCount = (originalRequest._retryCount || 0) + 1
          if (originalRequest._retryCount > 3) {
            this.clearAuth()
            window.location.href = '/login'
            return Promise.reject(error)
          }

          originalRequest._retry = true

          try {
            // Tentar refresh do token
            await this.refreshToken()
            
            // Refazer o request original com novo token
            originalRequest.headers['Authorization'] = `Bearer ${this.accessToken}`
            return this.api(originalRequest)
          } catch (refreshError) {
            // Refresh falhou, fazer logout
            this.clearAuth()
            window.location.href = '/login'
            return Promise.reject(refreshError)
          }
        }

        return Promise.reject(error)
      }
    )
  }

  // Garantir token CSRF
  async ensureCsrfToken() {
    if (!this.csrfToken) {
      try {
        const response = await this.api.get('/api/csrf')
        this.csrfToken = response.data.csrf_token
      } catch (error) {
        // Se não conseguir CSRF, continuar sem ele (endpoints que não precisam)
      }
    }
  }

  // Login
  async login(credentials) {
    try {
      await this.ensureCsrfToken()
      const response = await this.api.post('/api/auth/login', credentials)
      
      const { access_token, user } = response.data
      
      // Armazenar em memória
      this.setToken(access_token)
      this.setUser(user)
      
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async refreshToken() {
    try {
      // Refresh token usa cookie HttpOnly, não precisa enviar no body
      await this.ensureCsrfToken()
      const response = await this.api.post('/api/auth/refresh')
      
      // Atualizar token em memória
      const { access_token } = response.data
      this.setToken(access_token)
      
      return response.data
    } catch (error) {
      // Se o refresh falhar, limpar autenticação
      this.clearAuth()
      throw error
    }
  }

  async logout() {
    try {
      await this.ensureCsrfToken()
      await this.api.post('/api/auth/logout')
    } catch (error) {
      // Mesmo se falhar, limpar dados locais
    } finally {
      this.clearAuth()
    }
  }

  // Verificar se está autenticado
  isAuthenticated() {
    return !!this.accessToken && !!this.user
  }

  // Verificar se é admin
  isAdmin() {
    return this.user?.is_admin === true
  }

  // Tratamento de erros
  handleError(error) {
    if (error.response) {
      // Erro da API
      const message = error.response.data?.error || error.response.data?.message || 'Erro desconhecido'
      const details = error.response.data?.details || []
      const status = error.response.status
      
      return {
        message,
        details,
        status,
        originalError: error
      }
    } else if (error.request) {
      // Erro de rede
      return {
        message: 'Erro de conexão',
        details: ['Verifique sua conexão com a internet'],
        status: 0,
        originalError: error
      }
    } else {
      // Erro desconhecido
      return {
        message: error.message || 'Erro desconhecido',
        details: [],
        status: 0,
        originalError: error
      }
    }
  }

  // Obter usuário atual
  async getCurrentUser() {
    if (!this.isAuthenticated()) {
      throw new Error('Não autenticado')
    }

    try {
      const response = await this.api.get('/api/auth/me')
      this.setUser(response.data)
      return response.data
    } catch (error) {
      if (error.response?.status === 401) {
        this.clearAuth()
        throw new Error('Sessão expirada')
      }
      throw this.handleError(error)
    }
  }

  // Validação de token
  validateToken() {
    if (!this.accessToken) return false
    
    try {
      // Decodificar JWT (básico, sem verificação de assinatura)
      const parts = this.accessToken.split('.')
      if (parts.length !== 3) return false
      
      const payload = JSON.parse(atob(parts[1]))
      const now = Math.floor(Date.now() / 1000)
      
      return payload.exp > now
    } catch {
      return false
    }
  }

  // Auto-refresh se necessário
  async ensureValidToken() {
    if (!this.accessToken) {
      return false
    }

    if (!this.validateToken()) {
      try {
        await this.refreshToken()
        return true
      } catch (error) {
        this.clearAuth()
        return false
      }
    }

    return true
  }
}

// Instância singleton
const authService = new AuthService()

export default authService
