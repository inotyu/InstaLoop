import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

import './styles/global.css'

// Bloquear console em produção (antes de qualquer coisa)
if (import.meta.env.PROD) {
  const noop = () => {}
  Object.keys(console).forEach((key) => {
    try {
      console[key] = noop
    } catch (e) {}
  })
  try {
    Object.freeze(console)
  } catch (e) {}
}

// DevTools detector (produção)
import './utils/devtools-detector.js'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
