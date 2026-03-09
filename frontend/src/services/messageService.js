import axios from 'axios'
import authService from './authService'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'

class MessageService {
  constructor() {
    // Usar a instância do authService para compartilhar token
    this.client = authService.api
  }

  // Buscar conversas do usuário
  async getConversations(page = 1, limit = 20) {
    const response = await this.client.get('/api/messages/conversations', {
      params: { page, limit }
    })
    return response.data
  }

  // Buscar mensagens de uma conversa
  async getConversationMessages(userId, page = 1, limit = 50) {
    const response = await this.client.get(`/api/messages/conversation/${userId}`, {
      params: { page, limit }
    })
    return response.data
  }

  // Enviar mensagem
  async sendMessage(receiverId, content, mediaUrl = null) {
    const response = await this.client.post('/api/messages', {
      receiver_id: receiverId,
      content,
      media_url: mediaUrl
    })
    return response.data
  }

  // Upload de mídia para mensagens
  async uploadMedia(file) {
    const formData = new FormData()
    formData.append('media', file)

    const response = await this.client.post('/api/messages/upload-media', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  }

  // Apagar mensagem
  async deleteMessage(messageId) {
    const response = await this.client.delete(`/api/messages/${messageId}`)
    return response.data
  }

  // Buscar mensagens
  async searchMessages(query, page = 1, limit = 20) {
    const response = await this.client.get('/api/messages/search', {
      params: { q: query, page, limit }
    })
    return response.data
  }

  // Contagem de mensagens não lidas
  async getUnreadCount() {
    const response = await this.client.get('/api/messages/unread-count')
    return response.data
  }
}

export const messageService = new MessageService()
