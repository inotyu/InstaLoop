import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import authService from '../services/authService.js'
import PublicShell from '../components/layout/PublicShell.jsx'
import TextField from '../components/ui/TextField.jsx'
import Button from '../components/ui/Button.jsx'
import Divider from '../components/ui/Divider.jsx'

export default function Login() {
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [details, setDetails] = useState([])

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setDetails([])
    setLoading(true)
    try {
      const payload = { identifier, password }
      const response = await authService.login(payload)
      navigate('/feed')
    } catch (err) {
      setError(err.message || 'Falha no login')
      setDetails(err.details || [])
    } finally {
      setLoading(false)
    }
  }

  return (
    <PublicShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
          <div style={{ fontSize: 26, fontWeight: 900, letterSpacing: 0.2 }}>InstaLoop</div>
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>Entre para ver fotos e vídeos dos seus amigos.</div>
        </div>

        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <TextField label="Email ou username" name="identifier" value={identifier} onChange={(e) => setIdentifier(e.target.value)} autoComplete="username" />
          <TextField label="Senha" name="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />

          <Button disabled={loading} type="submit">{loading ? '...' : 'Entrar'}</Button>
          
          {error ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ color: 'var(--danger)', fontSize: 13, fontWeight: 600 }}>{error}</div>
              {details.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--danger)', fontSize: 12 }}>
                  {details.map((d, i) => <li key={i}>{d}</li>)}
                </ul>
              )}
            </div>
          ) : null}
        </form>

        <Divider />

        <Button as="a" href="/register" variant="ghost">Criar nova conta</Button>
        
        <div style={{ textAlign: 'center' }}>
          <Button 
            as="a" 
            href="/reset-password" 
            variant="ghost" 
            style={{ fontSize: 13, color: 'var(--muted)' }}
          >
            Esqueceu a senha?
          </Button>
        </div>
      </div>
    </PublicShell>
  )
}
