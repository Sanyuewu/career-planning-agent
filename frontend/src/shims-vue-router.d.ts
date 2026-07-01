declare module 'vue-router' {
  import { DefineComponent, Plugin } from 'vue'

  export interface RouteLocationNormalized {
    path: string
    name: string | symbol | null | undefined
    params: Record<string, string | string[]>
    query: Record<string, string | string[]>
    hash: string
    fullPath: string
    matched: RouteRecordNormalized[]
    redirectedFrom: RouteLocationNormalized | undefined
    meta: Record<string, any>
  }

  export interface NavigationGuardNext {
    (): void
    (error: Error): void
    (location: string | RouteLocationRaw): void
    (valid: boolean): void
  }

  export interface RouteRecordRaw {
    path: string
    name?: string | symbol
    component?: DefineComponent<any, any, any> | (() => Promise<any>)
    components?: Record<string, DefineComponent<any, any, any> | (() => Promise<any>)>
    redirect?: string | RouteLocationRaw | ((to: RouteLocationNormalized) => RouteLocationRaw)
    alias?: string | string[]
    children?: RouteRecordRaw[]
    meta?: Record<string, any>
    beforeEnter?: NavigationGuard | NavigationGuard[]
    props?: boolean | Record<string, any> | ((to: RouteLocationNormalized) => Record<string, any>)
    sensitive?: boolean
    strict?: boolean
  }

  export type RouteLocationRaw = string | {
    path?: string
    name?: string | symbol
    params?: Record<string, any>
    query?: Record<string, any>
    hash?: string
  }

  export interface RouteRecordNormalized {
    path: string
    name: string | symbol | null | undefined
    components: Record<string, DefineComponent<any, any, any>>
    redirect?: string | RouteLocationRaw
    meta: Record<string, any>
    beforeEnter?: NavigationGuard | NavigationGuard[]
    props: Record<string, any>
    children: RouteRecordNormalized[]
    aliasOf?: RouteRecordNormalized
  }

  export type NavigationGuard = (
    to: RouteLocationNormalized,
    from: RouteLocationNormalized,
    next: NavigationGuardNext
  ) => any

  export interface Router extends Plugin {
    push(to: RouteLocationRaw): Promise<void>
    replace(to: RouteLocationRaw): Promise<void>
    go(delta: number): void
    back(): void
    forward(): void
    beforeEach(guard: NavigationGuard): () => void
    beforeResolve(guard: NavigationGuard): () => void
    afterEach(guard: (to: RouteLocationNormalized, from: RouteLocationNormalized) => void): () => void
    currentRoute: RouteLocationNormalized
    getRoutes(): RouteRecordNormalized[]
    hasRoute(name: string | symbol): boolean
    removeRoute(name: string | symbol): void
    addRoute(route: RouteRecordRaw): () => void
    addRoute(parentName: string | symbol, route: RouteRecordRaw): () => void
    isReady(): Promise<void>
    onError(handler: (error: any) => void): () => void
    install(app: any): void
  }

  export interface RouterOptions {
    history: RouterHistory
    routes: RouteRecordRaw[]
    scrollBehavior?: (to: RouteLocationNormalized, from: RouteLocationNormalized, savedPosition: any) => any
    parseQuery?: (query: string) => Record<string, any>
    stringifyQuery?: (query: Record<string, any>) => string
    linkActiveClass?: string
    linkExactActiveClass?: string
    sensitive?: boolean
    strict?: boolean
  }

  export interface RouterHistory {
    location: string
    state: any
    push(location: string, state?: any): void
    replace(location: string, state?: any): void
    go(delta: number, triggerListeners?: boolean): void
    listen(callback: (location: string, state: any, direction: string) => void): () => void
    createHref(location: string): string
    destroy(): void
  }

  export function createRouter(options: RouterOptions): Router
  export function createWebHistory(base?: string): RouterHistory
  export function createWebHashHistory(base?: string): RouterHistory
  export function createMemoryHistory(base?: string): RouterHistory
  export function useRouter(): Router
  export function useRoute(): RouteLocationNormalized

  export const START_LOCATION_NORMALIZED: RouteLocationNormalized

  export function onBeforeRouteLeave(guard: NavigationGuard): void
  export function onBeforeRouteUpdate(guard: NavigationGuard): void

  export const RouterView: DefineComponent<any, any, any>
  export const RouterLink: DefineComponent<any, any, any>
}
