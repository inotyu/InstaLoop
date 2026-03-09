import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import AppShell from '../components/layout/AppShell.jsx'
import SuggestionsPanel from '../components/suggestions/SuggestionsPanel.jsx'
import Avatar from '../components/ui/Avatar.jsx'
import Button from '../components/ui/Button.jsx'
import PostCard from '../components/post/PostCard.jsx'
import authService from '../services/authService.js'
import postService from '../services/postService.js'

export default function Post() {
  const { postId } = useParams()
  const navigate = useNavigate()
  const [post, setPost] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

  useEffect(() => {
    const loadPost = async () => {
      try {
        setLoading(true)
        const response = await postService.getPost(postId)
        setPost(response)
        setError(null)
      } catch (err) {
        setError('Publicação não encontrada')
        setPost(null)
      } finally {
        setLoading(false)
      }
    }

    if (postId) {
      loadPost()
    }
  }, [postId])

  const handlePostUpdate = (updatedPost) => {
    setPost(updatedPost)
  }

  if (loading) {
    return (
      <AppShell>
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <div>Carregando publicação...</div>
        </div>
      </AppShell>
    )
  }

  if (error || !post) {
    return (
      <AppShell>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 40, gap: 20 }}>
          <div style={{ fontSize: 18, fontWeight: 600 }}>Publicação não encontrada</div>
          <Button onClick={() => navigate(-1)} variant="ghost">Voltar</Button>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell right={<SuggestionsPanel />}>
      <div style={{ maxWidth: '600px', margin: '0 auto', padding: '20px 0' }}>
        {/* Header com informações do autor */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
          <Link to={`/profile/${post.author.id}`}>
            <Avatar src={post.author.avatar_url} ring size={48} />
          </Link>
          <div style={{ flex: 1 }}>
            <Link to={`/profile/${post.author.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div style={{ fontWeight: 900, fontSize: 16 }}>@{post.author.username}</div>
            </Link>
            <div style={{ color: 'var(--muted)', fontSize: 13 }}>
              {new Date(post.created_at).toLocaleString()}
            </div>
          </div>
          <Button onClick={() => navigate(-1)} variant="ghost" size="sm">
            Voltar
          </Button>
        </div>

        {/* Post completo */}
        <PostCard post={post} onUpdate={handlePostUpdate} />
      </div>
    </AppShell>
  )
}
