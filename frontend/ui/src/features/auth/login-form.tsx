import { useState, type FormEvent, type ReactNode } from 'react';

import { useAuth } from '@/features/auth';

import styles from './login-form.module.css';

export interface LoginFormProps {
  /** Invoked after a successful login (e.g. to redirect). */
  readonly onSuccess?: () => void;
}

/**
 * `/meta`-adaptive, a11y-complete login form. Renders the password form when the
 * deployment enables `password` (or before `/meta` resolves), and otherwise explains
 * the configured non-interactive auth mode (`apikey`) or the future managed sign-in
 * (`stytch`). This is the production replacement for the foundation's placeholder form.
 */
export function LoginForm({ onSuccess }: LoginFormProps): ReactNode {
  const { meta, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Before /meta resolves we optimistically offer the password form (the OSS default).
  const passwordEnabled = !meta || meta.auth_modes.includes('password');
  const apiKeyEnabled = meta?.auth_modes.includes('apikey') ?? false;
  const stytchEnabled = meta?.auth_modes.includes('stytch') ?? false;

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const result = await login({ email, password });
    setSubmitting(false);
    if (result.ok) {
      onSuccess?.();
    } else {
      setError(result.error.message);
    }
  }

  if (passwordEnabled) {
    return (
      <form
        className={styles.form}
        onSubmit={(event) => void onSubmit(event)}
        aria-labelledby="login-form-title"
      >
        <h2 id="login-form-title" className={styles.title}>
          Sign in
        </h2>

        <label className={styles.label} htmlFor="login-email">
          Email
        </label>
        <input
          id="login-email"
          className={styles.input}
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <label className={styles.label} htmlFor="login-password">
          Password
        </label>
        <input
          id="login-password"
          className={styles.input}
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        <button className={styles.submit} type="submit" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    );
  }

  if (apiKeyEnabled) {
    return (
      <div className={styles.notice} role="status">
        <h2 className={styles.title}>Configured API key</h2>
        <p className={styles.sub}>
          This deployment authenticates with a configured API key — no interactive login is
          required.
        </p>
      </div>
    );
  }

  if (stytchEnabled) {
    return (
      <div className={styles.notice} role="status">
        <h2 className={styles.title}>Managed sign-in</h2>
        <p className={styles.sub}>Managed sign-in is coming soon.</p>
      </div>
    );
  }

  return (
    <div className={styles.notice} role="status">
      <h2 className={styles.title}>Sign-in unavailable</h2>
      <p className={styles.sub}>No interactive auth mode is enabled for this deployment.</p>
    </div>
  );
}
