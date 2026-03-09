import { Link, useLocation } from 'react-router-dom'
import { Home, Search, Send, User, PlusSquare, Heart } from 'lucide-react'
import './sidebar.css'

function Item({ to, icon: Icon, label }) {
  const { pathname } = useLocation()
  const active = pathname === to
  return (
    <Link className={active ? 'sb-item sb-itemActive' : 'sb-item'} to={to}>
      <Icon size={22} />
      <span className="sb-label">{label}</span>
    </Link>
  )
}

export default function Sidebar() {
  return (
    <div className="sb">
      <div className="sb-top">
        <Link to="/feed" className="sb-logo">InstaLoop</Link>
      </div>

      <div className="sb-nav">
        <Item to="/feed" icon={Home} label="Início" />
        <Item to="/search" icon={Search} label="Pesquisar" />
        <Item to="/messages" icon={Send} label="Mensagens" />
        <Item to="/follow-requests" icon={Heart} label="Solicitações" />
        <Item to="/create" icon={PlusSquare} label="Criar" />
        <Item to="/me" icon={User} label="Perfil" />
      </div>

      <div className="sb-bottom">
        <div className="sb-meta">Mini Social Network</div>
      </div>
    </div>
  )
}
