import { useState, useEffect } from 'react'
import { messageService } from '../../services/messageService.js'

export default function ConversationList({ onSelectConversation, selectedUserId }) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      setLoading(true)
      const data = await messageService.getConversations()
      setConversations(data.conversations)
    } catch (err) {
      setError('Erro ao carregar conversas')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 16, textAlign: 'center' }}>
        Carregando conversas...
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 16, color: 'red', textAlign: 'center' }}>
        {error}
      </div>
    )
  }

  return (
    <div style={{ borderRight: '1px solid var(--border)', height: '100%' }}>
      <div style={{ padding: 16, borderBottom: '1px solid var(--border)', fontWeight: 600 }}>
        Conversas
      </div>
      
      {conversations.length === 0 ? (
        <div style={{ padding: 16, color: 'var(--muted)', textAlign: 'center' }}>
          <div style={{ marginBottom: 16 }}>
            Nenhuma conversa ainda
          </div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>
            Você só pode conversar com usuários que te seguem de volta.
            Siga alguém e espere que ela também te siga para iniciar uma conversa!
          </div>
        </div>
      ) : (
        <div style={{ overflowY: 'auto', height: 'calc(100% - 60px)' }}>
          {conversations.map((conv) => (
            <div
              key={conv.other_user.id}
              onClick={() => onSelectConversation(conv.other_user.id)}
              style={{
                padding: 12,
                cursor: 'pointer',
                borderBottom: '1px solid var(--border)',
                backgroundColor: selectedUserId === conv.other_user.id ? 'var(--accent)' : 'transparent',
                display: 'flex',
                alignItems: 'center',
                gap: 12
              }}
            >
              <img
                src={conv.other_user.avatar_url ? `http://localhost:5000${conv.other_user.avatar_url}` : '/default-avatar.png'}
                alt={conv.other_user.username}
                onError={(e) => {
                  e.target.src = 'https://picsum.photos/seed/' + conv.other_user.username + '/40/40.jpg'
                }}
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  objectFit: 'cover'
                }}
              />
              
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500, fontSize: 14 }}>
                  {conv.other_user.username}
                </div>
                <div style={{ 
                  fontSize: 12, 
                  color: 'var(--muted)', 
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {conv.last_message ? (conv.last_message.content || '[Mídia]') : 'Sem mensagens ainda'}
                </div>
              </div>
              
              {conv.unread_count > 0 && (
                <div style={{
                  backgroundColor: 'var(--primary)',
                  color: 'white',
                  borderRadius: '50%',
                  width: 20,
                  height: 20,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 11,
                  fontWeight: 600
                }}>
                  {conv.unread_count}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
