/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LAVS_API_URL?: string;
  /** Build-time fallback for the Stytch publishable token when `/meta` does not supply one. */
  readonly VITE_STYTCH_PUBLIC_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
