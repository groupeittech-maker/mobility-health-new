import client from './client'
import { Souscription } from '../types'

export interface StartSubscriptionRequest {
  produit_assurance_id: number
  projet_voyage_id?: number
  date_debut?: string
  notes?: string
}

export const subscriptionsApi = {
  start: async (data: StartSubscriptionRequest): Promise<Souscription> => {
    const response = await client.post('/subscriptions/start', data)
    return response.data
  },

  getAll: async (): Promise<Souscription[]> => {
    const response = await client.get('/subscriptions')
    return response.data
  },

  getById: async (id: number): Promise<Souscription> => {
    const response = await client.get(`/subscriptions/${id}`)
    return response.data
  },
}
