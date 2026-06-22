import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { contextApi, mcpApi } from '../services/api';
import type { MCPServer } from '../types';

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

  const [allServers, setAllServers] = useState<MCPServer[]>([]);
  const [linkedServerIds, setLinkedServerIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    mcpApi.list().then(setAllServers).catch(() => {});
    if (id) {
      contextApi.get(id).then(profile => {
        setName(profile.name);
        setDescription(profile.description || '');
        setSystemPrompt(profile.system_prompt);
      });
      contextApi.getLinkedServers(id).then(servers => {
        setLinkedServerIds(new Set(servers.map(s => s.id)));
      }).catch(() => {});
    }
  }, [id]);

  const handleToggleServer = async (serverId: string) => {
    if (!id) return;
    const isLinked = linkedServerIds.has(serverId);
    try {
      if (isLinked) {
        await contextApi.unlinkServer(id, serverId);
        setLinkedServerIds(prev => { const s = new Set(prev); s.delete(serverId); return s; });
      } else {
        await contextApi.linkServer(id, serverId);
        setLinkedServerIds(prev => new Set(prev).add(serverId));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update link');
    }
  };

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

          {id && allServers.length > 0 && (
            <div style={styles.field}>
              <label style={styles.label}>Linked MCP Servers</label>
              <p style={styles.hint}>Select which MCP servers this context can use for tool access.</p>
              <div style={styles.serverList}>
                {allServers.map(server => (
                  <div key={server.id} style={styles.serverItem} onClick={() => handleToggleServer(server.id)}>
                    <input
                      type="checkbox"
                      checked={linkedServerIds.has(server.id)}
                      onChange={() => handleToggleServer(server.id)}
                      style={styles.checkbox}
                    />
                    <div>
                      <span style={styles.serverName}>{server.name}</span>
                      {server.description && <span style={styles.serverDesc}> - {server.description}</span>}
                    </div>
                  </div>
                ))}
              </div>
              <button type="button" style={styles.linkBtn} onClick={() => navigate('/mcp-servers')}>
                Manage MCP Servers
              </button>
            </div>
          )}

          {!id && (
            <p style={styles.hint}>
              After creating this context, you can link MCP servers by editing it.
            </p>
          )}

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
  hint: {
    color: 'var(--text-secondary)',
    fontSize: '0.8rem',
  },
  serverList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
    background: 'var(--bg-tertiary)',
    borderRadius: '8px',
    padding: '0.75rem',
    border: '1px solid var(--border)',
  },
  serverItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.5rem',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  checkbox: {
    width: '16px',
    height: '16px',
  },
  serverName: {
    fontWeight: 500,
    fontSize: '0.875rem',
  },
  serverDesc: {
    color: 'var(--text-secondary)',
    fontSize: '0.8rem',
  },
  linkBtn: {
    padding: '0.375rem 0.75rem',
    borderRadius: '6px',
    background: 'transparent',
    color: 'var(--accent)',
    border: '1px solid var(--accent)',
    fontSize: '0.8rem',
    alignSelf: 'flex-start',
    marginTop: '0.25rem',
  },
};
