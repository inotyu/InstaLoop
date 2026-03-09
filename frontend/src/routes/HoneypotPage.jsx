import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

export default function HoneypotPage() {
  const location = useLocation()

  useEffect(() => {
    
    fetch('/api/telemetry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: 'honeypot_route_accessed',
        route: location.pathname,
        ts: Date.now(),
        referrer: document.referrer
      }),
      keepalive: true
    }).catch(() => {})
  }, [location.pathname])

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <p>Carregando...</p>
    </div>
  )
}
