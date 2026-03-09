import AppShell from '../components/layout/AppShell.jsx'
import SuggestionsPanel from '../components/suggestions/SuggestionsPanel.jsx'
import TextField from '../components/ui/TextField.jsx'
import Button from '../components/ui/Button.jsx'

export default function Create() {
  return (
    <AppShell right={<SuggestionsPanel />}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ fontWeight: 900, fontSize: 18 }}>Criar</div>
        <TextField label="Conteúdo" placeholder="Escreva algo..." />
        <Button disabled>Criar post</Button>
        <div style={{ color: 'var(--muted)', fontSize: 13 }}>UI pronta. Lógica será conectada no backend.</div>
      </div>
    </AppShell>
  )
}
