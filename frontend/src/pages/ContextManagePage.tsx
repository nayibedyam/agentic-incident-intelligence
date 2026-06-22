import { useNavigate } from 'react-router-dom';
import { contextApi } from '../services/api';
import type { ContextProfile } from '../types';

interface Props {
  contexts: ContextProfile[];
  onRefresh: () => void;
}

export default function ContextManagePage({ contexts, onRefresh }: Props) {
  const navigate = useNavigate();

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this context profile? Associated sessions will remain but lose their context.')) return;
    await contextApi.delete(id);
    onRefresh();
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>Context Profiles</h1>
        <div style={styles.actions}>
          <button style={styles.secondaryBtn} onClick={() => navigate('/chat')}>
            Back to Chat
          </button>
          <button style={styles.secondaryBtn} onClick={() => navigate('/mcp-servers')}>
            MCP Servers
          </button>
          <button style={styles.primaryBtn} onClick={() => navigate('/contexts/new')}>
            + New Context
          </button>
        </div>
      </div>

      <div style={styles.list}>
        {contexts.map((ctx) => (
          <div key={ctx.id} style={styles.card}>
            <div style={styles.cardHeader}>
              <h3 style={styles.cardTitle}>{ctx.name}</h3>
              <span style={styles.cardDate}>
                {new Date(ctx.created_at).toLocaleDateString()}
              </span>
            </div>
            {ctx.description && (
              <p style={styles.cardDesc}>{ctx.description}</p>
            )}
            <p style={styles.cardPrompt}>
              {ctx.system_prompt.slice(0, 120)}...
            </p>
            <div style={styles.cardActions}>
              <button
                style={styles.editBtn}
                onClick={() => navigate(`/contexts/${ctx.id}/edit`)}
              >
                Edit
              </button>
              <button
                style={styles.deleteBtn}
                onClick={() => handleDelete(ctx.id)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '2rem',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '2rem',
  },
  title: {
    fontSize: '1.5rem',
  },
  actions: {
    display: 'flex',
    gap: '0.75rem',
  },
  primaryBtn: {
    padding: '0.5rem 1rem',
    borderRadius: '8px',
    background: 'var(--accent)',
    color: 'white',
    fontWeight: 500,
    fontSize: '0.875rem',
  },
  secondaryBtn: {
    padding: '0.5rem 1rem',
    borderRadius: '8px',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
    fontSize: '0.875rem',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  card: {
    background: 'var(--bg-secondary)',
    borderRadius: '10px',
    padding: '1.25rem',
    border: '1px solid var(--border)',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.5rem',
  },
  cardTitle: {
    fontSize: '1.1rem',
  },
  cardDate: {
    color: 'var(--text-secondary)',
    fontSize: '0.8rem',
  },
  cardDesc: {
    color: 'var(--text-secondary)',
    fontSize: '0.875rem',
    marginBottom: '0.5rem',
  },
  cardPrompt: {
    color: 'var(--text-secondary)',
    fontSize: '0.8rem',
    fontStyle: 'italic',
    marginBottom: '0.75rem',
  },
  cardActions: {
    display: 'flex',
    gap: '0.5rem',
  },
  editBtn: {
    padding: '0.375rem 0.75rem',
    borderRadius: '6px',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
    fontSize: '0.8rem',
  },
  deleteBtn: {
    padding: '0.375rem 0.75rem',
    borderRadius: '6px',
    background: 'transparent',
    color: 'var(--error)',
    border: '1px solid var(--error)',
    fontSize: '0.8rem',
  },
};
