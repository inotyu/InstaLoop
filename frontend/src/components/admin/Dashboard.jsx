import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, MessageSquare, FileText, AlertTriangle, TrendingUp, Activity } from 'lucide-react'
import Button from '../ui/Button.jsx'

export default function Dashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        // Import dinâmico para evitar problemas
        const { default: authService } = await import('../../services/authService.js')
        
        const response = await authService.secureRequest(
          'get',
          '/admin123/dashboard'
        )
        setData(response)
      } catch (error) {
        setData({
          overview: {
            total_users: 0,
            total_posts: 0,
            total_messages: 0,
            pending_reports: 0,
            new_users_week: 0,
            new_posts_day: 0
          },
          security: {
            total_security_events: 0,
            critical_events: []
          },
          system_health: {
            database_status: "healthy",
            redis_status: "healthy",
            storage_status: "healthy"
          }
        })
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <div>Carregando dashboard...</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <div>Erro ao carregar dashboard</div>
      </div>
    )
  }

  // Estrutura da API real vs dados mock
  const overview = data.overview || {
    total_users: 3,
    total_posts: 0,
    total_messages: 0,
    pending_reports: 0,
    new_users_week: 1,
    new_posts_day: 0
  }
  
  const security = data.security || {
    total_security_events: 0,
    critical_events: []
  }
  
  const system_health = data.system_health || {
    database_status: "healthy",
    redis_status: "healthy", 
    storage_status: "healthy"
  }

  const statCards = [
    {
      title: 'Total de Usuários',
      value: overview.total_users,
      change: overview.new_users_week,
      changeLabel: 'esta semana',
      icon: Users,
      color: 'var(--primary)'
    },
    {
      title: 'Total de Posts',
      value: overview.total_posts,
      change: overview.new_posts_day,
      changeLabel: 'hoje',
      icon: FileText,
      color: 'var(--success)'
    },
    {
      title: 'Mensagens',
      value: overview.total_messages,
      change: null,
      changeLabel: '',
      icon: MessageSquare,
      color: 'var(--warning)'
    },
    {
      title: 'Denúncias',
      value: overview.pending_reports,
      change: null,
      changeLabel: 'pendentes',
      icon: AlertTriangle,
      color: 'var(--danger)'
    }
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Stats Grid */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
        gap: '20px' 
      }}>
        {statCards.map((stat, index) => {
          const Icon = stat.icon
          return (
            <div
              key={index}
              style={{
                background: 'var(--panel)',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                padding: '24px',
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>
                    {stat.title}
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 900, color: 'var(--text)' }}>
                    {stat.value.toLocaleString()}
                  </div>
                  {stat.change !== null && (
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '4px',
                      marginTop: '8px',
                      fontSize: '12px'
                    }}>
                      <TrendingUp size={14} style={{ color: 'var(--success)' }} />
                      <span style={{ color: 'var(--success)' }}>
                        +{stat.change} {stat.changeLabel}
                      </span>
                    </div>
                  )}
                </div>
                <div style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '12px',
                  background: `${stat.color}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Icon size={24} style={{ color: stat.color }} />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* System Health & Security */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr', 
        gap: '20px' 
      }}>
        {/* System Health */}
        <div style={{
          background: 'var(--panel)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '24px'
        }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '20px', color: 'var(--text)' }}>
            Saúde do Sistema
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {Object.entries(system_health).map(([key, status]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: status === 'healthy' ? 'var(--success)' : 'var(--danger)'
                }} />
                <span style={{ fontSize: '14px', color: 'var(--text)' }}>
                  {key.replace('_', ' ').charAt(0).toUpperCase() + key.replace('_', ' ').slice(1)}
                </span>
                <span style={{ 
                  fontSize: '12px', 
                  color: status === 'healthy' ? 'var(--success)' : 'var(--danger)',
                  marginLeft: 'auto'
                }}>
                  {status === 'healthy' ? 'OK' : 'ERROR'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Security Summary */}
        <div style={{
          background: 'var(--panel)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '24px'
        }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '20px', color: 'var(--text)' }}>
            Resumo de Segurança (24h)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {security?.summary && Object.entries(security.summary).map(([key, value]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Activity size={16} style={{ color: 'var(--warning)' }} />
                <span style={{ fontSize: '14px', color: 'var(--text)' }}>
                  {key.replace('_', ' ').charAt(0).toUpperCase() + key.replace('_', ' ').slice(1)}
                </span>
                <span style={{ 
                  fontSize: '12px', 
                  color: 'var(--muted)',
                  marginLeft: 'auto'
                }}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{
        background: 'var(--panel)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '24px'
      }}>
        <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '20px', color: 'var(--text)' }}>
          Ações Rápidas
        </h3>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <Button variant="primary" onClick={() => {
            navigate('/admin123/users')
          }}>
            Gerenciar Usuários
          </Button>
          <Button variant="ghost" onClick={() => {
            navigate('/admin123/reports')
          }}>
            Revisar Denúncias
          </Button>
          <Button variant="ghost" onClick={() => {
            navigate('/admin123/security')
          }}>
            Ver Logs de Segurança
          </Button>
        </div>
      </div>
    </div>
  )
}
