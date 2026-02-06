import client from './client'
import { ProduitAssurance, HistoriquePrix } from '../types'

export const productsApi = {
  // Admin endpoints
  getAll: async (estActif?: boolean): Promise<ProduitAssurance[]> => {
    const params = estActif !== undefined ? { est_actif: estActif } : {}
    const response = await client.get('/admin/products', { params })
    return response.data
  },

  getById: async (id: number): Promise<ProduitAssurance> => {
    const response = await client.get(`/products/${id}`)
    return response.data
  },

  create: async (data: Partial<ProduitAssurance>): Promise<ProduitAssurance> => {
    const response = await client.post('/admin/products', data)
    return response.data
  },

  update: async (id: number, data: Partial<ProduitAssurance>): Promise<ProduitAssurance> => {
    const response = await client.put(`/admin/products/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/admin/products/${id}`)
  },

  getPriceHistory: async (id: number): Promise<HistoriquePrix[]> => {
    const response = await client.get(`/admin/products/${id}/price-history`)
    return response.data
  },

  // Public endpoints
  getPublicProducts: async (estActif: boolean = true): Promise<ProduitAssurance[]> => {
    const response = await client.get('/products', { params: { est_actif: estActif } })
    return response.data
  },
}