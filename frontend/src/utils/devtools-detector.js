// Detector de DevTools - CAMADA 10: DevTools Invisibility

class DevToolsDetector {
  constructor() {
    this.isOpen = false
    this.wasOpened = false
    this.checkInterval = null
    this.warningCount = 0
    this.maxWarnings = 3
    
    // Iniciar detecção
    this.startDetection()
    
    // Detectar tentativas de desativar
    this.preventDisabling()
  }

  startDetection() {
    // Múltiplos métodos de detecção
    
    // 1. Método baseado em dimensões da janela
    this.checkInterval = setInterval(() => {
      this.checkByDimensions()
    }, 1000)
    
    // 2. Método baseado em console
    this.checkByConsole()
    
    // 3. Método baseado em performance
    this.checkByPerformance()
    
    // 4. Método baseado em debugger
    this.checkByDebugger()
    
    // 5. Event listeners
    this.setupEventListeners()
  }

  checkByDimensions() {
    const threshold = 200
    const isOpen = 
      window.outerHeight - window.innerHeight > threshold ||
      window.outerWidth - window.innerWidth > threshold

    if (isOpen && !this.isOpen) {
      this.onDevToolsOpened('dimensions')
    } else if (!isOpen && this.isOpen) {
      this.onDevToolsClosed('dimensions')
    }
  }

  checkByConsole() {
    // Detectar se console foi modificado
    const originalConsole = window.console
    const suspiciousMethods = ['log', 'warn', 'error', 'info', 'debug']
    
    suspiciousMethods.forEach(method => {
      if (window.console[method].toString().length < 50) {
        this.onDevToolsOpened('console_modified')
      }
    })
  }

  checkByPerformance() {
    // Detectar se performance timing é suspeito
    if (window.performance && window.performance.timing) {
      const timing = window.performance.timing
      const loadTime = timing.loadEventEnd - timing.navigationStart
      
      // Tempos muito rápidos podem indicar DevTools
      if (loadTime > 0 && loadTime < 100) {
        this.onDevToolsOpened('performance')
      }
    }
  }

  checkByDebugger() {
    // Detectar breakpoint
    const start = performance.now()
    debugger
    const end = performance.now()
    
    if (end - start > 100) {
      this.onDevToolsOpened('debugger')
    }
  }

  setupEventListeners() {
    // Detectar mudanças de foco
    let originalFocus = document.hasFocus()
    
    setInterval(() => {
      const currentFocus = document.hasFocus()
      if (!currentFocus && originalFocus) {
        // Possível DevTools aberto
        this.onDevToolsOpened('focus')
      }
      originalFocus = currentFocus
    }, 1000)
    
    // Detectar teclas de atalho do DevTools
    document.addEventListener('keydown', (e) => {
      const isDevToolsShortcut = 
        (e.key === 'F12') ||
        (e.ctrlKey && e.shiftKey && e.key === 'I') ||
        (e.ctrlKey && e.shiftKey && e.key === 'J') ||
        (e.ctrlKey && e.shiftKey && e.key === 'C') ||
        (e.metaKey && e.altKey && e.key === 'I')
      
      if (isDevToolsShortcut) {
        e.preventDefault()
        this.onDevToolsOpened('shortcut')
      }
    })
    
    // Detectar右 clique
    document.addEventListener('contextmenu', (e) => {
      // Verificar se inspecionar elemento foi selecionado
      setTimeout(() => {
        if (document.activeElement && document.activeElement.tagName === 'INS') {
          this.onDevToolsOpened('inspect')
        }
      }, 100)
    })
  }

  onDevToolsOpened(method) {
    if (!this.isOpen) {
      this.isOpen = true
      this.wasOpened = true
      
      // Reportar ao backend
      this.reportToBackend(method)
      
      // Ações progressivas
      this.handleDevToolsOpened(method)
    }
  }

  onDevToolsClosed(method) {
    this.isOpen = false
    this.reportToBackend(`closed_${method}`)
  }

