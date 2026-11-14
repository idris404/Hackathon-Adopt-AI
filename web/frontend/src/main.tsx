import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import { Providers } from './app/providers'
import { ROOT_ELEMENT_ID, ROOT_ELEMENT_MISSING_ERROR } from './constants/app'
import './index.css'

const rootElement = document.getElementById(ROOT_ELEMENT_ID)
if (!rootElement) {
  throw new Error(ROOT_ELEMENT_MISSING_ERROR)
}

createRoot(rootElement).render(
  <StrictMode>
    <Providers>
      <App />
    </Providers>
  </StrictMode>,
)
