import type {
  ContextProfile,
  ContextProfileCreate,
  ChatSession,
  ChatMessage,
  ChatRequest,
  ChatResponse,
  MCPServer,
  MCPServerCreate,
} from '../types';

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error ${res.status}: ${error}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const contextApi = {
  list: () => request<ContextProfile[]>('/context'),

  get: (id: string) => request<ContextProfile>(`/context/${id}`),

  create: (data: ContextProfileCreate) =>
    request<ContextProfile>('/context', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<ContextProfileCreate>) =>
    request<ContextProfile>(`/context/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/context/${id}`, { method: 'DELETE' }),

  getLinkedServers: (id: string) =>
    request<MCPServer[]>(`/context/${id}/mcp-servers`),

  linkServer: (contextId: string, serverId: string) =>
    request<void>(`/context/${contextId}/mcp-servers/${serverId}`, { method: 'POST' }),

  unlinkServer: (contextId: string, serverId: string) =>
    request<void>(`/context/${contextId}/mcp-servers/${serverId}`, { method: 'DELETE' }),
};

export const mcpApi = {
  list: () => request<MCPServer[]>('/mcp/servers'),

  get: (id: string) => request<MCPServer>(`/mcp/servers/${id}`),

  create: (data: MCPServerCreate) =>
    request<MCPServer>('/mcp/servers', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<MCPServerCreate>) =>
    request<MCPServer>(`/mcp/servers/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/mcp/servers/${id}`, { method: 'DELETE' }),

  start: (id: string) =>
    request<{ name: string; tools: string[]; running: boolean }>(`/mcp/servers/${id}/start`, { method: 'POST' }),

  stop: (id: string) =>
    request<void>(`/mcp/servers/${id}/stop`, { method: 'POST' }),
};

export const chatApi = {
  send: (data: ChatRequest) =>
    request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  streamChat: (
    data: ChatRequest,
    onChunk: (text: string) => void,
    onSessionId: (id: string) => void,
    onDone: () => void,
  ) => {
    const controller = new AbortController();

    fetch(`${BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: controller.signal,
    }).then(async (res) => {
      const reader = res.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = JSON.parse(line.slice(6));
          if (payload.type === 'session_id') onSessionId(payload.session_id);
          else if (payload.type === 'content') onChunk(payload.content);
          else if (payload.type === 'done') onDone();
        }
      }
    });

    return controller;
  },

  getSessions: (contextId?: string) => {
    const params = contextId ? `?context_id=${contextId}` : '';
    return request<ChatSession[]>(`/chat/sessions${params}`);
  },

  getSessionMessages: (sessionId: string) =>
    request<ChatMessage[]>(`/chat/sessions/${sessionId}`),

  deleteSession: (sessionId: string) =>
    request<void>(`/chat/sessions/${sessionId}`, { method: 'DELETE' }),
};
