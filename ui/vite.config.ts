import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      // Enable React Fast Refresh
      fastRefresh: true,
      // Optimize JSX runtime
      jsxRuntime: 'automatic',
      // Enable babel plugins for better performance
      babel: {
        plugins: [
          // Optimize React components
          ['@babel/plugin-transform-react-jsx', { runtime: 'automatic' }],
          // Remove console.log in production
          process.env.NODE_ENV === 'production' && [
            'transform-remove-console',
            { exclude: ['error', 'warn'] }
          ]
        ].filter(Boolean)
      }
    })
  ],
  
  // Path resolution
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@hooks': resolve(__dirname, 'src/hooks'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@types': resolve(__dirname, 'src/types'),
      '@assets': resolve(__dirname, 'src/assets')
    }
  },

  // Development server configuration
  server: {
    port: 5173,
    host: true,
    open: true,
    cors: true,
    // Enable HMR for better development experience
    hmr: {
      overlay: true
    }
  },

  // Preview server configuration
  preview: {
    port: 4173,
    host: true,
    open: true
  },

  // Build configuration
  build: {
    // Output directory
    outDir: 'dist',
    
    // Source map configuration
    sourcemap: process.env.NODE_ENV === 'development',
    
    // Minification
    minify: 'terser',
    terserOptions: {
      compress: {
        // Remove console.log in production
        drop_console: true,
        drop_debugger: true,
        // Remove unused code
        unused: true,
        // Optimize for size
        passes: 2
      },
      mangle: {
        // Mangle class names for smaller bundles
        keep_classnames: false,
        keep_fnames: false
      }
    },

    // Chunk size optimization
    chunkSizeWarningLimit: 1000,
    
    // Rollup options
    rollupOptions: {
      output: {
        // Manual chunks for better caching
        manualChunks: {
          // Vendor chunks
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'chart-vendor': ['chart.js', 'react-chartjs-2'],
          'ui-vendor': ['lucide-react', 'framer-motion'],
          'utils-vendor': ['axios', 'date-fns', 'clsx', 'tailwind-merge']
        },
        // Optimize chunk names
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId
            ? chunkInfo.facadeModuleId.split('/').pop().replace('.tsx', '').replace('.ts', '')
            : 'chunk';
          return `js/${facadeModuleId}-[hash].js`;
        },
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.');
          const ext = info[info.length - 1];
          if (/\.(css)$/.test(assetInfo.name)) {
            return `css/[name]-[hash].${ext}`;
          }
          return `assets/[name]-[hash].${ext}`;
        }
      }
    },

    // Target modern browsers for better performance
    target: ['es2015', 'chrome58', 'firefox57', 'safari11', 'edge16'],

    // CSS code splitting
    cssCodeSplit: true,

    // Asset handling
    assetsInlineLimit: 4096
  },

  // CSS configuration
  css: {
    // Enable CSS modules
    modules: {
      localsConvention: 'camelCase'
    },
    // PostCSS configuration
    postcss: {
      plugins: [
        require('tailwindcss'),
        require('autoprefixer')
      ]
    }
  },

  // Environment variables
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString())
  },

  // Optimize dependencies
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'chart.js',
      'react-chartjs-2',
      'lucide-react',
      'axios',
      'date-fns',
      'clsx',
      'tailwind-merge',
      'zustand',
      'framer-motion'
    ],
    exclude: ['@vite/client', '@vite/env']
  },

  // Performance optimizations
  esbuild: {
    // Enable tree shaking
    treeShaking: true,
    // Optimize for production
    minifyIdentifiers: process.env.NODE_ENV === 'production',
    minifySyntax: process.env.NODE_ENV === 'production',
    minifyWhitespace: process.env.NODE_ENV === 'production'
  },

  // Experimental features
  experimental: {
    // Enable renderBuiltUrl for better asset handling
    renderBuiltUrl(filename, { hostType }) {
      if (hostType === 'js') {
        return { js: `/${filename}` };
      } else {
        return { relative: true };
      }
    }
  }
});
