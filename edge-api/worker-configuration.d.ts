/// <reference types="@cloudflare/workers-types" />

declare global {
  interface Env {
    APP_NAME: string;
    COURSE_NAME: string;
    API_TOKEN?: string;
    ADMIN_EMAIL?: string;
    SETTINGS: KVNamespace;
  }
}

export {};
