import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { App } from './App';
import { AuthProvider } from './context/AuthContext';
import { DocumentoProvider } from './context/DocumentoContext';
import './styles/index.css';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Elemento #root não encontrado em index.html');
}

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <DocumentoProvider>
          <App />
        </DocumentoProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
