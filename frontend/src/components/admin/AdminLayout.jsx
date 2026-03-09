import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Link } from 'react-router-dom'
import {
  Users,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  LayoutDashboard,
  AlertTriangle,
  Shield
} from 'lucide-react'
import authService from '../../services/authService.js'
import AppShell from '../layout/AppShell.jsx'
import Button from '../ui/Button.jsx'

const adminNavItems = [
  { path: '/admin/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/admin/users', icon: Users, label: 'Usuários' },
  { path: '/admin/reports', icon: AlertTriangle, label: 'Denúncias' },
  { path: '/admin/security', icon: Shield, label: 'Segurança' },
  { path: '/admin/logs', icon: FileText, label: 'Logs' },
  { path: '/admin/settings', icon: Settings, label: 'Config' }
]

export default function AdminLayout({ children, title }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await authService.logout()
    navigate('/login')
  }

  return (
    <AppShell>
      <div style={{ display: 'flex', height: '100vh', background: 'var(--bg)' }}>
        {/* Sidebar */}
        <div style={{
          width: sidebarOpen ? '280px' : '0',
          background: 'var(--panel)',
          borderRight: '1px solid var(--border)',
          transition: 'width 0.3s ease',
          position: 'fixed',
          height: '100vh',
          zIndex: 1000,
          overflow: 'hidden'
        }}>
          <div style={{ padding: '20px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 900, color: 'var(--text)' }}>Admin Panel</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSidebarOpen(false)}
                style={{ padding: '4px' }}
              >
                <X size={20} />
              </Button>
            </div>
          </div>
          
          <nav style={{ padding: '20px 0' }}>
            {adminNavItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px 20px',
                    color: isActive ? 'var(--primary)' : 'var(--muted)',
                    background: isActive ? 'var(--primary-bg)' : 'transparent',
                    textDecoration: 'none',
                    transition: 'all 0.2s ease',
                    borderLeft: isActive ? '3px solid var(--primary)' : '3px solid transparent'
                  }}
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon size={20} />
                  <span style={{ fontSize: '14px', fontWeight: 500 }}>{item.label}</span>
                </Link>
              )
            })}
          </nav>
          
          <div style={{ position: 'absolute', bottom: '20px', left: '20px', right: '20px' }}>
            <Button
              variant="ghost"
              onClick={handleLogout}
              style={{ 
                width: '100%', 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px',
                justifyContent: 'flex-start',
                padding: '12px'
              }}
            >
              <LogOut size={20} />
              Sair
            </Button>
          </div>
        </div>

        {/* Main Content */}
        <div style={{ 
          flex: 1, 
          marginLeft: sidebarOpen ? '280px' : '0',
          transition: 'margin-left 0.3s ease',
          overflow: 'auto'
        }}>
          {/* Header */}
          <header style={{
            background: 'var(--panel)',
            borderBottom: '1px solid var(--border)',
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 100
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                style={{ padding: '6px' }}
              >
                <Menu size={20} />
              </Button>
              <h1 style={{ fontSize: '24px', fontWeight: 900, color: 'var(--text)' }}>
                {title || 'Admin Dashboard'}
              </h1>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                padding: '6px 12px',
                background: 'var(--success-bg)',
                color: 'var(--success)',
                borderRadius: '20px',
                fontSize: '12px',
                fontWeight: 600
              }}>
                Admin Online
              </div>
            </div>
          </header>

          {/* Page Content */}
          <main style={{ padding: '24px' }}>
            {children}
          </main>
        </div>
      </div>
    </AppShell>
  )
}
