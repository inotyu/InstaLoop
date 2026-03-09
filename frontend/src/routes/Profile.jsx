import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import authService from '../services/authService.js'
import userService from '../services/userService.js'
import postService from '../services/postService.js'
import AppShell from '../components/layout/AppShell.jsx'
import SuggestionsPanel from '../components/suggestions/SuggestionsPanel.jsx'
import Avatar from '../components/ui/Avatar.jsx'
import Button from '../components/ui/Button.jsx'

export default function Profile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const currentUser = authService.getUser()
  const isOwnProfile = currentUser?.id === id
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

  const loadProfileData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await userService.getProfile(id)
      setProfile(data)
      
      // Se puder ver o conteúdo, carrega os posts
      if (!data.is_private || data.is_following || currentUser?.id === id) {
        const postsRes = await postService.getUserPosts(id)
        setPosts(postsRes.posts || [])
      }
      
    } catch (err) {
      if (err.status === 404) {
        setProfile(null)
      }
    } finally {
      setLoading(false)
    }
  }, [id, currentUser?.id])

  useEffect(() => {
    loadProfileData()
  }, [loadProfileData])

  async function handleFollow() {
    setActionLoading(true)
    try {
      let response;
      if (profile.is_following || profile.follow_status === 'pending') {
        // unfollow
        response = await userService.unfollowUser(id)
      } else {
        // follow
        response = await userService.followUser(id)
      }
      
      // reload profile
      await loadProfileData()
    } catch (err) {
      // Mesmo em erro, recarregar para atualizar estado
      await loadProfileData()
    } finally {
      setActionLoading(false)
    }
  }

  async function handleBlock() {
    if (!window.confirm('Deseja bloquear este usuário?')) return
    setActionLoading(true)
    try {
      await userService.blockUser(id)
      navigate('/feed')
    } catch (err) {
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <AppShell right={<SuggestionsPanel />}>
        <div style={{ color: 'var(--muted)', textAlign: 'center', padding: 40 }}>Carregando...</div>
      </AppShell>
    )
  }

  if (!profile) {
    return (
      <AppShell right={<SuggestionsPanel />}>
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <h2 style={{ fontWeight: 900 }}>Usuário não encontrado</h2>
          <p style={{ color: 'var(--muted)' }}>O link pode estar quebrado ou a conta foi removida.</p>
        </div>
      </AppShell>
    )
  }

  const canSeeContent = !profile.is_private || profile.is_following || isOwnProfile

  return (
    <AppShell right={<SuggestionsPanel />}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {/* Header do Perfil */}
        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <Avatar size={86} ring src={profile.avatar_url} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, flex: 1, minWidth: 260 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <div style={{ fontWeight: 900, fontSize: 20 }}>@{profile.username}</div>
              
              {!isOwnProfile && (
                <>
                  <Button 
                    variant={profile.is_following ? 'ghost' : 'primary'} 
                    size="sm" 
                    onClick={handleFollow}
                    disabled={actionLoading}
                  >
                    {profile.is_following ? 'Seguindo' : (profile.follow_status === 'pending' ? 'Pendente' : 'Seguir')}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleBlock} disabled={actionLoading} style={{ color: 'var(--danger)' }}>Bloquear</Button>
                </>
              )}
              
              {isOwnProfile && (
                <Button variant="ghost" size="sm" onClick={() => navigate('/edit-profile')}>Editar perfil</Button>
              )}
            </div>

            <div style={{ display: 'flex', gap: 24, color: 'var(--text)', fontSize: 14 }}>
              <div><strong>{profile.posts_count ?? 0}</strong> publicações</div>
              <div><strong>{profile.followers_count ?? 0}</strong> seguidores</div>
              <div><strong>{profile.following_count ?? 0}</strong> seguindo</div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>@{profile.username}</div>
              <div style={{ fontSize: 14, whiteSpace: 'pre-wrap' }}>{profile.bio || ''}</div>
            </div>
          </div>
        </div>

        <div className="hr" />

        {/* Conteúdo (Posts ou Mensagem de Privado) */}
        {!canSeeContent ? (
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            gap: 12, 
            padding: '60px 20px',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            background: 'var(--panel)'
          }}>
            <div style={{ fontWeight: 900 }}>Esta conta é privada</div>
            <div style={{ color: 'var(--muted)', fontSize: 14, textAlign: 'center' }}>
              Siga para ver suas fotos e vídeos.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ fontWeight: 900, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, display: 'flex', justifyContent: 'center', borderTop: '1px solid var(--text)', paddingTop: 12, marginTop: -12 }}>
              Publicações
            </div>
            
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
                    <>
                      <img 
                        src={post.media_url.startsWith('http') ? post.media_url : `${API_BASE_URL}${post.media_url}`} 
                        alt="" 
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                      {/* Overlay com informações */}
                      <div style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        background: 'linear-gradient(to top, rgba(0,0,0,0.8), transparent)',
                        color: 'white',
                        padding: '8px',
                        fontSize: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px'
                      }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          ❤️ {post.likes_count || 0}
                        </span>
                        {post.content && (
                          <span style={{ 
                            overflow: 'hidden', 
                            textOverflow: 'ellipsis', 
                            whiteSpace: 'nowrap',
                            flex: 1
                          }}>
                            {post.content}
                          </span>
                        )}
                      </div>
                    </>
                  ) : (
                    <div style={{ 
                      height: '100%', 
                      display: 'flex',
                      flexDirection: 'column',
                      position: 'relative'
                    }}>
                      {/* Conteúdo do post */}
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
                      {/* Footer com curtidas */}
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

            {posts.length === 0 && (
              <div style={{ color: 'var(--muted)', fontSize: 13, textAlign: 'center', padding: 40 }}>
                Nenhuma publicação ainda.
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  )
}
