/// <reference types="vite/client" />

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresStudent?: boolean
    requiresRole?: string
  }
}
