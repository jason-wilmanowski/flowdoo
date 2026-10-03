/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the Flowdoo API, e.g. http://localhost:8000 */
  readonly VITE_API_URL?: string;
  /** "api" (default) or "fixtures": where traces come from */
  readonly VITE_DATA_SOURCE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
