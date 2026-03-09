import { useState, useEffect } from 'react'
import { AlertTriangle, Eye, Check, X, MessageSquare, FileText, User } from 'lucide-react'
import Button from '../ui/Button.jsx'
import Avatar from '../ui/Avatar.jsx'

export default function ReportManagement() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('pending')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [selectedReport, setSelectedReport] = useState(null)

  // Garantir que reports seja sempre um array
  const safeReports = Array.isArray(reports) ? reports : []

  useEffect(() => {
    loadReports()
  }, [statusFilter, page])

  const loadReports = async () => {
    try {
      setLoading(true)
      
      // Import dinâmico para evitar problemas
      const { default: authService } = await import('../../services/authService.js')
      
      // Backend espera status: pending | reviewed | dismissed | all
      const response = await authService.secureRequest('get', '/api/reports', null, {
        params: {
          page,
          status: statusFilter
        }
      })
      
      const data = response.data || {}
      setReports(Array.isArray(data.data) ? data.data : [])
      setTotalPages(data.pagination?.pages || 1)
    } catch (error) {
      setReports([])
      setTotalPages(1)
    } finally {
      setLoading(false)
    }
  }

  const handleReportAction = async (reportId, action) => {
    try {
      const { default: authService } = await import('../../services/authService.js')
      
      // Mapear ação do frontend para o backend
      const backendAction = action === 'approve' ? 'approve' : 'dismiss'
      
      const response = await authService.secureRequest(
        'post',
        `/api/reports/${reportId}/review`,
        { action: backendAction }
      )
      
      if (response.ok || response.data) {
        loadReports() // Recarregar lista
        setSelectedReport(null) // Fechar modal
      }
    } catch (error) {
    }
  }

  const getReportTypeIcon = (type) => {
    switch (type) {
      case 'post': return <FileText size={16} />
      case 'comment': return <MessageSquare size={16} />
      case 'user': return <User size={16} />
      default: return <AlertTriangle size={16} />
    }
  }

  const getReportTypeLabel = (type) => {
    switch (type) {
      case 'post': return 'Post'
      case 'comment': return 'Comentário'
      case 'user': return 'Usuário'
      default: return 'Outro'
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <div>Carregando denúncias...</div>
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
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              padding: '10px 12px',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              background: 'var(--bg)',
              color: 'var(--text)',
              fontSize: '14px'
            }}
          >
            <option value="pending">Pendentes</option>
            <option value="reviewed">Aprovadas</option>
            <option value="dismissed">Rejeitadas</option>
            <option value="all">Todas</option>
          </select>
          
          <div style={{ marginLeft: 'auto', fontSize: '14px', color: 'var(--muted)' }}>
            {reports.length} denúncia(s) encontrada(s)
          </div>
        </div>
      </div>

      {/* Reports List */}
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
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Denúncia</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Reporter</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Motivo</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Data</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Status</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {safeReports.map((report) => (
                <tr key={report.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '8px',
                        background: 'var(--primary-bg)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--primary)'
                      }}>
                        {getReportTypeIcon(report.target_type)}
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--text)' }}>
                          {getReportTypeLabel(report.target_type)}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--muted)' }}>
                          ID: {report.target_id?.substring(0, 8)}...
                        </div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Avatar src={report.reporter?.avatar_url} size={24} />
                      <span style={{ fontSize: '14px', color: 'var(--text)' }}>
                        @{report.reporter?.username}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '16px' }}>
                    <div style={{ fontSize: '14px', color: 'var(--text)' }}>
                      {report.reason}
                    </div>
                    {report.description && (
                      <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '4px' }}>
                        {report.description.substring(0, 100)}...
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '16px', fontSize: '14px', color: 'var(--muted)' }}>
                    {new Date(report.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '16px' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontWeight: 600,
                      background: 
                        report.status === 'pending' ? 'var(--warning-bg)' :
                        report.status === 'reviewed' ? 'var(--success-bg)' :
                        'var(--danger-bg)',
                      color: 
                        report.status === 'pending' ? 'var(--warning)' :
                        report.status === 'reviewed' ? 'var(--success)' :
                        'var(--danger)'
                    }}>
                      {report.status === 'pending' ? 'Pendente' :
                       report.status === 'reviewed' ? 'Aprovada' : 'Rejeitada'}
                    </span>
                  </td>
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedReport(report)}
                        title="Ver detalhes"
                      >
                        <Eye size={16} />
                      </Button>
                      
                      {report.status === 'pending' && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleReportAction(report.id, 'approve')}
                            title="Aprovar denúncia"
                            style={{ color: 'var(--success)' }}
                          >
                            <Check size={16} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleReportAction(report.id, 'reject')}
                            title="Rejeitar denúncia"
                            style={{ color: 'var(--danger)' }}
                          >
                            <X size={16} />
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {reports.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--muted)' }}>
            Nenhuma denúncia encontrada
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

      {/* Report Detail Modal */}
      {selectedReport && (
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
            maxWidth: '600px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text)' }}>
                Detalhes da Denúncia
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedReport(null)}
              >
                <X size={20} />
              </Button>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <strong>Tipo:</strong> {getReportTypeLabel(selectedReport.target_type)}
              </div>
              <div>
                <strong>ID do Alvo:</strong> {selectedReport.target_id}
              </div>
              <div>
                <strong>Reporter:</strong> @{selectedReport.reporter?.username}
              </div>
              <div>
                <strong>Motivo:</strong> {selectedReport.reason}
              </div>
              <div>
                <strong>Descrição:</strong>
                <p style={{ marginTop: '8px', color: 'var(--text)' }}>
                  {selectedReport.description || 'Nenhuma descrição fornecida'}
                </p>
              </div>
              <div>
                <strong>Data:</strong> {new Date(selectedReport.created_at).toLocaleString()}
              </div>
              
              {selectedReport.status === 'pending' && (
                <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                  <Button
                    variant="primary"
                    onClick={() => handleReportAction(selectedReport.id, 'approve')}
                  >
                    Aprovar Denúncia
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => handleReportAction(selectedReport.id, 'reject')}
                    style={{ color: 'var(--danger)' }}
                  >
                    Rejeitar Denúncia
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
