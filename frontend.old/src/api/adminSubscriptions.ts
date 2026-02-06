import client from './client'
import { Souscription } from '../types'
import { QuestionnaireResponse } from './questionnaires'

export interface PaiementResponse {
  id: number
  souscription_id: number
  user_id: number
  montant: number
  type_paiement: string
  statut: string
  date_paiement: string | null
  reference_transaction: string | null
  reference_externe: string | null
  notes: string | null
  montant_rembourse: number | null
  created_at: string
  updated_at: string
}

export interface ValidationRequest {
  approved: boolean
  notes?: string
}

export const adminSubscriptionsApi = {
  getAll: async (statut?: string): Promise<Souscription[]> => {
    const params = statut ? { statut } : {}
    const response = await client.get('/admin/subscriptions', { params })
    return response.data
  },

  getPending: async (): Promise<Souscription[]> => {
    const response = await client.get('/admin/subscriptions/pending')
    return response.data
  },

  getById: async (id: number): Promise<Souscription> => {
    const response = await client.get(`/admin/subscriptions/${id}`)
    return response.data
  },

  getQuestionnaires: async (subscriptionId: number): Promise<QuestionnaireResponse[]> => {
    const response = await client.get(`/admin/subscriptions/${subscriptionId}/questionnaires`)
    return response.data
  },

  getPayments: async (subscriptionId: number): Promise<PaiementResponse[]> => {
    const response = await client.get(`/admin/subscriptions/${subscriptionId}/payments`)
    return response.data
  },

  validateMedical: async (subscriptionId: number, data: ValidationRequest): Promise<Souscription> => {
    const response = await client.post(`/admin/subscriptions/${subscriptionId}/validate_medical`, data)
    return response.data
  },

  validateTech: async (subscriptionId: number, data: ValidationRequest): Promise<Souscription> => {
    const response = await client.post(`/admin/subscriptions/${subscriptionId}/validate_tech`, data)
    return response.data
  },

  approveFinal: async (subscriptionId: number, data: ValidationRequest): Promise<Souscription> => {
    const response = await client.post(`/admin/subscriptions/${subscriptionId}/approve_final`, data)
    return response.data
  },

  generateAttestation: async (subscriptionId: number): Promise<{ url: string }> => {
    const response = await client.post(`/admin/subscriptions/${subscriptionId}/generate-attestation`)
    return response.data
  },
}
