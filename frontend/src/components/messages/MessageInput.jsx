import { useState, useRef } from 'react'
import { messageService } from '../../services/messageService.js'

export default function MessageInput({ onSendMessage }) {
  const [content, setContent] = useState('')
  const [mediaUrl, setMediaUrl] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [sending, setSending] = useState(false)
  const fileInputRef = useRef(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!content.trim() && !mediaUrl) return
    
    try {
      setSending(true)
      await onSendMessage(content.trim(), mediaUrl)
      setContent('')
      setMediaUrl(null)
    } catch (err) {
    } finally {
      setSending(false)
    }
  }

  const handleFileSelect = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    // Validar tipo de arquivo
    if (!file.type.startsWith('image/')) {
      alert('Apenas imagens são permitidas')
      return
    }

    // Validar tamanho (5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Arquivo muito grande. Máximo 5MB.')
      return
    }

    try {
      setUploading(true)
      const result = await messageService.uploadMedia(file)
      setMediaUrl(result.media_url)
    } catch (err) {
      alert('Erro ao fazer upload da mídia')
    } finally {
      setUploading(false)
    }
  }

  const removeMedia = () => {
    setMediaUrl(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div style={{ borderTop: '1px solid var(--border)', padding: 16 }}>
      {/* Preview da mídia */}
      {mediaUrl && (
        <div style={{ marginBottom: 12, position: 'relative', display: 'inline-block' }}>
          <img
            src={mediaUrl.startsWith('http') ? mediaUrl : `http://localhost:5000${mediaUrl}`}
            alt="Preview"
            style={{
              maxWidth: 200,
              maxHeight: 150,
              borderRadius: 8,
              objectFit: 'cover'
            }}
          />
          <button
            onClick={removeMedia}
            style={{
              position: 'absolute',
              top: 4,
              right: 4,
              background: 'rgba(0,0,0,0.7)',
              color: 'white',
              border: 'none',
              borderRadius: '50%',
              width: 24,
              height: 24,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 14
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Digite sua mensagem..."
            style={{
              width: '100%',
              minHeight: 40,
              maxHeight: 120,
              padding: 12,
              border: '1px solid var(--border)',
              borderRadius: 20,
              resize: 'none',
              fontFamily: 'inherit',
              fontSize: 14,
              outline: 'none'
            }}
            disabled={sending}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
          />
        </div>

        {/* Botão de mídia */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          disabled={uploading || sending}
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          style={{
            padding: 10,
            border: '1px solid var(--border)',
            borderRadius: '50%',
            background: 'var(--background)',
            cursor: uploading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          disabled={uploading || sending}
          title="Anexar imagem"
        >
          {uploading ? '⏳' : '📎'}
        </button>

        {/* Botão enviar */}
        <button
          type="submit"
          disabled={(!content.trim() && !mediaUrl) || sending}
          style={{
            padding: '10px 16px',
            background: 'var(--primary)',
            color: 'white',
            border: 'none',
            borderRadius: 20,
            cursor: sending ? 'not-allowed' : 'pointer',
            fontWeight: 500,
            minWidth: 60
          }}
        >
          {sending ? '...' : 'Enviar'}
        </button>
      </form>
    </div>
  )
}
