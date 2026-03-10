import { useState } from 'react'
import { Shield, Lock } from 'lucide-react'
import authService from '../../services/authService.js'
import './Admin2FAVerify.css'

export default function Admin2FAVerify({ onVerified }) {
  const [totp, setTotp] = useState(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleInputChange(index, value) {
    if (value.length > 1) return // Só permite um caractere
    
    const newTotp = [...totp]
    newTotp[index] = value
    setTotp(newTotp)
    
    // Auto-focus próximo campo
    if (value && index < 5) {
      const nextInput = document.getElementById(`totp-${index + 1}`)
      if (nextInput) nextInput.focus()
    }
  }

  function handleKeyDown(index, e) {
    // Backspace para voltar ao campo anterior
    if (e.key === 'Backspace' && !totp[index] && index > 0) {
      const prevInput = document.getElementById(`totp-${index - 1}`)
      if (prevInput) {
        prevInput.focus()
        const newTotp = [...totp]
        newTotp[index - 1] = ''
        setTotp(newTotp)
      }
    }
  }

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      const totpCode = totp.join('')
      
      if (totpCode.length !== 6) {
        setError('Digite o código completo de 6 dígitos')
        setLoading(false)
        return
      }
      
      
      const response = await authService.api.post(`/${import.meta.env.VITE_ADMIN_ROUTE}/verify-2fa`, {
        totp_code: totpCode
      })
      
      
      // Atualizar token com 2FA verificado
      localStorage.setItem('access_token', response.data.access_token)
      
      onVerified()
    } catch (err) {
      
      if (err.response?.status === 401) {
        setError('Código TOTP inválido')
      } else {
        setError('Erro ao verificar código. Tente novamente.')
      }
      
      // Limpar campos em caso de erro
      setTotp(['', '', '', '', '', ''])
      
      // Focar primeiro campo
      const firstInput = document.getElementById('totp-0')
      if (firstInput) firstInput.focus()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="admin-2fa-container">
      <div className="admin-2fa-card">
        <div className="admin-2fa-header">
          <div className="admin-2fa-icon">
            <Shield size={48} color="#0095f6" />
          </div>
          <h1>Verificação em Duas Etapas</h1>
          <p>Para acessar o painel administrativo, digite o código do seu aplicativo autenticador.</p>
        </div>

        {error && (
          <div className="admin-2fa-error">
            <Lock size={20} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={onSubmit} className="admin-2fa-form">
          <div className="admin-2fa-inputs">
            {totp.map((digit, index) => (
              <input
                key={index}
                id={`totp-${index}`}
                type="text"
                inputMode="numeric"
                pattern="[0-9]"
                maxLength={1}
                value={digit}
                onChange={(e) => handleInputChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                className="admin-2fa-input"
                disabled={loading}
                autoComplete="off"
              />
            ))}
          </div>

          <button 
            type="submit" 
            className="admin-2fa-button"
            disabled={loading || totp.join('').length !== 6}
          >
            {loading ? 'Verificando...' : 'Verificar Acesso'}
          </button>
        </form>

        <div className="admin-2fa-help">
          <h3>🔐 Como funciona:</h3>
          <ul>
            <li>Abra seu aplicativo autenticador (Google Authenticator, Authy, etc.)</li>
            <li>Procure por "InstaLoop" na lista</li>
            <li>Digite o código de 6 dígitos mostrado</li>
            <li>Códigos expiram a cada 30 segundos</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
