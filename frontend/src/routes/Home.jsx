import { Link } from 'react-router-dom'
import PublicShell from '../components/layout/PublicShell.jsx'
import Button from '../components/ui/Button.jsx'

export default function Home() {
  return (
    <PublicShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, alignItems: 'center', textAlign: 'center' }}>
        <div style={{ fontSize: 26, fontWeight: 900 }}>InstaLoop</div>
        <div style={{ color: 'var(--muted)', fontSize: 13 }}>Mini rede social inspirada no Instagram.</div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
          <Button as={Link} to="/login">Entrar</Button>
          <Button as={Link} to="/register" variant="ghost">Criar conta</Button>
        </div>
      </div>
    </PublicShell>
  )
}
