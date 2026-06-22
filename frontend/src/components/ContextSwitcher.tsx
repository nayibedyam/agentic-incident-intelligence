import type { ContextProfile } from '../types';

interface Props {
  contexts: ContextProfile[];
  active: ContextProfile;
  onSwitch: (ctx: ContextProfile) => void;
}

export default function ContextSwitcher({ contexts, active, onSwitch }: Props) {
  return (
    <div style={styles.container}>
      <label style={styles.label}>Context:</label>
      <select
        style={styles.select}
        value={active.id}
        onChange={(e) => {
          const ctx = contexts.find((c) => c.id === e.target.value);
          if (ctx) onSwitch(ctx);
        }}
      >
        {contexts.map((ctx) => (
          <option key={ctx.id} value={ctx.id}>
            {ctx.name}
          </option>
        ))}
      </select>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  label: {
    fontSize: '0.875rem',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  select: {
    padding: '0.5rem 0.75rem',
    borderRadius: '6px',
    border: '1px solid var(--border)',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    fontSize: '0.875rem',
  },
};
