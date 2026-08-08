import { createContext } from 'react';

import type { ReactNode } from 'react';

/** Props passed to every managed sign-in renderer injected into the login slot. */
export interface ManagedSignInProps {
  /** Invoked after the managed provider exchanges its session for a LAVS session. */
  readonly onSuccess?: () => void;
}

/** Renders the managed sign-in UI for a single auth mode. */
export type ManagedSignInComponent = (props: ManagedSignInProps) => ReactNode;

/**
 * Maps an auth mode advertised by `/meta` to the component that renders its managed
 * sign-in UI. Keyed by the raw auth-mode string so external (EE) builds can register
 * managed-identity modes the core `AuthMode` union does not know about.
 */
export type ManagedSignInRegistry = Readonly<Record<string, ManagedSignInComponent>>;

/**
 * Login-form extension slot. OSS provides the empty default (nothing renders); an
 * external (EE) build wraps the app in
 * `<ManagedSignInContext.Provider value={{ <mode>: <Component> }}>`, so `LoginForm`
 * renders that component whenever `/meta` advertises the matching auth mode.
 */
export const ManagedSignInContext = createContext<ManagedSignInRegistry>({});
