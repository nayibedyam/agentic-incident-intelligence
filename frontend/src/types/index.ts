export interface ContextProfile {
  id: string;
  name: string;
  description: string | null;
  system_prompt: string;
  knowledge_sources: KnowledgeSource[] | null;
  severity_rules: Record<string, string[]> | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSource {
  type: string;
  path: string;
}

export interface MCPServer {
  id: string;
  name: string;
  description: string | null;
  command: string;
  args: string[];
  env: Record<string, string>;
  running: boolean;
  created_at: string;
  updated_at: string;
}

export interface MCPServerCreate {
  name: string;
  description?: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
}

export interface ChatSession {
  id: string;
  context_profile_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  context_id: string;
  attachments?: Attachment[];
}

export interface Attachment {
  type: string;
  content: string;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  metadata: Record<string, unknown> | null;
}

export interface ContextProfileCreate {
  name: string;
  description?: string;
  system_prompt: string;
  knowledge_sources?: KnowledgeSource[];
  severity_rules?: Record<string, string[]>;
}
