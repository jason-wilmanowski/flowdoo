/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the Flowdoo API, e.g. http://localhost:8000 */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
