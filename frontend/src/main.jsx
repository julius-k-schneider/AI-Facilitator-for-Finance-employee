import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MantineProvider } from '@mantine/core'
import '@mantine/core/styles.css'
import './index.css'
import { theme, applyBrandingVars } from './theme'
import './i18n'
import App from './App.jsx'

// Branding-Farben als CSS-Variablen verfügbar machen (zentral über branding.js steuerbar).
applyBrandingVars()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="light">
      <App />
    </MantineProvider>
  </StrictMode>,
)
