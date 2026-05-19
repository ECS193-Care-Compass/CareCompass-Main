import './assets/main.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { ContrastProvider } from './contexts/ContrastContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ContrastProvider>
      <App />
    </ContrastProvider>
  </StrictMode>
)
