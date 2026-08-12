import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// Apply dark mode class before first render to avoid flash
const stored = localStorage.getItem('hs-dark')
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
if (stored === 'true' || (stored === null && prefersDark)) {
  document.documentElement.classList.add('dark')
}

// Registering is inert on its own — no prompts, no subscription — it just makes the worker
// available for the explicit, user-initiated "enable push" flow (docs/32_Core_Notifications_and_Push.md §10).
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {})
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
