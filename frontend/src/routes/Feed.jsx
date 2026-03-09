import { useEffect, useState, useCallback } from 'react'
import authService from '../services/authService.js'
import postService from '../services/postService.js'
import AppShell from '../components/layout/AppShell.jsx'
import SuggestionsPanel from '../components/suggestions/SuggestionsPanel.jsx'
import PostCard from '../components/post/PostCard.jsx'
import CreatePost from '../components/post/CreatePost.jsx'

export default function Feed() {
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)

  const handlePostUpdate = useCallback((updatedPost) => {
    setPosts(prevPosts => 
      prevPosts.map(post => 
        post.id === updatedPost.id ? updatedPost : post
      )
    )
  }, [])

  const loadFeed = useCallback(async () => {
    try {
      await authService.ensureCsrfToken()
      const res = await postService.getFeed()
      setPosts(res.posts || [])
    } catch (err) {
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadFeed()
  }, [loadFeed])

  return (
    <AppShell right={<SuggestionsPanel />}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <CreatePost onPostCreated={loadFeed} />
        
        {loading ? (
          <div style={{ color: 'var(--muted)', textAlign: 'center', padding: 20 }}>Carregando feed...</div>
        ) : (
          <>
            {posts.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: 40, 
                border: '1px solid var(--border)', 
                borderRadius: 'var(--radius)',
                background: 'var(--panel)'
              }}>
                <div style={{ fontWeight: 800 }}>Bem-vindo ao InstaLoop</div>
                <div style={{ color: 'var(--muted)', fontSize: 14, marginTop: 4 }}>
                  Siga pessoas para ver publicações aqui.
                </div>
              </div>
            ) : (
              posts.map((p) => <PostCard key={p.id} post={p} onUpdate={handlePostUpdate} />)
            )}
          </>
        )}
      </div>
    </AppShell>
  )
}
