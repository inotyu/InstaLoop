import { useState, useEffect } from 'react'
import { Search, Filter, Download, Eye, Calendar, User, AlertTriangle } from 'lucide-react'
import Button from '../ui/Button.jsx'

export default function LogsViewer() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [eventFilter, setEventFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')
  const [hoursFilter, setHoursFilter] = useState('24')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [selectedLog, setSelectedLog] = useState(null)

  useEffect(() => {
    loadLogs()
  }, [search, eventFilter, userFilter, hoursFilter, page])

  const loadLogs = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page,
        search,
        event: eventFilter,
        user_id: userFilter,
        hours: hoursFilter
      })
      
      const response = await fetch(`/admin/logs?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      })
      const data = await response.json()
      setLogs(data.logs || [])
      setTotalPages(data.pagination?.pages || 1)
    } catch (error) {
    } finally {
      setLoading(false)
    }
  }

  const exportLogs = async () => {
    try {
      const params = new URLSearchParams({
        search,
        event: eventFilter,
        user_id: userFilter,
        hours: hoursFilter,
        export: 'true'
      })
      
      const response = await fetch(`/admin/logs?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      })
      
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `instaloop-logs-${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }
    } catch (error) {
    }
  }

  const getEventIcon = (eventType) => {
    if (eventType.includes('login') || eventType.includes('auth')) {
      return <User size={16} style={{ color: 'var(--primary)' }} />
    }
    if (eventType.includes('security') || eventType.includes('suspicious')) {
      return <AlertTriangle size={16} style={{ color: 'var(--warning)' }} />
    }
    return <Calendar size={16} style={{ color: 'var(--muted)' }} />
  }

  const getEventColor = (eventType) => {
    if (eventType.includes('failed') || eventType.includes('blocked')) {
      return 'var(--danger)'
    }
    if (eventType.includes('security') || eventType.includes('suspicious')) {
      return 'var(--warning)'
    }
    if (eventType.includes('success') || eventType.includes('created')) {
      return 'var(--success)'
    }
    return 'var(--muted)'
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <div>Carregando logs...</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Filters */}
      <div style={{
        background: 'var(--panel)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '20px'
      }}>
        <div style={{ 
          display: 'flex', 
          gap: '16px', 
          flexWrap: 'wrap',
          alignItems: 'center'
        }}>
          <div style={{ 
            flex: 1, 
            minWidth: '200px',
            position: 'relative'
          }}>
            <Search 
              size={20} 
              style={{ 
                position: 'absolute', 
                left: '12px', 
                top: '50%', 
                transform: 'translateY(-50%)',
                color: 'var(--muted)'
              }} 
            />
            <input
              type="text"
              placeholder="Buscar logs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px 10px 40px',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                background: 'var(--bg)',
                color: 'var(--text)',
                fontSize: '14px'
              }}
            />
          </div>
          
          <select
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value)}
            style={{
              padding: '10px 12px',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              background: 'var(--bg)',
              color: 'var(--text)',
              fontSize: '14px'
            }}
          >
            <option value="">Todos eventos</option>
            <option value="login_success">Login Sucesso</option>
            <option value="login_failed">Login Falha</option>
            <option value="suspicious_activity">Atividade Suspeita</option>
            <option value="bot_detected">Bot Detectado</option>
            <option value="jwt_invalid">JWT Inválido</option>
          </select>
          
          <input
            type="text"
            placeholder="ID do usuário"
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            style={{
              padding: '10px 12px',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              background: 'var(--bg)',
              color: 'var(--text)',
              fontSize: '14px',
              width: '150px'
            }}
          />
          
          <select
            value={hoursFilter}
            onChange={(e) => setHoursFilter(e.target.value)}
            style={{
              padding: '10px 12px',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              background: 'var(--bg)',
              color: 'var(--text)',
              fontSize: '14px'
            }}
          >
            <option value="1">Última hora</option>
            <option value="24">Últimas 24h</option>
            <option value="168">Últimos 7 dias</option>
            <option value="720">Últimos 30 dias</option>
          </select>
          
          <Button
            variant="ghost"
            onClick={exportLogs}
            title="Exportar logs"
          >
            <Download size={16} />
          </Button>
        </div>
      </div>

      {/* Logs Table */}
      <div style={{
        background: 'var(--panel)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        overflow: 'hidden'
      }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Evento</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Usuário</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>IP</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Detalhes</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Data</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {getEventIcon(log.event_type)}
                      <span style={{ 
                        fontSize: '14px', 
                        color: getEventColor(log.event_type),
                        fontWeight: 500
                      }}>
                        {log.event_type.replace('_', ' ').charAt(0).toUpperCase() + 
                         log.event_type.replace('_', ' ').slice(1)}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '16px', fontSize: '14px', color: 'var(--text)' }}>
                    {log.user_id ? log.user_id.substring(0, 8) + '...' : '-'}
                  </td>
                  <td style={{ padding: '16px', fontSize: '14px', color: 'var(--muted)' }}>
                    {log.ip}
                  </td>
                  <td style={{ padding: '16px' }}>
                    <div style={{ fontSize: '14px', color: 'var(--text)' }}>
                      {log.details ? 
                        (typeof log.details === 'string' ? 
                          log.details : 
                          JSON.stringify(log.details).substring(0, 50) + '...'
                        ) : '-'
                      }
                    </div>
                  </td>
                  <td style={{ padding: '16px', fontSize: '14px', color: 'var(--muted)' }}>
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td style={{ padding: '16px' }}>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedLog(log)}
                      title="Ver detalhes"
                    >
                      <Eye size={16} />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {logs.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--muted)' }}>
            Nenhum log encontrado com os filtros atuais
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
          >
            Anterior
          </Button>
          
          <span style={{ 
            padding: '8px 16px', 
            fontSize: '14px', 
            color: 'var(--muted)' 
          }}>
            Página {page} de {totalPages}
          </span>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
          >
            Próxima
          </Button>
        </div>
      )}

      {/* Log Detail Modal */}
      {selectedLog && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--panel)',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '700px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text)' }}>
                Detalhes do Log
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedLog(null)}
              >
                ×
              </Button>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div><strong>ID:</strong> {selectedLog.id}</div>
              <div><strong>Evento:</strong> {selectedLog.event_type}</div>
              <div><strong>Usuário:</strong> {selectedLog.user_id || 'N/A'}</div>
              <div><strong>IP:</strong> {selectedLog.ip}</div>
              <div><strong>Fingerprint:</strong> {selectedLog.fingerprint || 'N/A'}</div>
              <div><strong>Data:</strong> {new Date(selectedLog.timestamp).toLocaleString()}</div>
              <div>
                <strong>Detalhes:</strong>
                <pre style={{ 
                  marginTop: '8px', 
                  padding: '12px', 
                  background: 'var(--panel-2)', 
                  borderRadius: '8px',
                  fontSize: '12px',
                  overflow: 'auto',
                  maxHeight: '200px'
                }}>
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
