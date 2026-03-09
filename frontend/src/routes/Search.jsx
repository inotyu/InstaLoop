import { useState, useEffect } from 'react'
import AppShell from '../components/layout/AppShell.jsx'
import SuggestionsPanel from '../components/suggestions/SuggestionsPanel.jsx'
import TextField from '../components/ui/TextField.jsx'
import Avatar from '../components/ui/Avatar.jsx'
import Button from '../components/ui/Button.jsx'
import userService from '../services/userService.js'
import { Link } from 'react-router-dom'

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)

  useEffect(() => {
    if (query.length >= 2) {
      searchUsers()
    } else {
      setResults([])
    }
  }, [query, page])

  const searchUsers = async () => {
    if (query.length < 2) return
    
    setLoading(true)
    try {
      const response = await userService.searchUsers(query, page, 20)
      if (page === 1) {
        setResults(response.users || [])
      } else {
        setResults(prev => [...prev, ...(response.users || [])])
      }
      setHasMore(response.pagination?.has_more || false)
    } catch (error) {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleLoadMore = () => {
    if (!loading && hasMore) {
      setPage(prev => prev + 1)
    }
  }

  return (
    <AppShell right={<SuggestionsPanel />}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ fontWeight: 900, fontSize: 18 }}>Pesquisar</div>
        
        <TextField 
          label="Buscar usuários" 
          placeholder="Digite pelo menos 2 caracteres..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setPage(1)
          }}
        />

        {query.length >= 2 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 14, color: 'var(--muted)' }}>
              {loading ? 'Buscando...' : `${results.length} usuário(s) encontrado(s)`}
            </div>

            {results.map(user => (
              <div 
                key={user.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '12px',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  background: 'var(--panel)',
                  textDecoration: 'none'
                }}
              >
                <Link 
                  to={`/profile/${user.id}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    flex: 1,
                    textDecoration: 'none'
                  }}
                >
                  <Avatar src={user.avatar_url} size={40} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, color: 'var(--text)' }}>
                      @{user.username}
                    </div>
                    {user.bio && (
                      <div style={{ 
                        fontSize: 13, 
                        color: 'var(--muted)',
                        marginTop: 2
                      }}>
                        {user.bio.length > 50 ? `${user.bio.substring(0, 50)}...` : user.bio}
                      </div>
                    )}
                    {user.is_private && (
                      <div style={{ 
                        fontSize: 12, 
                        color: 'var(--muted)',
                        marginTop: 2
                      }}>
                        🔒 Perfil privado
                      </div>
                    )}
                  </div>
                </Link>
              </div>
            ))}

            {!loading && results.length === 0 && query.length >= 2 && (
              <div style={{ 
                textAlign: 'center', 
                color: 'var(--muted)', 
                padding: '40px 20px',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                background: 'var(--panel)'
              }}>
                Nenhum usuário encontrado para "{query}"
              </div>
            )}

            {hasMore && (
              <div style={{ textAlign: 'center' }}>
                <Button 
                  variant="ghost" 
                  onClick={handleLoadMore}
                  disabled={loading}
                >
                  {loading ? 'Carregando...' : 'Carregar mais'}
                </Button>
              </div>
            )}
          </div>
        )}

        {query.length > 0 && query.length < 2 && (
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>
            Digite pelo menos 2 caracteres para buscar
          </div>
        )}
      </div>
    </AppShell>
  )
}
