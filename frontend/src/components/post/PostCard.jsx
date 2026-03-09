import { Heart, MessageCircle, Send, Bookmark, Trash2, Flag, Edit, MoreVertical } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import DOMPurify from 'dompurify'
import Avatar from '../ui/Avatar.jsx'
import postService from '../../services/postService.js'
import authService from '../../services/authService.js'
import './postcard.css'

export default function PostCard({ post, onUpdate }) {
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(false)
  const [showComments, setShowComments] = useState(false)
  const [showReportModal, setShowReportModal] = useState(false)
  const [reportReason, setReportReason] = useState('')
  const [reportDescription, setReportDescription] = useState('')
  const [showOptionsMenu, setShowOptionsMenu] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [editMediaUrl, setEditMediaUrl] = useState('')
  const menuRef = useRef(null)
  
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'
  const currentUser = authService.getUser()
  const isOwner = currentUser?.id === post?.user_id
  
  // Fechar menu ao clicar fora
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowOptionsMenu(false)
      }
    }
    
    if (showOptionsMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showOptionsMenu])
  
  const username = post?.author?.username || 'user'
  const avatar = post?.author?.avatar_url || null
  const createdAt = post?.created_at ? new Date(post.created_at).toLocaleString() : ''
  const mediaUrl = post?.media_url && !post.media_url.startsWith('http') 
    ? `${API_BASE_URL}${post.media_url}` 
    : post?.media_url

  async function handleLike() {
    try {
      const response = await postService.toggleLike(post.id)
      // Update the post with new like data
      if (onUpdate) {
        onUpdate({
          ...post,
          is_liked: response.liked,
          likes_count: response.likes_count
        })
      }
    } catch (err) {
    }
  }

  async function handleComment(e) {
    e.preventDefault()
    if (!comment.trim() || loading) return
    
    setLoading(true)
    try {
      const response = await postService.addComment(post.id, comment)
      
      // Update the post with new comment data
      if (onUpdate) {
        onUpdate({
          ...post,
          comments_count: (post.comments_count || 0) + 1,
          comments: [...(post.comments || []), response.comment]
        })
      }
      
      setComment('')
      setShowComments(true)
    } catch (err) {
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteComment(commentId) {
    if (!window.confirm('Tem certeza que deseja excluir este comentário?')) return
    
    try {
      await postService.deleteComment(commentId)
      
      // Update the post by removing the comment
      if (onUpdate) {
        onUpdate({
          ...post,
          comments_count: Math.max(0, (post.comments_count || 0) - 1),
          comments: (post.comments || []).filter(c => c.id !== commentId)
        })
      }
    } catch (err) {
      alert('Erro ao excluir comentário')
    }
  }

  async function handleDelete() {
    if (!window.confirm('Tem certeza que deseja excluir este post?')) return
    
    try {
      await postService.deletePost(post.id)
      // Remove post da interface
      if (onUpdate) {
        onUpdate(null) // null indica que o post foi removido
      }
    } catch (err) {
      alert('Erro ao excluir post')
    }
  }

  async function handleEdit() {
    setEditContent(post.content || '')
    setEditMediaUrl(post.media_url || '')
    setIsEditing(true)
    setShowEditModal(true)
    setShowOptionsMenu(false)
  }

  async function handleUpdate() {
    try {
      setLoading(true)
      const response = await postService.updatePost(post.id, editContent.trim(), editMediaUrl)
      
      // Update the post with new data
      if (onUpdate) {
        onUpdate({
          ...post,
          content: editContent.trim(),
          media_url: editMediaUrl
        })
      }
      
      setIsEditing(false)
      setEditContent('')
      setEditMediaUrl('')
    } catch (err) {
      alert('Erro ao editar post')
    } finally {
      setLoading(false)
    }
  }

  async function handleReport() {
    if (!reportReason.trim()) return
    
    try {
      // Usar o endpoint oficial de denúncia de post
      await authService.secureRequest(
        'post', 
        `/api/posts/${post.id}/report`,
        {
          target_type: 'post',
          target_id: post.id,
          reason: reportReason
        }
      )

      alert('Denúncia enviada com sucesso!')
      setShowReportModal(false)
      setReportReason('')
      setReportDescription('')
    } catch (err) {
      alert(err?.response?.data?.error || 'Erro ao enviar denúncia')
    }
  }

  return (
    <article className="post">
      <header className="post-header">
        <div className="post-user">
          <Avatar src={avatar} ring size={36} />
          <div className="post-userText">
            <div className="post-username">@{username}</div>
            <div className="post-meta">{createdAt}</div>
          </div>
        </div>
        {isOwner && (
          <div style={{ position: 'relative' }} ref={menuRef}>
            <button 
              onClick={handleEdit}
              title="Editar post" 
              style={{ 
                background: 'none', 
                border: 'none', 
                cursor: 'pointer',
                marginRight: '8px',
                color: 'var(--text)',
                padding: '4px'
              }}
            >
              <Edit size={18} />
            </button>
            <button 
              className="post-more" 
              onClick={() => setShowOptionsMenu(!showOptionsMenu)} 
              title="Opções" 
              style={{ background: 'none', border: 'none', cursor: 'pointer' }}
            >
              <MoreVertical size={18} />
            </button>
            
            {showOptionsMenu && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                background: 'var(--panel)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                zIndex: 1000,
                minWidth: 120
              }}>
                <button 
                  onClick={handleDelete}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: 'none',
                    background: 'none',
                    color: 'var(--danger)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '14px'
                  }}
                >
                  <Trash2 size={16} />
                  Excluir
                </button>
              </div>
            )}
          </div>
        )}
      </header>

      {mediaUrl ? (
        <div className="post-media" onDoubleClick={handleLike}>
          <img alt="" src={mediaUrl} loading="lazy" />
        </div>
      ) : null}

      <div className="post-body">
        <div className="post-actions">
          <div className="post-actionsLeft">
            <button 
              className={post?.is_liked ? 'post-actionBtn liked' : 'post-actionBtn'} 
              onClick={handleLike}
            >
              <Heart size={24} fill={post?.is_liked ? "var(--danger)" : "none"} color={post?.is_liked ? "var(--danger)" : "currentColor"} />
            </button>
            <button className="post-actionBtn" onClick={() => setShowComments(!showComments)}>
              <MessageCircle size={24} />
            </button>
            <button className="post-actionBtn">
              <Send size={24} />
            </button>
          </div>
          <button className="post-actionBtn">
            <Bookmark size={24} />
          </button>
        </div>

        <div className="post-likesCount">
          {post?.likes_count || 0} curtidas
        </div>

        <div className="post-caption">
          <span className="post-captionUser">@{username}</span>{' '}
          <span
            className="post-content"
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(post?.content || '') }}
          />
        </div>

        {post?.comments_count > 0 && !showComments && (
          <button className="post-viewComments" onClick={() => setShowComments(true)}>
            Ver todos os {post.comments_count} comentários
          </button>
        )}

        {showComments && (
          <div className="post-commentsList">
            {post?.comments?.map(c => {
              const isCommentOwner = currentUser?.id === c.author?.id
              return (
                <div key={c.id} className="post-comment">
                  <span className="post-commentUser">@{c.author?.username}</span>{' '}
                  <span className="post-commentText">{c.content}</span>
                  {isCommentOwner && (
                    <button 
                      onClick={() => handleDeleteComment(c.id)}
                      title="Excluir comentário"
                      style={{
                        marginLeft: '8px',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: 'var(--muted)',
                        fontSize: '12px',
                        padding: '2px'
                      }}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <form className="post-commentForm" onSubmit={handleComment}>
          <input 
            placeholder="Adicione um comentário..." 
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            disabled={loading}
          />
          <button type="submit" disabled={!comment.trim() || loading}>
            Publicar
          </button>
        </form>
      </div>

      {/* Modal de Denúncia */}
      {showReportModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--panel)',
            padding: '24px',
            borderRadius: '12px',
            maxWidth: '400px',
            width: '90%',
            border: '1px solid var(--border)'
          }}>
            <h3 style={{ margin: '0 0 16px 0', color: 'var(--text)' }}>Denunciar Publicação</h3>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', color: 'var(--text)' }}>
                Motivo da denúncia
              </label>
              <select 
                value={reportReason} 
                onChange={(e) => setReportReason(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  background: 'var(--background)',
                  color: 'var(--text)'
                }}
              >
                <option value="">Selecione um motivo</option>
                <option value="spam">Spam</option>
                <option value="inappropriate">Conteúdo inapropriado</option>
                <option value="harassment">Assédio</option>
                <option value="violence">Violência</option>
                <option value="copyright">Violação de direitos autorais</option>
                <option value="other">Outro</option>
              </select>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', color: 'var(--text)' }}>
                Descrição (opcional)
              </label>
              <textarea 
                value={reportDescription}
                onChange={(e) => setReportDescription(e.target.value)}
                placeholder="Descreva o motivo da denúncia..."
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  background: 'var(--background)',
                  color: 'var(--text)',
                  minHeight: '80px',
                  resize: 'vertical'
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button 
                onClick={() => {
                  setShowReportModal(false)
                  setReportReason('')
                  setReportDescription('')
                }}
                style={{
                  padding: '8px 16px',
                  border: '1px solid var(--border)',
                  background: 'var(--background)',
                  color: 'var(--text)',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Cancelar
              </button>
              <button 
                onClick={handleReport}
                disabled={!reportReason.trim()}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  background: reportReason.trim() ? 'var(--danger)' : 'var(--muted)',
                  color: 'white',
                  borderRadius: '4px',
                  cursor: reportReason.trim() ? 'pointer' : 'not-allowed'
                }}
              >
                Enviar Denúncia
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Edição */}
      {showEditModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--panel)',
            padding: '24px',
            borderRadius: '12px',
            maxWidth: '500px',
            width: '90%',
            border: '1px solid var(--border)'
          }}>
            <h3 style={{ margin: '0 0 16px 0', color: 'var(--text)' }}>Editar Publicação</h3>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', color: 'var(--text)' }}>
                Conteúdo
              </label>
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                placeholder="Digite o conteúdo da publicação..."
                rows={4}
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  background: 'var(--background)',
                  color: 'var(--text)',
                  resize: 'vertical'
                }}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', color: 'var(--text)' }}>
                URL da Imagem (opcional)
              </label>
              <input
                type="url"
                value={editMediaUrl}
                onChange={(e) => setEditMediaUrl(e.target.value)}
                placeholder="https://exemplo.com/imagem.jpg"
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  background: 'var(--background)',
                  color: 'var(--text)'
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button 
                onClick={() => {
                  setShowEditModal(false)
                  setEditContent('')
                  setEditMediaUrl('')
                }}
                style={{
                  padding: '8px 16px',
                  border: '1px solid var(--border)',
                  background: 'transparent',
                  color: 'var(--text)',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Cancelar
              </button>
              <button 
                onClick={handleUpdate}
                disabled={loading || (!editContent.trim() && !editMediaUrl.trim())}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  background: (loading || (!editContent.trim() && !editMediaUrl.trim())) ? 'var(--muted)' : 'var(--primary)',
                  color: 'white',
                  borderRadius: '4px',
                  cursor: (loading || (!editContent.trim() && !editMediaUrl.trim())) ? 'not-allowed' : 'pointer'
                }}
              >
                {loading ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </article>
  )
}
