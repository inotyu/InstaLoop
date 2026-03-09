import { useState, useEffect } from 'react'
import userService from '../services/userService.js'
import Avatar from './ui/Avatar.jsx'
import Button from './ui/Button.jsx'

export default function FollowRequestsPanel() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)

  useEffect(() => {
    loadRequests()
  }, [])

  async function loadRequests() {
    setLoading(true)
    try {
      const data = await userService.getFollowRequests()
      setRequests(data.requests || [])
    } catch (err) {
    } finally {
      setLoading(false)
    }
  }

  async function handleAccept(requestId) {
    setActionLoading(requestId)
    try {
      await userService.acceptFollowRequest(requestId)
      setRequests(prev => prev.filter(req => req.id !== requestId))
    } catch (err) {
      await loadRequests()
    } finally {
      setActionLoading(null)
    }
  }

  async function handleReject(requestId) {
    setActionLoading(requestId)
    try {
      await userService.rejectFollowRequest(requestId)
      setRequests(prev => prev.filter(req => req.id !== requestId))
    } catch (err) {
      await loadRequests()
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        Carregando solicitações...
      </div>
    )
  }

  if (requests.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>📭</div>
        <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>
          Nenhuma solicitação pendente
        </div>
        <div style={{ fontSize: 14 }}>
          Quando alguém solicitar seguir você, aparecerá aqui
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <div style={{ 
        fontWeight: 700, 
        fontSize: 18, 
        marginBottom: 24,
        display: 'flex',
        alignItems: 'center',
        gap: 8
      }}>
        📋 Solicitações de follow ({requests.length})
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {requests.map(request => (
          <div 
            key={request.id}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 16, 
              padding: 16,
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              background: 'var(--panel)'
            }}
          >
            <Avatar 
              size={48} 
              src={request.follower.avatar_url} 
              alt={request.follower.username}
            />
            
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>
                @{request.follower.username}
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                Quer seguir você
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <Button 
                size="sm" 
                variant="primary"
                onClick={() => handleAccept(request.id)}
                disabled={actionLoading === request.id}
                style={{ fontSize: 12 }}
              >
                {actionLoading === request.id ? '...' : 'Aceitar'}
              </Button>
              
              <Button 
                size="sm" 
                variant="ghost"
                onClick={() => handleReject(request.id)}
                disabled={actionLoading === request.id}
                style={{ fontSize: 12, color: 'var(--danger)' }}
              >
                {actionLoading === request.id ? '...' : 'Rejeitar'}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
