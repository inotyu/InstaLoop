import { useState, useRef } from 'react'
import { Image, X, Loader2 } from 'lucide-react'
import Button from '../ui/Button.jsx'
import TextField from '../ui/TextField.jsx'
import postService from '../../services/postService.js'
import './createpost.css'

export default function CreatePost({ onPostCreated }) {
  const [content, setContent] = useState('')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)

  function handleFileChange(e) {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      const reader = new FileReader()
      reader.onloadend = () => setPreview(reader.result)
      reader.readAsDataURL(selectedFile)
    }
  }

  function removeMedia() {
    setFile(null)
    setPreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!content && !file) return

    setLoading(true)
    setError('')
    try {
      await postService.createPost(content, file)
      setContent('')
      removeMedia()
      if (onPostCreated) onPostCreated()
    } catch (err) {
      setError(err.message || 'Erro ao criar publicação')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="create-post">
      <form onSubmit={handleSubmit}>
        <div className="create-post-input">
          <textarea
            placeholder="No que você está pensando?"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={loading}
          />
        </div>

        {preview && (
          <div className="create-post-preview">
            <img src={preview} alt="Preview" />
            <button type="button" className="remove-preview" onClick={removeMedia}>
              <X size={18} />
            </button>
          </div>
        )}

        {error && <div className="create-post-error">{error}</div>}

        <div className="create-post-actions">
          <button
            type="button"
            className="add-media-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
          >
            <Image size={20} />
            <span>Foto</span>
          </button>
          <input
            type="file"
            className="visuallyHidden"
            accept="image/*"
            ref={fileInputRef}
            onChange={handleFileChange}
          />
          
          <Button 
            type="submit" 
            size="sm" 
            disabled={loading || (!content && !file)}
          >
            {loading ? <Loader2 className="animate-spin" size={18} /> : 'Publicar'}
          </Button>
        </div>
      </form>
    </div>
  )
}
