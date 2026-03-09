import authService from './authService'

class PostService {
  /**
   * Obtém um post específico com todos os detalhes.
   */
  async getPost(postId) {
    try {
      const response = await authService.api.get(`/api/posts/${postId}`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Obtém posts para o feed (usuários seguidos).
   */
  async getFeed(page = 1, limit = 20) {
    try {
      const response = await authService.api.get('/api/posts/feed', {
        params: { page, limit }
      })
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Obtém posts de um usuário específico.
   */
  async getUserPosts(userId, page = 1, limit = 20) {
    try {
      const response = await authService.api.get(`/api/posts/user/${userId}`, {
        params: { page, limit }
      })
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Cria um novo post (texto e/ou imagem).
   */
  async createPost(content, file) {
    try {
      await authService.ensureCsrfToken()
      const formData = new FormData()
      if (content) formData.append('content', content)
      if (file) formData.append('media', file)

      const response = await authService.api.post('/api/posts/create', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Exclui um post próprio.
   */
  async deletePost(postId) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.delete(`/api/posts/${postId}`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Edita um post próprio.
   */
  async updatePost(postId, content, mediaUrl) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.put(`/api/posts/${postId}`, {
        content,
        media_url: mediaUrl
      })
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Curte ou descurte um post.
   */
  async toggleLike(postId) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.post(`/api/posts/${postId}/like`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Adiciona um comentário a um post.
   */
  async addComment(postId, content) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.post(`/api/posts/${postId}/comment`, { content })
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }

  /**
   * Exclui um comentário próprio.
   */
  async deleteComment(commentId) {
    try {
      await authService.ensureCsrfToken()
      const response = await authService.api.delete(`/api/posts/comment/${commentId}`)
      return response.data
    } catch (error) {
      throw authService.handleError(error)
    }
  }
}

const postService = new PostService()
export default postService
