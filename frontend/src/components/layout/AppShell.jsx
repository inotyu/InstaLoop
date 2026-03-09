import './appshell.css'
import Sidebar from '../nav/Sidebar.jsx'
import BottomNav from '../nav/BottomNav.jsx'

export default function AppShell({ children, right }) {
  return (
    <div className="shell">
      <aside className="shell-sidebar">
        <Sidebar />
      </aside>

      <main className="shell-main">
        <div className="shell-mainInner">{children}</div>
      </main>

      <aside className="shell-right">{right}</aside>

      <nav className="shell-bottom">
        <BottomNav />
      </nav>
    </div>
  )
}
