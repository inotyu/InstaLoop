import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AppShell from '../components/layout/AppShell.jsx'
import SuggestionsPanel from '../components/suggestions/SuggestionsPanel.jsx'
import TextField from '../components/ui/TextField.jsx'
import Button from '../components/ui/Button.jsx'
import Avatar from '../components/ui/Avatar.jsx'
import authService from '../services/authService.js'
import userService from '../services/userService.js'

export default function EditProfile() {
  const navigate = useNavigate()
  const [user, setUser] = useState(authService.getUser())
  const [bio, setBio] = useState(user?.bio || '')
  const [isPrivate, setIsPrivate] = useState(user?.is_private || false)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [details, setDetails] = useState([])

  useEffect(() => {
    const currentUser = authService.getUser()
    if (currentUser) {
      setUser(currentUser)
      setBio(currentUser.bio || '')
      setIsPrivate(currentUser.is_private || false)
    }
  }, [])

  async function handleAvatarChange(e) {
    const file = e.target.files[0]
    if (!file) return

    setUploading(true)
    setError('')
    setSuccess('')
    try {
      await userService.uploadAvatar(file)
      setUser({ ...authService.getUser() })
      setSuccess('Foto de perfil atualizada!')
    } catch (err) {
      setError(err.message || 'Erro no upload')
      setDetails(err.details || [])
    } finally {
      setUploading(false)
    }
  }

  async function onSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    setDetails([])

    try {
      await userService.updateProfile({
        bio,
        is_private: isPrivate
      })
      setSuccess('Perfil atualizado com sucesso!')
      setTimeout(() => navigate('/me'), 1500)
    } catch (err) {
      setError(err.message || 'Erro ao atualizar perfil')
      setDetails(err.details || [])
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppShell right={<SuggestionsPanel />}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h2 style={{ fontWeight: 900, fontSize: 20 }}>Editar Perfil</h2>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Avatar size={64} src={user?.avatar_url} ring />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ fontWeight: 700 }}>@{user?.username}</div>
            <label style={{ color: 'var(--brand)', cursor: 'pointer', fontSize: 14, fontWeight: 600 }}>
              Alterar foto de perfil
              <input 
                type="file" 
                className="visuallyHidden" 
                accept="image/*" 
                onChange={handleAvatarChange}
                disabled={uploading}
              />
            </label>
            {uploading && <div style={{ fontSize: 12, color: 'var(--muted)' }}>Enviando...</div>}
          </div>
        </div>

        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <TextField 
            label="Bio" 
            placeholder="Conte um pouco sobre você..." 
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            multiline
            rows={3}
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <input 
              type="checkbox" 
              id="isPrivate" 
              checked={isPrivate}
              onChange={(e) => setIsPrivate(e.target.checked)}
              style={{ width: 18, height: 18 }}
            />
            <label htmlFor="isPrivate" style={{ fontSize: 14, fontWeight: 600 }}>Conta privada</label>
          </div>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: -14 }}>
            Quando sua conta é privada, apenas as pessoas que você aprova podem ver suas fotos e vídeos.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Button disabled={loading || uploading} type="submit">
              {loading ? 'Salvando...' : 'Enviar'}
            </Button>
            
            {error && (
              <div style={{ color: 'var(--danger)', fontSize: 13 }}>
                <strong>{error}</strong>
                {details.length > 0 && (
                  <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>
                    {details.map((d, i) => <li key={i}>{d}</li>)}
                  </ul>
                )}
              </div>
            )}
            
            {success && <div style={{ color: 'var(--ok)', fontSize: 13, fontWeight: 600 }}>{success}</div>}
          </div>
        </form>
      </div>
    </AppShell>
  )
}
