import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    // ZERO source maps - completamente blindado
    sourcemap: false,
    
    // Minificação agressiva com Terser
    minify: 'terser',
    terserOptions: {
      compress: {
        // Remover todos os console.* (apenas em produção)
        // drop_console: true,
        // drop_debugger: true,
        
        // Múltiplas passagens de otimização
        passes: 3,
        
        // Remover funções específicas (apenas em produção)
        // pure_funcs: [
        //   'console.log', 'console.warn', 'console.error',
        //   'console.info', 'console.debug', 'console.trace',
        //   'console.table', 'console.group', 'console.groupEnd'
        // ],
        
        // Otimizações adicionais
        dead_code: true,
        unused: true,
        hoist_funs: true,
        hoist_vars: true,
        if_return: true,
        join_vars: true,
        collapse_vars: true,
        reduce_vars: true,
        sequences: true,
        
        // Proteção contra engenharia reversa
        evaluate: true,
        booleans: true,
        loops: true,
        properties: true,
        keep_fnames: false
      },
      mangle: {
        // Ofuscação de nomes de variáveis
        toplevel: true,
        eval: true,
        
        // Reserved names to prevent breaking React internals
        reserved: [
          'ReactCurrentOwner',
          '__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED__',
          'ReactCurrentDispatcher',
          'ReactCurrentBatchConfig'
        ],
        
        // Ofuscar propriedades com underscore
        properties: {
          regex: /^_/,
          reserved: []
        },
        
        // Configurações de ofuscação
        keep_fnames: false
      },
      format: {
        // Zero comentários no bundle
        comments: false
      }
    },
    
    // Rollup options para chunks com hash
    rollupOptions: {
      output: {
        // Nomes de chunks com hash - impossível deduzir conteúdo
        chunkFileNames: 'assets/[hash].js',
        entryFileNames: 'assets/[hash].js',
        assetFileNames: 'assets/[hash].[ext]',
        
        // Divisão de código manual
        manualChunks: {
          // Vendor em chunk separado
          vendor: ['react', 'react-dom', 'react-router-dom'],
          
          // Bibliotecas de UI em chunk separado
          ui: ['lucide-react'],
          
          // Utilitários em chunk separado
          utils: []
        },
        
        // Otimizações adicionais
        compact: true
      },
      
      // Plugins adicionais de segurança
      plugins: []
    },
    
    // Configurações de output
    outDir: 'dist',
    assetsDir: 'assets',
    
    // Target moderno para melhor otimização
    target: 'es2020',
    
    // Chunk size warning limit alto (para evitar warnings em produção)
    chunkSizeWarningLimit: 1000,
    
    // CSS inline em JS (menos requests)
    cssCodeSplit: false
  },
  
  // Configurações de servidor de desenvolvimento
  server: {
    host: '0.0.0.0',
    port: 5173,
    
    // Proxy para API backend
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      }
    },
    
    // Headers de segurança em desenvolvimento
    headers: {
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block'
    }
  },
  
  // Configurações de preview
  preview: {
    host: '0.0.0.0',
    port: 4173,
    
    // Headers de segurança em preview
    headers: {
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block'
    }
  },
  
  // Configurações de dependências
  optimizeDeps: {
    // Pre-bundle de dependências para performance
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'axios'
    ],
    
    // Excluir dependências problemáticas
    exclude: []
  },
  
  // Configurações de CSS
  css: {
    // Módulos CSS com hash
    modules: {
      generateScopedName: '[hash][local]'
    },
    
    // PostCSS config
    postcss: {
      plugins: []
    },
    
    // Preprocessadores
    preprocessorOptions: {}
  },
  
  // Configurações de ambiente
  define: {
    // Remover informações de ambiente sensíveis
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString())
  },
  
  // Configurações de resolve
  resolve: {
    // Alias para paths limpos
    alias: {
      '@': '/src'
    },
    
    // Extensions para imports limpos
    extensions: ['.js', '.jsx', '.ts', '.tsx', '.json'],
    
    // Dedupe para evitar duplicação de React
    dedupe: ['react', 'react-dom']
  },
  
  // Configurações de ESBuild
  esbuild: {
    // Minificação em desenvolvimento também
    minify: true,
    
    // Remover console apenas em produção
    // drop: ['console', 'debugger'],
    
    // Target moderno
    target: 'es2020'
  },
  
  // Configurações experimentais
  experimental: {
    // Renderizar SSR
    renderBuiltUrl: (filename, { hostType }) => {
      if (hostType === 'js') {
        return { js: `/${filename}` }
      } else {
        return { relative: true }
      }
    }
  }
})
