import type { ChatSession } from '../types';

interface Props {
  sessions: ChatSession[];
  activeSessionId?: string;
  onSelect: (session: ChatSession) => void;
  onNew: () => void;
  onManageContexts: () => void;
}

export default function SessionSidebar({ sessions, activeSessionId, onSelect, onNew, onManageContexts }: Props) {
  return (
    <div style={styles.sidebar}>
      <div style={styles.header}>
        <span style={styles.title}>Sessions</span>
      </div>

      <div style={styles.sessions}>
        {sessions.map((session) => (
          <button
            key={session.id}
            style={session.id === activeSessionId ? styles.activeItem : styles.item}
            onClick={() => onSelect(session)}
          >
            {session.title || 'Untitled'}
          </button>
        ))}
      </div>

      <div style={styles.footer}>
        <button style={styles.footerBtn} onClick={onNew}>+ New Chat</button>
        <button style={styles.footerBtn} onClick={onManageContexts}>Manage Contexts</button>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    width: '240px',
    background: 'var(--bg-secondary)',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    padding: '1rem',
    borderBottom: '1px solid var(--border)',
  },
  title: {
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  sessions: {
    flex: 1,
    overflow: 'auto',
    padding: '0.5rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  item: {
    padding: '0.625rem 0.75rem',
    borderRadius: '6px',
    background: 'transparent',
    color: 'var(--text-primary)',
    fontSize: '0.8rem',
    textAlign: 'left',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  activeItem: {
    padding: '0.625rem 0.75rem',
    borderRadius: '6px',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    fontSize: '0.8rem',
    textAlign: 'left',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  footer: {
    padding: '0.75rem',
    borderTop: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  footerBtn: {
    padding: '0.5rem 0.75rem',
    borderRadius: '6px',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    fontSize: '0.8rem',
    textAlign: 'left',
    border: '1px solid var(--border)',
  },
};
