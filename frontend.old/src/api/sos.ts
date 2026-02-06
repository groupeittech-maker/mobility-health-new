import client from './client'
import type { Alerte, Hospital } from '../types'
import { normalizeAlerte } from './transformers'

export interface TriggerSOSRequest {
  latitude: number
  longitude: number
  adresse?: string
  description?: string
  priorite?: string
  souscription_id?: number
}

export interface PrestationInfo {
  id: number
  code_prestation: string
  libelle: string
  description?: string
  montant_unitaire: number
  quantite: number
  montant_total: number
  date_prestation: string
  statut: string
}

export interface SinistreWorkflowStep {
  step_key: string
  titre: string
  description?: string
  ordre: number
  statut: string
  completed_at?: string
  actor_id?: number
  details?: Record<string, any>
}

export interface SinistreDetail {
  id: number
  alerte_id: number
  souscription_id?: number
  hospital_id?: number
  numero_sinistre: string
  description?: string
  statut: string
  agent_sinistre_id?: number
  medecin_referent_id?: number
  notes?: string
  created_at: string
  updated_at: string
  hospital?: Hospital
  prestations: PrestationInfo[]
  agent_sinistre_nom?: string
  medecin_referent_nom?: string
  workflow_steps: SinistreWorkflowStep[]
}

export const sosApi = {
  trigger: async (data: TriggerSOSRequest): Promise<Alerte> => {
    const response = await client.post('/sos/trigger', data)
    return normalizeAlerte(response.data)
  },

  getAlertes: async (statut?: string): Promise<Alerte[]> => {
    const params = statut ? { statut } : {}
    const response = await client.get('/sos', { params })
    return response.data.map(normalizeAlerte)
  },

  getAlerte: async (id: number): Promise<Alerte> => {
    const response = await client.get(`/sos/${id}`)
    return normalizeAlerte(response.data)
  },

  getSinistreByAlerte: async (alerteId: number): Promise<SinistreDetail> => {
    const response = await client.get(`/sos/${alerteId}/sinistre`)
    return response.data
  },
}
