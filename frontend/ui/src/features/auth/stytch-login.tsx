import { useEffect, useRef, useState, type ReactNode } from 'react';

import type { Meta } from '@/types';

import { useAuth } from './use-auth';
import styles from './stytch-login.module.css';

// Type-only namespace import: erased at compile time, so the SDK itself is still
// loaded lazily via dynamic import() below.
import type * as StytchSdk from '@stytch/vanilla-js';

export interface StytchLoginProps {
  /** Invoked after the Stytch session is exchanged for a LAVS session. */
  readonly onSuccess?: () => void;
}

/** DOM id the Stytch prebuilt widget mounts into (one login screen per page). */
const STYTCH_WIDGET_ID = 'stytch-login-widget';

type StytchModule = typeof StytchSdk;

/**
 * Publishable token sourcing: prefer the deploy config (`/meta`), fall back to the
 * build-time `VITE_STYTCH_PUBLIC_TOKEN`. Empty strings count as unconfigured.
 */
function resolvePublicToken(meta: Meta): string | null {
  const token = meta.stytch_public_token ?? import.meta.env.VITE_STYTCH_PUBLIC_TOKEN ?? null;
  return token !== null && token !== '' ? token : null;
}

/**
 * EE managed sign-in. Lazy-loads `@stytch/vanilla-js` (the SDK never enters the main
 * bundle for OSS deployments) and mounts Stytch's prebuilt login widget configured for
 * email magic links + OAuth. When the widget completes an auth flow, the Stytch session
 * token is exchanged at `POST /auth/stytch/callback` via the auth context, which sets the
 * HttpOnly `lavs_session` cookie and promotes the returned principal into app state —
 * exactly mirroring the password `login()` flow.
 */
export function StytchLogin({ onSuccess }: StytchLoginProps): ReactNode {
  const { meta, completeStytchLogin } = useAuth();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Latest-ref pattern: the widget mounts once per token; callbacks stay fresh without
  // remounting Stytch's DOM on every provider render.
  const completeStytchLoginRef = useRef(completeStytchLogin);
  const onSuccessRef = useRef(onSuccess);
  useEffect(() => {
    completeStytchLoginRef.current = completeStytchLogin;
    onSuccessRef.current = onSuccess;
  });

  const publicToken = meta ? resolvePublicToken(meta) : null;

  useEffect(() => {
    if (!publicToken) return undefined;
    let cancelled = false;
    let exchanging = false;

    async function mountWidget(): Promise<void> {
      let stytch: StytchModule;
      try {
        stytch = await import('@stytch/vanilla-js');
      } catch {
        if (!cancelled) {
          setError('Managed sign-in failed to load. Reload the page to try again.');
        }
        return;
      }
      if (cancelled || !publicToken) return;

      const client = new stytch.StytchUIClient(publicToken);

      async function exchange(): Promise<void> {
        if (exchanging) return;
        exchanging = true;
        setError(null);
        const tokens = client.session.getTokens();
        // Prefer the JWT (what the backend verifies); fall back to the opaque token.
        const sessionToken = tokens?.session_jwt ?? tokens?.session_token ?? null;
        if (!sessionToken) {
          exchanging = false;
          setError('Managed sign-in did not produce a session token. Please try again.');
          return;
        }
        const result = await completeStytchLoginRef.current(sessionToken);
        exchanging = false;
        if (result.ok) {
          onSuccessRef.current?.();
        } else {
          setError(result.error.message);
        }
      }

      // Redirect magic links / OAuth back to this page; the remounted widget then
      // authenticates the token from the URL and fires AuthenticateFlowComplete.
      const redirectUrl = window.location.href;
      client.mountLogin({
        client,
        elementId: `#${STYTCH_WIDGET_ID}`,
        config: {
          products: [stytch.Products.emailMagicLinks, stytch.Products.oauth],
          emailMagicLinksOptions: {
            loginRedirectURL: redirectUrl,
            signupRedirectURL: redirectUrl,
          },
          oauthOptions: {
            // Fixed product decision (P6 plan, G-P6e): consumer Stytch with magic links +
            // Google/GitHub OAuth. Deployments must enable these providers on their Stytch
            // project; making the list deploy-configurable is deliberately deferred.
            providers: [{ type: 'google' }, { type: 'github' }],
            loginRedirectURL: redirectUrl,
            signupRedirectURL: redirectUrl,
          },
        },
        callbacks: {
          onEvent: (event) => {
            if (event.type === stytch.StytchEventType.AuthenticateFlowComplete) {
              void exchange();
            }
          },
          onError: () => {
            setError('Managed sign-in failed. Please try again.');
          },
        },
      });
      setReady(true);
    }

    void mountWidget();
    return (): void => {
      cancelled = true;
    };
  }, [publicToken]);

  if (!meta) {
    return (
      <div className={styles.container}>
        <p className={styles.loading} role="status">
          Loading sign-in configuration…
        </p>
      </div>
    );
  }

  if (!publicToken) {
    return (
      <div className={styles.container}>
        <h2 className={styles.title}>Managed sign-in</h2>
        <p className={styles.error} role="alert">
          Managed sign-in is enabled, but no Stytch publishable token is configured. Set it in the
          deployment config (or via VITE_STYTCH_PUBLIC_TOKEN) and reload.
        </p>
      </div>
    );
  }

  return (
    <section className={styles.container} aria-labelledby="stytch-login-title">
      <h2 id="stytch-login-title" className={styles.title}>
        Managed sign-in
      </h2>
      {!ready && !error ? (
        <p className={styles.loading} role="status">
          Loading managed sign-in…
        </p>
      ) : null}
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
      <div id={STYTCH_WIDGET_ID} className={styles.widget} data-testid="stytch-widget" />
    </section>
  );
}
