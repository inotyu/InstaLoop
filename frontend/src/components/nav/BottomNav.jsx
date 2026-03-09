import { Link, useLocation } from 'react-router-dom'
import { Home, Search, Send, User, PlusSquare } from 'lucide-react'
import './bottomnav.css'

function NavIcon({ to, icon: Icon }) {
  const { pathname } = useLocation()
  const active = pathname === to
  return (
    <Link className={active ? 'bn-item bn-itemActive' : 'bn-item'} to={to}>
      <Icon size={22} />
    </Link>
  )
}

export default function BottomNav() {
  return (
    <div className="bn">
      <NavIcon to="/feed" icon={Home} />
      <NavIcon to="/search" icon={Search} />
      <NavIcon to="/create" icon={PlusSquare} />
      <NavIcon to="/messages" icon={Send} />
      <NavIcon to="/me" icon={User} />
    </div>
  )
}
