import { useState, useEffect } from 'react'
import { Search, Filter, Ban, Shield, UserCheck, UserX, Eye } from 'lucide-react'
import Button from '../ui/Button.jsx'
import Avatar from '../ui/Avatar.jsx'

export default function UserManagement() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  useEffect(() => {
    loadUsers()
  }, [search, statusFilter, page])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page,
        search,
        status: statusFilter
      })
      
      const response = await fetch(`/admin/users?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      })
      const data = await response.json()
      setUsers(data.users || [])
      setTotalPages(data.pagination?.pages || 1)
    } catch (error) {
    } finally {
      setLoading(false)
    }
  }

  const handleUserAction = async (userId, action) => {
    try {
      const response = await fetch(`/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ action })
      })
      
      if (response.ok) {
        loadUsers() // Recarregar lista
      }
    } catch (error) {
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <div>Carregando usuários...</div>
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
              placeholder="Buscar usuários..."
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
            <option value="all">Todos</option>
            <option value="active">Ativos</option>
            <option value="banned">Banidos</option>
            <option value="admin">Admins</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
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
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Usuário</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Email</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Status</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Cadastro</th>
                <th style={{ padding: '16px', textAlign: 'left', fontSize: '12px', color: 'var(--muted)' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <Avatar src={user.avatar_url} size={32} />
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--text)' }}>
                          @{user.username}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--muted)' }}>
                          {user.followers_count || 0} seguidores
                        </div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '16px', fontSize: '14px', color: 'var(--text)' }}>
                    {user.email}
                  </td>
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      {user.is_admin && (
                        <span style={{
                          padding: '4px 8px',
                          background: 'var(--primary-bg)',
                          color: 'var(--primary)',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: 600
                        }}>
                          Admin
                        </span>
                      )}
                      {user.is_banned ? (
                        <span style={{
                          padding: '4px 8px',
                          background: 'var(--danger-bg)',
                          color: 'var(--danger)',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: 600
                        }}>
                          Banido
                        </span>
                      ) : (
                        <span style={{
                          padding: '4px 8px',
                          background: 'var(--success-bg)',
                          color: 'var(--success)',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: 600
                        }}>
                          Ativo
                        </span>
                      )}
                    </div>
                  </td>
                  <td style={{ padding: '16px', fontSize: '14px', color: 'var(--muted)' }}>
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => window.open(`/profile/${user.id}`, '_blank')}
                        title="Ver perfil"
                      >
                        <Eye size={16} />
                      </Button>
                      
                      {!user.is_admin && (
                        <>
                          {user.is_banned ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleUserAction(user.id, 'unban')}
                              title="Desbanir"
                              style={{ color: 'var(--success)' }}
                            >
                              <UserCheck size={16} />
                            </Button>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleUserAction(user.id, 'ban')}
                              title="Banir"
                              style={{ color: 'var(--danger)' }}
                            >
                              <Ban size={16} />
                            </Button>
                          )}
                          
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleUserAction(user.id, user.is_admin ? 'unadmin' : 'admin')}
                            title={user.is_admin ? 'Remover admin' : 'Tornar admin'}
                            style={{ color: 'var(--warning)' }}
                          >
                            <Shield size={16} />
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
        
        {users.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--muted)' }}>
            Nenhum usuário encontrado
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
    </div>
  )
}
