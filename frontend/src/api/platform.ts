import { http } from '@/lib/http'

// 平台运营（跨租户超管）。后端 require_role(platform_admin)。
export interface PlatformTotals { tenants: number; students: number; reports: number; matches: number }
export interface TenantStat {
  id: string
  name: string
  student_count: number
  teacher_count: number
  report_count: number
  avg_competitiveness: number
  improvement_pct: number | null
  created_at: string
}
export interface OverviewResponse { totals: PlatformTotals; tenants: TenantStat[]; top: TenantStat[] }
export interface TenantDetail {
  tenant: TenantStat
  students: Array<{ student_id: string; name: string; competitiveness: number; completeness: number }>
}

export const platformApi = {
  overview: () => http.get<OverviewResponse>('/platform/overview'),
  tenants: () => http.get<{ tenants: TenantStat[] }>('/platform/tenants'),
  tenantDetail: (id: string) => http.get<TenantDetail>(`/platform/tenants/${id}`),
  createTenant: (name: string, adminUsername: string, adminPassword: string, tenantId?: string) =>
    http.post<{ tenant_id: string; name: string; admin_username: string }>('/platform/tenants', {
      name, admin_username: adminUsername, admin_password: adminPassword, tenant_id: tenantId || undefined,
    }),
}
