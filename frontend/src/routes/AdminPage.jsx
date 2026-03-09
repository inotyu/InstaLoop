import { useState, useEffect } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import authService from '../services/authService.js'
import AdminLayout from '../components/admin/AdminLayout.jsx'
import Admin2FAVerify from '../components/admin/Admin2FAVerify.jsx'
import Dashboard from '../components/admin/Dashboard.jsx'
import UserManagement from '../components/admin/UserManagement.jsx'
import ReportManagement from '../components/admin/ReportManagement.jsx'
import SecurityPanel from '../components/admin/SecurityPanel.jsx'
import LogsViewer from '../components/admin/LogsViewer.jsx'

export default function AdminPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [need2FA, setNeed2FA] = useState(true) // Começa exigindo 2FA

  useEffect(() => {
    // Verificar se é admin
    const user = authService.getUser()
    
    if (!user?.is_admin) {
      navigate('/feed')
      return
    }

    // Verificar se 2FA já foi verificado nesta sessão
    const token = localStorage.getItem('access_token')
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        if (payload.totp_verified) {
          setNeed2FA(false)
        }
      } catch (e) {
      }
    }
    
    setLoading(false)
  }, [navigate])

  const handle2FAVerified = () => {
    setNeed2FA(false)
  }

  if (loading) {
    return <div style={{ padding: 20 }}>Carregando...</div>
  }

  // Exigir 2FA antes de mostrar o painel
  if (need2FA) {
    return <Admin2FAVerify onVerified={handle2FAVerified} />
  }

  return (
    <Routes>
      <Route path="" element={
        <>
          <AdminLayout>
            <Dashboard />
          </AdminLayout>
        </>
      } />
      <Route path="dashboard" element={
        <>
          <AdminLayout title="Dashboard">
            <Dashboard />
          </AdminLayout>
        </>
      } />
      <Route path="users" element={
        <AdminLayout>
          <UserManagement />
        </AdminLayout>
      } />
      <Route path="reports" element={
        <AdminLayout>
          <ReportManagement />
        </AdminLayout>
      } />
      <Route path="security" element={
        <>
          <AdminLayout title="Segurança">
            <SecurityPanel />
          </AdminLayout>
        </>
      } />
      <Route path="logs" element={
        <>
          <AdminLayout title="Logs do Sistema">
            <LogsViewer />
          </AdminLayout>
        </>
      } />
    </Routes>
  )
}
