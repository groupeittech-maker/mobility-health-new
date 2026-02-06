import client from './client'
import { ProjetVoyage } from '../types'

export const voyagesApi = {
  create: async (data: Partial<ProjetVoyage>): Promise<ProjetVoyage> => {
    const response = await client.post('/voyages', data)
    return response.data
  },

  getById: async (id: number): Promise<ProjetVoyage> => {
    const response = await client.get(`/voyages/${id}`)
    return response.data
  },
}
