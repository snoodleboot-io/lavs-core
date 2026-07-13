import { useState, type FormEvent, type ReactNode } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth';

import styles from './login-page.module.css';

/**
 * Minimal password/session login (foundation). R4 enhances it to be `/meta`-adaptive
 * (render only enabled auth modes) and completes the a11y pass.
 */
export function LoginPage(): ReactNode {
  const { status, meta, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === 'authenticated') {
    return <Navigate to="/" replace />;
  }

  const passwordEnabled = !meta || meta.auth_modes.includes('password');

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const result = await login({ email, password });
    setSubmitting(false);
    if (result.ok) {
      void navigate('/', { replace: true });
    } else {
      setError(result.error.message);
    }
  }

  return (
    <div className={styles.wrap}>
      <form className={styles.card} onSubmit={(event) => void onSubmit(event)} aria-labelledby="login-title">
        <h1 id="login-title" className={styles.title}>
          LAVS <span className={styles.tag}>Constellation</span>
        </h1>
        <p className={styles.sub}>Sign in to observe the streams.</p>

        {passwordEnabled ? (
          <>
            <label className={styles.label} htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className={styles.input}
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />

            <label className={styles.label} htmlFor="password">
              Password
            </label>
            <input
              id="password"
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
          </>
        ) : (
          <p className={styles.sub}>
            This deployment uses a configured API key; no interactive login is required.
          </p>
        )}
      </form>
    </div>
  );
}