  reportToBackend(method) {
    const data = {
      event: 'devtools_detected',
      method: method,
      timestamp: Date.now(),
      url: window.location.pathname,
      userAgent: navigator.userAgent,
      screen: {
        width: screen.width,
        height: screen.height
      },
      window: {
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
        outerWidth: window.outerWidth,
        outerHeight: window.outerHeight
      },
      wasPreviouslyOpened: this.wasOpened
    }

    // Enviar para backend
    fetch('/api/telemetry', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data),
      keepalive: true
    }).catch(() => {
      // Silenciar erros para não alertar o usuário
    })
  }

  handleDevToolsOpened(method) {
    this.warningCount++
    
    if (this.warningCount >= this.maxWarnings) {
      // Ação drástica após múltiplas detecções
      this.takeDrasticAction()
    } else {
      // Ações progressivas
      switch (this.warningCount) {
        case 1:
          this.showWarning()
          break
        case 2:
          this.obfuscateContent()
          break
        default:
          this.degradeExperience()
      }
    }
  }

  showWarning() {
    // Mostrar aviso sutil
    const warning = document.createElement('div')
    warning.innerHTML = '⚠️ Para sua segurança, feche as ferramentas de desenvolvedor'
    warning.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #ff6b6b;
      color: white;
      padding: 10px 15px;
      border-radius: 5px;
      z-index: 10000;
      font-size: 14px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    `
    
    document.body.appendChild(warning)
    
    setTimeout(() => {
      if (warning.parentNode) {
        warning.parentNode.removeChild(warning)
      }
    }, 5000)
  }

  obfuscateContent() {
    // Ofuscar conteúdo da página
    document.body.style.filter = 'blur(5px)'
    document.body.style.pointerEvents = 'none'
    
    setTimeout(() => {
      if (this.isOpen) {
        document.body.style.filter = 'blur(10px)'
      } else {
        document.body.style.filter = ''
        document.body.style.pointerEvents = ''
      }
    }, 3000)
  }

  degradeExperience() {
    // Degradação da experiência
    const style = document.createElement('style')
    style.textContent = `
      * { 
        animation-duration: 0.1s !important;
        transition-duration: 0.1s !important;
      }
      img { opacity: 0.5 !important; }
      button { 
        background: #ccc !important;
        cursor: not-allowed !important;
      }
    `
    document.head.appendChild(style)
    
    setTimeout(() => {
      if (style.parentNode) {
        style.parentNode.removeChild(style)
      }
    }, 10000)
  }

  takeDrasticAction() {
    // Ação drástica: logout ou redirecionamento
    if (window.authService && window.authService.isAuthenticated()) {
      window.authService.logout()
      window.location.href = '/login?reason=security'
    } else {
      window.location.href = '/security-warning'
    }
  }

  preventDisabling() {
    // Impedir que o detector seja desativado
    const originalClearInterval = window.clearInterval
    window.clearInterval = function(id) {
      if (id === devToolsDetector.checkInterval) {
        devToolsDetector.reportToBackend('disable_attempt')
        return // Não permitir limpar o intervalo
      }
      return originalClearInterval.call(this, id)
    }
    
    // Proteger contra sobrescrita
    Object.defineProperty(window, 'devToolsDetector', {
      value: this,
      writable: false,
      configurable: false
    })
  }

  stop() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
    }
  }
}

// Inicializar detector apenas em produção
if (import.meta.env.PROD) {
  // Bloquear console em produção
  const noop = () => {}
  const consoleMethods = ['log', 'warn', 'error', 'info', 'debug', 'trace', 'table', 'group', 'groupEnd']
  
  consoleMethods.forEach(method => {
    console[method] = noop
  })
  
  // Congelar console
  Object.freeze(console)
  
  // Iniciar detector
  const devToolsDetector = new DevToolsDetector()
  
  // Disponibilizar globalmente para proteção
  window.devToolsDetector = devToolsDetector
  
  // Detectar tentativas de acessar variáveis internas
  let inspectionCount = 0
  const maxInspections = 5
  
  const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'devToolsDetector')
  Object.defineProperty(window, 'devToolsDetector', {
    get: function() {
      inspectionCount++
      
      if (inspectionCount > maxInspections) {
        devToolsDetector.takeDrasticAction()
      }
      
      devToolsDetector.reportToBackend('variable_inspection')
      return originalDescriptor.value
    },
    configurable: false,
    enumerable: false
  })
  
  // Detectar acessos a propriedades sensíveis
  const sensitiveProps = ['accessToken', 'token', 'auth', 'user']
  sensitiveProps.forEach(prop => {
    let propAccessCount = 0
    
    Object.defineProperty(window, prop, {
      get: function() {
        propAccessCount++
        devToolsDetector.reportToBackend(`sensitive_property_access_${prop}`)
        
        if (propAccessCount > 3) {
          devToolsDetector.takeDrasticAction()
        }
        
        return undefined
      },
      configurable: false,
      enumerable: false
    })
  })
  
  // Proteger contra eval
  const originalEval = window.eval
  window.eval = function(code) {
    devToolsDetector.reportToBackend('eval_attempt')
    
    if (code.includes('devToolsDetector') || code.includes('console')) {
      return undefined
    }
    
    return originalEval.call(this, code)
  }
  
  // Detectar mudanças no DOM
  const observer = new MutationObserver((mutations) => {
    mutations.forEach(mutation => {
      if (mutation.type === 'attributes' && 
          (mutation.attributeName === 'style' || mutation.attributeName === 'class')) {
        
        // Detectar tentativas de remover estilos de proteção
        const element = mutation.target
        if (element.style && element.style.filter === 'none' && devToolsDetector.warningCount > 0) {
          devToolsDetector.reportToBackend('style_manipulation')
          element.style.filter = 'blur(5px)'
        }
      }
    })
  })
  
  observer.observe(document.body, {
    attributes: true,
    subtree: true,
    attributeFilter: ['style', 'class']
  })
  
  // Cleanup ao sair da página
  window.addEventListener('beforeunload', () => {
    devToolsDetector.stop()
  })
}

export default DevToolsDetector
