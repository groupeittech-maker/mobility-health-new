import client from './client'

export interface DashboardStats {
  subscriptions_today: number
  subscriptions_pending: number
  sinistres_open: number
  payments_recent: Array<{
    id: number
    montant: number
    statut: string
    date_paiement: string | null
    created_at: string
    subscription_id: number
    user_id: number
  }>
  total_revenue: number
  total_revenue_today: number
}

export interface Statistics {
  subscriptions_by_period: Record<string, number>
  top_products: Array<{
    id: number
    nom: string
    count: number
  }>
  revenue_by_period: Record<string, number>
  sinistres_by_country: Record<string, number>
  sinistres_by_product: Record<string, number>
}

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await client.get('/dashboard/stats')
    return response.data
  },

  getStatistics: async (period: string = 'month'): Promise<Statistics> => {
    const response = await client.get('/dashboard/statistics', { params: { period } })
    return response.data
  },
}

