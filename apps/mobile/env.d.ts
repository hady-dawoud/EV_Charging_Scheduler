declare const __DEV__: boolean;

declare global {
  namespace NodeJS {
    interface ProcessEnv {
      EXPO_PUBLIC_API_BASE_URL?: string;
      NODE_ENV?: string;
    }
  }

  interface ImportMetaEnv {
    readonly VITE_API_BASE_URL?: string;
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}

export {};
