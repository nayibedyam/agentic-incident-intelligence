import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { mcpApi } from '../services/api';
import type { MCPServer } from '../types';

export default function MCPServersPage() {
  const navigate = useNavigate();
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', description: '', command: '', args: '', env: '' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [error, setError] = useState('');

  const loadServers = async () => {
    try {
      const data = await mcpApi.list();
      setServers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load servers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadServers(); }, []);

  const resetForm = () => {
    setForm({ name: '', description: '', command: '', args: '', env: '' });
    setEditingId(null);
    setShowForm(false);
    setError('');
  };

  const handleEdit = (server: MCPServer) => {
    setForm({
      name: server.name,
      description: server.description || '',
      command: server.command,
      args: (server.args || []).join('\n'),
      env: Object.entries(server.env || {}).map(([k, v]) => `${k}=${v}`).join('\n'),
    });
    setEditingId(server.id);
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.command.trim()) {
      setError('Name and Command are required');
      return;
    }

    const args = form.args.trim() ? form.args.trim().split('\n').map(s => s.trim()).filter(Boolean) : [];
    const env: Record<string, string> = {};
    if (form.env.trim()) {
      for (const line of form.env.trim().split('\n')) {
        const idx = line.indexOf('=');
        if (idx > 0) env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
      }
    }

    setSaving(true);
    setError('');
    try {
      if (editingId) {
        await mcpApi.update(editingId, { name: form.name, description: form.description || undefined, command: form.command, args, env });
      } else {
        await mcpApi.create({ name: form.name, description: form.description || undefined, command: form.command, args, env });
      }
      resetForm();
      await loadServers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this MCP server? It will be unlinked from all context profiles.')) return;
    setTogglingId(id);
    try {
      await mcpApi.delete(id);
      await loadServers();
    } finally {
      setTogglingId(null);
    }
  };

  const handleToggle = async (server: MCPServer) => {
    setTogglingId(server.id);
    setError('');
    try {
      if (server.running) {
        await mcpApi.stop(server.id);
      } else {
        await mcpApi.start(server.id);
      }
      await loadServers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle server');
    } finally {
      setTogglingId(null);
    }
  };

  if (loading) {
    return (
      <div style={styles.loading}>
        <span className="spinner" style={{ width: '24px', height: '24px', borderWidth: '3px' }} />
        <span style={{ marginLeft: '0.75rem', color: 'var(--text-secondary)' }}>Loading MCP servers...</span>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>MCP Servers</h1>
        <div style={styles.actions}>
          <button style={styles.secondaryBtn} onClick={() => navigate('/chat')}>Back to Chat</button>
          <button style={styles.primaryBtn} onClick={() => { resetForm(); setShowForm(true); }}>+ Add Server</button>
        </div>
      </div>

      <p style={styles.subtitle}>
        Manage Model Context Protocol servers. These provide external tools (JIRA, Confluence, etc.) to the AI agent.
      </p>

      {error && <p style={styles.error}>{error}</p>}

      {showForm && (
        <div style={styles.formCard}>
          <h3 style={styles.formTitle}>{editingId ? 'Edit Server' : 'Register New MCP Server'}</h3>
          <form onSubmit={handleSubmit} style={styles.form}>
            <div style={styles.field}>
              <label style={styles.label}>Name</label>
              <input style={styles.input} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g., atlassian-mcp" />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Description</label>
              <input style={styles.input} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="JIRA & Confluence integration" />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Command</label>
              <input style={styles.input} value={form.command} onChange={e => setForm({ ...form, command: e.target.value })} placeholder="docker" />
              <span style={styles.hint}>The executable to run (e.g., docker, npx, node)</span>
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Arguments (one per line)</label>
              <textarea style={styles.textarea} value={form.args} onChange={e => setForm({ ...form, args: e.target.value })} placeholder={"run\n--rm\n-i\nghcr.io/sooperset/mcp-atlassian:latest"} rows={5} />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Environment Variables (KEY=VALUE, one per line)</label>
              <textarea style={styles.textarea} value={form.env} onChange={e => setForm({ ...form, env: e.target.value })} placeholder={"JIRA_URL=https://your-org.atlassian.net\nJIRA_USERNAME=user@example.com\nJIRA_API_TOKEN=your-token"} rows={4} />
              <span style={styles.hint}>These are passed securely to the MCP server process</span>
            </div>
            <div style={styles.formActions}>
              <button type="button" style={styles.secondaryBtn} onClick={resetForm}>Cancel</button>
              <button type="submit" style={styles.primaryBtn} disabled={saving}>
                {saving ? <><span className="spinner" style={{ marginRight: '0.5rem' }} /> Saving...</> : editingId ? 'Update' : 'Register'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div style={styles.list}>
        {servers.length === 0 && !showForm && (
          <div style={styles.empty}>No MCP servers registered yet. Click "+ Add Server" to get started.</div>
        )}
        {servers.map(server => {
          const isToggling = togglingId === server.id;
          return (
            <div key={server.id} style={styles.card}>
              <div style={styles.cardHeader}>
                <div style={styles.cardTitleRow}>
                  <h3 style={styles.cardTitle}>{server.name}</h3>
                  <span style={{ ...styles.badge, background: server.running ? 'var(--success)' : 'var(--bg-tertiary)', color: server.running ? 'white' : 'var(--text-secondary)' }}>
                    {isToggling ? <span className="spinner" style={{ width: '10px', height: '10px', borderWidth: '1.5px' }} /> : null}
                    {' '}{server.running ? 'Running' : 'Stopped'}
                  </span>
                </div>
                <span style={styles.cardDate}>{new Date(server.created_at).toLocaleDateString()}</span>
              </div>
              {server.description && <p style={styles.cardDesc}>{server.description}</p>}
              <p style={styles.cardCommand}>{server.command} {(server.args || []).slice(0, 3).join(' ')}{(server.args || []).length > 3 ? ' ...' : ''}</p>
              {Object.keys(server.env || {}).length > 0 && (
                <p style={styles.cardEnvCount}>{Object.keys(server.env).length} env variable(s) configured</p>
              )}
              <div style={styles.cardActions}>
                <button
                  style={{ ...styles.toggleBtn, opacity: isToggling ? 0.7 : 1 }}
                  onClick={() => handleToggle(server)}
                  disabled={isToggling}
                >
                  {isToggling ? <><span className="spinner" style={{ width: '12px', height: '12px', borderWidth: '1.5px', marginRight: '0.375rem' }} />{server.running ? 'Stopping...' : 'Starting...'}</> : server.running ? 'Stop' : 'Start'}
                </button>
                <button style={styles.editBtn} onClick={() => handleEdit(server)} disabled={isToggling}>Edit</button>
                <button style={styles.deleteBtn} onClick={() => handleDelete(server.id)} disabled={isToggling}>Delete</button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { maxWidth: '800px', margin: '0 auto', padding: '2rem' },
  loading: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' },
  title: { fontSize: '1.5rem' },
  subtitle: { color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' },
  actions: { display: 'flex', gap: '0.75rem' },
  primaryBtn: { padding: '0.5rem 1rem', borderRadius: '8px', background: 'var(--accent)', color: 'white', fontWeight: 500, fontSize: '0.875rem', display: 'flex', alignItems: 'center' },
  secondaryBtn: { padding: '0.5rem 1rem', borderRadius: '8px', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border)', fontSize: '0.875rem' },
  error: { color: 'var(--error)', fontSize: '0.875rem', marginBottom: '1rem', padding: '0.5rem 0.75rem', background: 'rgba(239,68,68,0.1)', borderRadius: '6px', border: '1px solid rgba(239,68,68,0.2)' },
  formCard: { background: 'var(--bg-secondary)', borderRadius: '10px', padding: '1.5rem', border: '1px solid var(--border)', marginBottom: '1.5rem' },
  formTitle: { fontSize: '1.1rem', marginBottom: '1rem' },
  form: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  field: { display: 'flex', flexDirection: 'column', gap: '0.375rem' },
  label: { fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 },
  input: { padding: '0.625rem 0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.875rem' },
  textarea: { padding: '0.625rem 0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.875rem', resize: 'vertical' as const, fontFamily: 'monospace' },
  hint: { fontSize: '0.75rem', color: 'var(--text-secondary)' },
  formActions: { display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' },
  list: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  empty: { textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', borderRadius: '10px', border: '1px solid var(--border)' },
  card: { background: 'var(--bg-secondary)', borderRadius: '10px', padding: '1.25rem', border: '1px solid var(--border)' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' },
  cardTitleRow: { display: 'flex', alignItems: 'center', gap: '0.75rem' },
  cardTitle: { fontSize: '1.05rem' },
  badge: { fontSize: '0.7rem', padding: '0.2rem 0.5rem', borderRadius: '4px', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' },
  cardDate: { color: 'var(--text-secondary)', fontSize: '0.75rem' },
  cardDesc: { color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '0.375rem' },
  cardCommand: { fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-secondary)', background: 'var(--bg-tertiary)', padding: '0.375rem 0.625rem', borderRadius: '4px', marginBottom: '0.375rem' },
  cardEnvCount: { fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' },
  cardActions: { display: 'flex', gap: '0.5rem', marginTop: '0.5rem' },
  toggleBtn: { padding: '0.375rem 0.75rem', borderRadius: '6px', background: 'var(--accent)', color: 'white', fontSize: '0.8rem', fontWeight: 500, display: 'inline-flex', alignItems: 'center' },
  editBtn: { padding: '0.375rem 0.75rem', borderRadius: '6px', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border)', fontSize: '0.8rem' },
  deleteBtn: { padding: '0.375rem 0.75rem', borderRadius: '6px', background: 'transparent', color: 'var(--error)', border: '1px solid var(--error)', fontSize: '0.8rem' },
};
