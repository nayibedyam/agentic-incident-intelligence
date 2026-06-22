import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { contextApi } from '../services/api';

interface Props {
  onCreated: () => void;
}

export default function ContextSetupPage({ onCreated }: Props) {
  const navigate = useNavigate();
  const { id } = useParams();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !systemPrompt.trim()) {
      setError('Name and System Context are required');
      return;
    }

    setSaving(true);
    setError('');
    try {
      if (id) {
        await contextApi.update(id, { name, description, system_prompt: systemPrompt });
      } else {
        await contextApi.create({ name, description, system_prompt: systemPrompt });
      }
      onCreated();
      navigate('/chat');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save context');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>
          {id ? 'Edit Context Profile' : 'Welcome to Incident Intelligence'}
        </h1>
        {!id && (
          <p style={styles.subtitle}>
            Before you begin, define your system context. This tells the agent about your service, its architecture, and common failure modes.
          </p>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>Context Name</label>
            <input
              style={styles.input}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., payment-service"
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Description</label>
            <input
              style={styles.input}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Short description of the service"
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>System Context (what should the agent know?)</label>
            <textarea
              style={styles.textarea}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="Describe your service architecture, common failure modes, dependencies, technology stack, and any domain-specific knowledge the agent needs..."
              rows={10}
            />
          </div>

          {error && <p style={styles.error}>{error}</p>}

          <button type="submit" style={styles.button} disabled={saving}>
            {saving ? 'Saving...' : id ? 'Update Context' : 'Create Context'}
          </button>
        </form>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    padding: '2rem',
  },
  card: {
    background: 'var(--bg-secondary)',
    borderRadius: '12px',
    padding: '2.5rem',
    maxWidth: '640px',
    width: '100%',
    border: '1px solid var(--border)',
  },
  title: {
    fontSize: '1.5rem',
    marginBottom: '0.5rem',
  },
  subtitle: {
    color: 'var(--text-secondary)',
    marginBottom: '1.5rem',
    lineHeight: 1.5,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  label: {
    fontSize: '0.875rem',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  input: {
    padding: '0.75rem 1rem',
    borderRadius: '8px',
    border: '1px solid var(--border)',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    fontSize: '0.9rem',
  },
  textarea: {
    padding: '0.75rem 1rem',
    borderRadius: '8px',
    border: '1px solid var(--border)',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    fontSize: '0.9rem',
    resize: 'vertical' as const,
    lineHeight: 1.5,
  },
  button: {
    padding: '0.75rem 1.5rem',
    borderRadius: '8px',
    background: 'var(--accent)',
    color: 'white',
    fontWeight: 600,
    fontSize: '0.9rem',
    marginTop: '0.5rem',
  },
  error: {
    color: 'var(--error)',
    fontSize: '0.875rem',
  },
};
