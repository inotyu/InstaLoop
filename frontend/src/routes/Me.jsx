import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import AppShell from '../components/layout/AppShell.jsx'
import SuggestionsPanel from '../components/suggestions/SuggestionsPanel.jsx'
import Avatar from '../components/ui/Avatar.jsx'
import Button from '../components/ui/Button.jsx'
import authService from '../services/authService.js'
import postService from '../services/postService.js'

export default function Me() {
  const [user, setUser] = useState(authService.getUser())
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [postsLoading, setPostsLoading] = useState(true)
  const navigate = useNavigate()
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

  // Log para depurar estado atual

  useEffect(() => {
    const loadUserData = async () => {
      try {
        const userData = await authService.getCurrentUser()
        setUser(userData)
      } catch (error) {
        setUser(authService.getUser())
      } finally {
        setLoading(false)
      }
    }

    loadUserData()
  }, [])

  useEffect(() => {
    const loadUserPosts = async () => {
      if (!user?.id) return
      
      try {
        setPostsLoading(true)
        const response = await postService.getUserPosts(user.id)
        setPosts(response.posts || [])
      } catch (error) {
        setPosts([])
      } finally {
        setPostsLoading(false)
      }
    }

    if (user?.id) {
      loadUserPosts()
    }
  }, [user?.id])

  return (
    <AppShell right={<SuggestionsPanel />}>
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>Carregando...</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Avatar size={78} ring src={user?.avatar_url} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ fontWeight: 900, fontSize: 18 }}>@{user?.username || 'user'}</div>
              <div style={{ color: 'var(--muted)', fontSize: 13 }}>{user?.bio || ''}</div>
              
              {/* Estatísticas do perfil */}
              <div style={{ display: 'flex', gap: 24, color: 'var(--text)', fontSize: 14 }}>
                <div><strong>{posts.length}</strong> publicações</div>
                <div><strong>{user?.followers_count || 0}</strong> seguidores</div>
                <div><strong>{user?.following_count || 0}</strong> seguindo</div>
              </div>
              
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <Button as={Link} to="/edit-profile" variant="ghost" size="sm">Editar perfil</Button>
                <Button variant="ghost" size="sm" onClick={async () => { 
    await authService.logout(); 
    navigate('/login'); 
  }}>Sair</Button>
                
                {user?.is_admin && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => navigate(`/${import.meta.env.VITE_ADMIN_ROUTE}`)}
                    style={{
                      background: 'var(--accent)',
                      color: 'var(--accent-foreground)',
                      border: '1px solid var(--accent)'
                    }}
                  >
                    Painel Admin
                  </Button>
                )}
              </div>
            </div>
          </div>
          <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 16, background: 'var(--panel)' }}>
            <div style={{ fontWeight: 800 }}>Publicações</div>
            
            {postsLoading ? (
              <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 6 }}>Carregando publicações...</div>
            ) : posts.length === 0 ? (
              <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 6 }}>Você ainda não fez nenhuma publicação.</div>
            ) : (
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(3, 1fr)', 
                gap: 4,
                marginTop: 8
              }}>
                {posts.map(post => (
                  <Link 
                    key={post.id} 
                    to={`/post/${post.id}`}
                    style={{ 
                      aspectRatio: '1/1', 
                      background: 'var(--panel-2)',
                      cursor: 'pointer',
                      overflow: 'hidden',
                      position: 'relative',
                      textDecoration: 'none'
                    }}
                  >
                    {post.media_url ? (
                      <img 
                        src={post.media_url.startsWith('http') ? post.media_url : `${API_BASE_URL}${post.media_url}`} 
                        alt="" 
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    ) : (
                      <div style={{ 
                        height: '100%', 
                        display: 'flex',
                        flexDirection: 'column',
                        position: 'relative'
                      }}>
                        <div style={{ 
                          padding: 8, 
                          fontSize: 11, 
                          flex: 1,
                          overflow: 'hidden',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          textAlign: 'center'
                        }}>
                          {post.content?.substring(0, 100)}...
                        </div>
                        <div style={{
                          position: 'absolute',
                          bottom: 0,
                          left: 0,
                          right: 0,
                          background: 'rgba(0,0,0,0.1)',
                          color: 'var(--text)',
                          padding: '4px 8px',
                          fontSize: '10px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          borderTop: '1px solid var(--border)'
                        }}>
                          ❤️ {post.likes_count || 0}
                        </div>
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  )
}

