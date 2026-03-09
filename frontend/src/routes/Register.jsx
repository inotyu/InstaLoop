import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import authService from '../services/authService.js'
import PublicShell from '../components/layout/PublicShell.jsx'
import TextField from '../components/ui/TextField.jsx'
import Button from '../components/ui/Button.jsx'
import Divider from '../components/ui/Divider.jsx'

export default function Register() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
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
      await authService.register({ username, email, password })
      navigate('/login')
    } catch (err) {
      setError(err.message || 'Falha no cadastro')
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
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>Cadastre-se para ver fotos e vídeos dos seus amigos.</div>
        </div>

        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <TextField label="Username" name="username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
          <TextField label="Email" name="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          <TextField label="Senha" name="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
          <Button disabled={loading} type="submit">{loading ? '...' : 'Criar conta'}</Button>
          
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

        <Button as="a" href="/login" variant="ghost">Já tem uma conta? Entrar</Button>
      </div>
    </PublicShell>
  )
}
