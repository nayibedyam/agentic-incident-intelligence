import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '../services/api';
import type { ContextProfile, ChatSession, ChatMessage } from '../types';
import ContextSwitcher from '../components/ContextSwitcher';
import SessionSidebar from '../components/SessionSidebar';

interface Props {
  contexts: ContextProfile[];
}

export default function ChatPage({ contexts }: Props) {
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const [activeContext, setActiveContext] = useState<ContextProfile>(contexts[0]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>(sessionId);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeContext) {
      chatApi.getSessions(activeContext.id).then(setSessions);
    }
  }, [activeContext]);

  useEffect(() => {
    if (sessionId) {
      setCurrentSessionId(sessionId);
      chatApi.getSessionMessages(sessionId).then(setMessages).catch(() => setMessages([]));
    }
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!input.trim() || streaming) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      session_id: currentSessionId || '',
      role: 'user',
      content: input,
      metadata: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setStreaming(true);
    setStreamingContent('');

    chatApi.streamChat(
      { message: userMessage.content, session_id: currentSessionId, context_id: activeContext.id },
      (chunk) => setStreamingContent((prev) => prev + chunk),
      (newSessionId) => {
        setCurrentSessionId(newSessionId);
        navigate(`/chat/${newSessionId}`, { replace: true });
        chatApi.getSessions(activeContext.id).then(setSessions);
      },
      () => {
        setStreaming(false);
        setStreamingContent((content) => {
          if (content) {
            const assistantMessage: ChatMessage = {
              id: crypto.randomUUID(),
              session_id: currentSessionId || '',
              role: 'assistant',
              content,
              metadata: null,
              created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, assistantMessage]);
          }
          return '';
        });
      },
    );
  };

  const handleContextSwitch = (ctx: ContextProfile) => {
    setActiveContext(ctx);
    setCurrentSessionId(undefined);
    setMessages([]);
    navigate('/chat');
  };

  const handleNewSession = () => {
    setCurrentSessionId(undefined);
    setMessages([]);
    navigate('/chat');
  };

  const handleSelectSession = (session: ChatSession) => {
    navigate(`/chat/${session.id}`);
  };

  return (
    <div style={styles.layout}>
      <SessionSidebar
        sessions={sessions}
        activeSessionId={currentSessionId}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onManageContexts={() => navigate('/contexts')}
      />

      <div style={styles.main}>
        <div style={styles.header}>
          <ContextSwitcher
            contexts={contexts}
            active={activeContext}
            onSwitch={handleContextSwitch}
          />
        </div>

        <div style={styles.messages}>
          {messages.length === 0 && !streaming && (
            <div style={styles.empty}>
              <p>Start a conversation about an incident in <strong>{activeContext.name}</strong></p>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} style={msg.role === 'user' ? styles.userMsg : styles.assistantMsg}>
              <div style={styles.msgRole}>{msg.role === 'user' ? 'You' : 'Agent'}</div>
              <div style={styles.msgContent}>
                {msg.role === 'assistant' ? (
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))}
          {streaming && streamingContent && (
            <div style={styles.assistantMsg}>
              <div style={styles.msgRole}>Agent</div>
              <div style={styles.msgContent}>
                <ReactMarkdown>{streamingContent}</ReactMarkdown>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={styles.inputArea}>
          <input
            style={styles.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Describe the incident or ask a question..."
            disabled={streaming}
          />
          <button style={styles.sendBtn} onClick={handleSend} disabled={streaming || !input.trim()}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  layout: {
    display: 'flex',
    height: '100vh',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    padding: '0.75rem 1.5rem',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-secondary)',
  },
  messages: {
    flex: 1,
    overflow: 'auto',
    padding: '1.5rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  empty: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: 'var(--text-secondary)',
  },
  userMsg: {
    alignSelf: 'flex-end',
    maxWidth: '70%',
    background: 'var(--accent)',
    borderRadius: '12px 12px 4px 12px',
    padding: '0.75rem 1rem',
  },
  assistantMsg: {
    alignSelf: 'flex-start',
    maxWidth: '80%',
    background: 'var(--bg-secondary)',
    borderRadius: '12px 12px 12px 4px',
    padding: '0.75rem 1rem',
    border: '1px solid var(--border)',
  },
  msgRole: {
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
    marginBottom: '0.25rem',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  msgContent: {
    fontSize: '0.9rem',
    lineHeight: 1.6,
  },
  inputArea: {
    display: 'flex',
    gap: '0.75rem',
    padding: '1rem 1.5rem',
    borderTop: '1px solid var(--border)',
    background: 'var(--bg-secondary)',
  },
  input: {
    flex: 1,
    padding: '0.75rem 1rem',
    borderRadius: '8px',
    border: '1px solid var(--border)',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    fontSize: '0.9rem',
  },
  sendBtn: {
    padding: '0.75rem 1.5rem',
    borderRadius: '8px',
    background: 'var(--accent)',
    color: 'white',
    fontWeight: 600,
    fontSize: '0.875rem',
  },
};
