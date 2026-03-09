import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import AppShell from '../components/layout/AppShell.jsx'
import ConversationList from '../components/messages/ConversationList.jsx'
import MessageThread from '../components/messages/MessageThread.jsx'

export default function Messages() {
  const [selectedUserId, setSelectedUserId] = useState(null)
  const [searchParams] = useSearchParams()

  useEffect(() => {
    const userParam = searchParams.get('user')
    if (userParam) {
      setSelectedUserId(userParam)
    }
  }, [searchParams])

  const handleSelectConversation = (userId) => {
    setSelectedUserId(userId)
  }

  const handleBackToConversations = () => {
    setSelectedUserId(null)
  }

  return (
    <AppShell>
      <div style={{ 
        height: 'calc(100vh - 60px)', // Ajustar baseado no header
        display: 'flex',
        border: '1px solid var(--border)',
        borderRadius: 8,
        overflow: 'hidden'
      }}>
        {/* Lista de conversas */}
        <div style={{ 
          width: selectedUserId ? '300px' : '100%', 
          borderRight: selectedUserId ? '1px solid var(--border)' : 'none',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <ConversationList 
            onSelectConversation={handleSelectConversation}
            selectedUserId={selectedUserId}
          />
        </div>

        {/* Thread de mensagens */}
        {selectedUserId && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <MessageThread 
              userId={selectedUserId}
              onBack={handleBackToConversations}
            />
          </div>
        )}
      </div>
    </AppShell>
  )
}
