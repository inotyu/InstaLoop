import PublicShell from '../components/layout/PublicShell.jsx'

export default function SecurityWarning() {
  return (
    <PublicShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, textAlign: 'center' }}>
        <div style={{ fontWeight: 900, fontSize: 18 }}>Segurança</div>
        <div style={{ color: 'var(--muted)', fontSize: 13 }}>Atividade suspeita detectada.</div>
      </div>
    </PublicShell>
  )
}
