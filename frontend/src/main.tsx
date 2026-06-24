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

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
