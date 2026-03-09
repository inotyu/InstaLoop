import './avatar.css'

export default function Avatar({ src, alt = '', size = 40, ring = false }) {
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'
  
  // Garantir que a URL da imagem aponte para o backend se for um caminho relativo
  const getImageUrl = (path) => {
    if (!path) return null
    if (path.startsWith('http')) return path
    // Remove barra inicial duplicada se existir
    const cleanPath = path.startsWith('/') ? path : `/${path}`
    return `${API_BASE_URL}${cleanPath}`
  }

  const imageUrl = getImageUrl(src)
  const style = { width: size, height: size }
  
  return (
    <div className={ring ? 'avatar avatar-ring' : 'avatar'} style={style}>
      {imageUrl ? (
        <img 
          src={imageUrl} 
          alt={alt} 
          onError={(e) => {
            e.target.onerror = null
            e.target.src = '' // Fallback em caso de erro de carregamento
            e.target.parentElement.classList.add('avatar-error')
          }}
        />
      ) : (
        <div className="avatar-fallback" />
      )}
    </div>
  )
}
