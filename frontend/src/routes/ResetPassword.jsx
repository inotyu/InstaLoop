import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Lock, Mail, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react'
import authService from '../services/authService'
import './ResetPassword.css'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')
  
  const [step, setStep] = useState(token ? 'confirm' : 'request')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  
  // Form states
  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  
  // Password validation
  const [passwordStrength, setPasswordStrength] = useState({
    score: 0,
    message: '',
    color: ''
  })

  useEffect(() => {
    if (token) {
      setStep('confirm')
    }
  }, [token])

  const validatePassword = (password) => {
    let score = 0
    let message = ''
    let color = ''
    
    // Length check
    if (password.length >= 8) score += 1
    if (password.length >= 12) score += 1
    
    // Character variety
    if (/[a-z]/.test(password)) score += 1
    if (/[A-Z]/.test(password)) score += 1
    if (/[0-9]/.test(password)) score += 1
    if (/[^a-zA-Z0-9]/.test(password)) score += 1
    
    if (score <= 2) {
      message = 'Senha fraca'
      color = '#ef4444'
    } else if (score <= 4) {
      message = 'Senha média'
      color = '#f59e0b'
    } else {
      message = 'Senha forte'
      color = '#10b981'
    }
    
    setPasswordStrength({ score, message, color })
  }

  const handlePasswordChange = (value) => {
    setNewPassword(value)
    validatePassword(value)
  }

  const handleRequestReset = async (e) => {
    e.preventDefault()
    if (!email.trim()) {
      setError('Digite seu email')
      return
    }
    
    setLoading(true)
    setError('')
    setSuccess('')
    
    try {
      await authService.resetPasswordRequest(email.trim())
      setSuccess('Se o email existir, você receberá as instruções.')
      setEmail('')
    } catch (err) {
      setError(err?.response?.data?.error || 'Erro ao solicitar redefinição')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmReset = async (e) => {
    e.preventDefault()
    
    if (!token) {
      setError('Token inválido')
      return
    }
    
    if (!newPassword) {
      setError('Digite a nova senha')
      return
    }
    
    if (newPassword !== confirmPassword) {
      setError('As senhas não coincidem')
      return
    }
    
    if (passwordStrength.score <= 2) {
      setError('Use uma senha mais forte')
      return
    }
    
    setLoading(true)
    setError('')
    setSuccess('')
    
    try {
      await authService.resetPasswordConfirm(token, newPassword)
      setSuccess('Senha redefinida com sucesso!')
      setTimeout(() => {
        navigate('/login')
      }, 3000)
    } catch (err) {
      setError(err?.response?.data?.error || 'Erro ao redefinir senha')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="reset-password-container">
      <div className="reset-password-card">
        <div className="reset-password-logo">
          <div className="logo-text"></div>
        </div>

        <div className="reset-password-header">
          <h1>{step === 'request' ? 'Recuperação de Senha' : 'Redefinir Senha'}</h1>
          <p>
            {step === 'request' 
              ? 'Digite seu email para receber as instruções de redefinição'
              : 'Digite sua nova senha abaixo'
            }
          </p>
        </div>

        {error && (
          <div className="reset-password-alert error">
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="reset-password-alert success">
            <CheckCircle size={20} />
            <span>{success}</span>
          </div>
        )}

        {step === 'request' ? (
          <form onSubmit={handleRequestReset} className="reset-password-form">
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Digite seu email"
                required
              />
            </div>

            <button 
              type="submit" 
              className="reset-password-button"
              disabled={loading}
            >
              {loading ? 'Enviando...' : 'Enviar instruções'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleConfirmReset} className="reset-password-form">
            <div className="form-group">
              <label htmlFor="new-password">Nova senha</label>
              <div className="password-input-wrapper">
                <input
                  id="new-password"
                  type={showPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => handlePasswordChange(e.target.value)}
                  placeholder="Digite sua nova senha"
                  required
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
              {newPassword && (
                <div className="password-strength">
                  <div 
                    className="password-strength-bar"
                    style={{ 
                      width: `${(passwordStrength.score / 6) * 100}%`,
                      backgroundColor: passwordStrength.color
                    }}
                  />
                  <span style={{ color: passwordStrength.color }}>
                    {passwordStrength.message}
                  </span>
                </div>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="confirm-password">Confirmar nova senha</label>
              <div className="password-input-wrapper">
                <input
                  id="confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirme sua nova senha"
                  required
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
            </div>

            <button 
              type="submit" 
              className="reset-password-button"
              disabled={loading}
            >
              {loading ? 'Redefinindo...' : 'Redefinir senha'}
            </button>
          </form>
        )}

        <div className="reset-password-footer">
          <p>
            Lembra sua senha?{' '}
            <button 
              type="button" 
              className="reset-password-link"
              onClick={() => navigate('/login')}
            >
              Fazer Login
            </button>
          </p>
        </div>

        <div className="reset-password-security">
          <h3>⚠️ Segurança</h3>
          <ul>
            <li>Os links expiram em 15 minutos</li>
            <li>Só podem ser usados uma vez</li>
            <li>Nunca compartilhe o link com ninguém</li>
            <li>Use uma senha forte e única</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
