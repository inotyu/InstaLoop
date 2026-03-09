import { useState, useEffect, useRef } from 'react'
import { messageService } from '../../services/messageService.js'
import MessageInput from './MessageInput.jsx'

export default function MessageThread({ userId, onBack }) {
  const [messages, setMessages] = useState([])
  const [otherUser, setOtherUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (userId) {
      loadConversation()
    }
  }, [userId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const loadConversation = async () => {
    try {
      setLoading(true)
      const data = await messageService.getConversationMessages(userId)
      setMessages(data.messages)
      setOtherUser(data.other_user)
    } catch (err) {
      setError('Erro ao carregar conversa')
    } finally {
      setLoading(false)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSendMessage = async (content, mediaUrl) => {
    try {
      const result = await messageService.sendMessage(userId, content, mediaUrl)
      setMessages(prev => [...prev, {
        id: result.message_data.id,
        content: result.message_data.content,
        media_url: result.message_data.media_url,
        created_at: result.message_data.created_at,
        is_from_me: true,
        sender: result.message_data.sender
      }])
    } catch (err) {
      alert('Erro ao enviar mensagem')
    }
  }

  const handleDeleteMessage = async (messageId) => {
    try {
      await messageService.deleteMessage(messageId)
      setMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { ...msg, is_deleted: true, content: '[Mensagem apagada]' }
          : msg
      ))
    } catch (err) {
    }
  }

  if (loading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        Carregando conversa...
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'red' }}>
        {error}
      </div>
    )
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{ 
        padding: 16, 
        borderBottom: '1px solid var(--border)', 
        display: 'flex', 
        alignItems: 'center',
        gap: 12
      }}>
        {onBack && (
          <button 
            onClick={onBack}
            style={{ 
              background: 'none', 
              border: 'none', 
              cursor: 'pointer',
              padding: 4
            }}
          >
            ←
          </button>
        )}
        
        <img
          src={otherUser?.avatar_url ? `http://localhost:5000${otherUser.avatar_url}` : '/default-avatar.png'}
          alt={otherUser?.username}
          onError={(e) => {
            e.target.src = 'https://picsum.photos/seed/' + otherUser?.username + '/32/32.jpg'
          }}
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            objectFit: 'cover'
          }}
        />
        
        <div style={{ fontWeight: 600 }}>
          {otherUser?.username}
        </div>
      </div>

      {/* Messages */}
      <div style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }}>
        {messages.length === 0 ? (
          <div style={{ 
            textAlign: 'center', 
            color: 'var(--muted)',
            marginTop: 40
          }}>
            Nenhuma mensagem ainda. Comece a conversar!
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              style={{
                display: 'flex',
                justifyContent: message.is_from_me ? 'flex-end' : 'flex-start'
              }}
            >
              <div
                style={{
                  maxWidth: '70%',
                  padding: 12,
                  borderRadius: 12,
                  backgroundColor: message.is_from_me ? 'var(--primary)' : 'var(--accent)',
                  color: message.is_from_me ? 'white' : 'inherit',
                  position: 'relative'
                }}
              >
                {message.is_deleted ? (
                  <em style={{ fontStyle: 'italic', color: 'var(--muted)' }}>
                    [Mensagem apagada]
                  </em>
                ) : (
                  <>
                    {message.content && (
                      <div style={{ marginBottom: message.media_url ? 8 : 0 }}>
                        {message.content}
                      </div>
                    )}
                    
                    {message.media_url && (
                      <img
                        src={message.media_url.startsWith('http') ? message.media_url : `http://localhost:5000${message.media_url}`}
                        alt="Mídia"
                        style={{
                          maxWidth: '100%',
                          maxHeight: 200,
                          borderRadius: 8,
                          objectFit: 'cover'
                        }}
                      />
                    )}
                  </>
                )}

                {!message.is_deleted && message.is_from_me && (
                  <button
                    onClick={() => handleDeleteMessage(message.id)}
                    style={{
                      position: 'absolute',
                      top: 4,
                      right: 4,
                      background: 'none',
                      border: 'none',
                      color: 'rgba(255,255,255,0.7)',
                      cursor: 'pointer',
                      fontSize: 12,
                      padding: 2
                    }}
                    title="Apagar mensagem"
                  >
                    ×
                  </button>
                )}

                <div style={{ 
                  fontSize: 11, 
                  opacity: 0.7, 
                  marginTop: 4,
                  textAlign: 'right'
                }}>
                  {new Date(message.created_at).toLocaleTimeString('pt-BR', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <MessageInput onSendMessage={handleSendMessage} />
    </div>
  )
}
