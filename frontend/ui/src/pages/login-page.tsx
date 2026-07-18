import type { ReactNode } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { LoginForm, useAuth } from '@/features/auth';

import styles from './login-page.module.css';

/** Login route: brand chrome around the `/meta`-adaptive LoginForm (R4). */
export function LoginPage(): ReactNode {
  const { status } = useAuth();
  const navigate = useNavigate();

  if (status === 'authenticated') {
    return <Navigate to="/" replace />;
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <h1 className={styles.title}>
          LAVS <span className={styles.tag}>Constellation</span>
        </h1>
        <p className={styles.sub}>Sign in to observe the streams.</p>
        <LoginForm onSuccess={() => void navigate('/', { replace: true })} />
      </div>
    </div>
  );
}
