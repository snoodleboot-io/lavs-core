/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LAVS_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
