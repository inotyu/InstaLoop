import Avatar from '../ui/Avatar.jsx'
import Button from '../ui/Button.jsx'
import './suggestions.css'

function Row({ name }) {
  return (
    <div className="sug-row">
      <div className="sug-left">
        <Avatar size={42} ring />
        <div className="sug-text">
          <div className="sug-name">@{name}</div>
          <div className="sug-sub">Sugestão para você</div>
        </div>
      </div>
      <Button variant="ghost" size="sm">Seguir</Button>
    </div>
  )
}

export default function SuggestionsPanel() {
  const items = ['vampir', 'peach_21s', 'ahan', 'giovanna', 'k.mysttx']
  return (
    <div className="sug">
      <div className="sug-title">Sugestões para você</div>
      <div className="sug-list">
        {items.map((n) => (
          <Row key={n} name={n} />
        ))}
      </div>
      <div className="sug-footer">Sobre • Ajuda • Privacidade • Termos</div>
    </div>
  )
}
