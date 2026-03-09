import authService from './authService'

class UserService {
  /**
   * Obtém o perfil de um usuário pelo ID.
   * A lógica de visibilidade (público/privado) é tratada no backend.
   */
  async getProfile(userId) {
    try {
      const response = await authService.api.get(`/api/users/profile/${userId}`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Atualiza o perfil do usuário logado (bio, avatar_url, is_private).
   */
  async updateProfile(profileData) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.put('/api/users/profile', profileData)
      
      // Se a atualização for bem-sucedida, atualizamos o usuário no authService
      if (response.data.user) {
        authService.setUser(response.data.user)
      }
      
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Realiza o upload de um novo avatar.
   * O arquivo é processado com validação de segurança no backend.
   */
  async uploadAvatar(file) {
    try {
      await authService.ensureCsrfToken()
      const formData = new FormData()
      formData.append('avatar', file)

      const response = await authService.api.post('/api/users/upload-avatar', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      // Atualiza a URL do avatar no usuário local
      const currentUser = authService.getUser()
      if (currentUser && response.data.avatar_url) {
        authService.setUser({ ...currentUser, avatar_url: response.data.avatar_url })
      }

      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Bloqueia um usuário.
   */
  async blockUser(userId) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.post(`/api/users/block/${userId}`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Desbloqueia um usuário.
   */
  async unblockUser(userId) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.delete(`/api/users/block/${userId}`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Segue um usuário.
   */
  async followUser(userId) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.post(`/api/users/follow/${userId}`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Deixa de seguir um usuário.
   */
  async unfollowUser(userId) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.delete(`/api/users/follow/${userId}`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Busca solicitações de follow pendentes recebidas.
   */
  async getFollowRequests() {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.get('/api/users/follow-requests')
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Aceita uma solicitação de follow.
   */
  async acceptFollowRequest(requestId) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.post(`/api/users/follow-request/${requestId}/accept`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Rejeita uma solicitação de follow.
   */
  async rejectFollowRequest(requestId) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.post(`/api/users/follow-request/${requestId}/reject`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Busca usuários.
   */
  async searchUsers(query, page = 1, limit = 20) {
    try {
      const response = await authService.api.get('/api/users/search', {
        params: { q: query, page, limit }
      })
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }
}

const userService = new UserService()
export default userService
