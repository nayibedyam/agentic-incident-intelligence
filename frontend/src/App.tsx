import { Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import ChatPage from './pages/ChatPage';
import ContextSetupPage from './pages/ContextSetupPage';
import ContextManagePage from './pages/ContextManagePage';
import MCPServersPage from './pages/MCPServersPage';
import { contextApi } from './services/api';
import type { ContextProfile } from './types';

export default function App() {
  const [contexts, setContexts] = useState<ContextProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    contextApi.list().then((data) => {
      setContexts(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const refreshContexts = () => {
    contextApi.list().then(setContexts);
  };

  if (loading) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--text-secondary)' }}>Loading...</div>;
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          contexts.length === 0
            ? <Navigate to="/contexts/new" replace />
            : <Navigate to="/chat" replace />
        }
      />
      <Route path="/contexts/new" element={<ContextSetupPage onCreated={refreshContexts} />} />
      <Route path="/contexts/:id/edit" element={<ContextSetupPage onCreated={refreshContexts} />} />
      <Route path="/contexts" element={<ContextManagePage contexts={contexts} onRefresh={refreshContexts} />} />
      <Route path="/mcp-servers" element={<MCPServersPage />} />
      <Route path="/chat" element={<ChatPage contexts={contexts} />} />
      <Route path="/chat/:sessionId" element={<ChatPage contexts={contexts} />} />
    </Routes>
  );
}
