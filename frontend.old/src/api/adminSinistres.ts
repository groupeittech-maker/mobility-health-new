import client from './client'
import { Alerte, Sinistre } from '../types'
import { normalizeAlerte } from './transformers'

export interface AssignHospitalRequest {
  hospital_id: number
}

export interface CloseSinistreRequest {
  notes?: string
}

export interface UpdateWorkflowStepRequest {
  statut: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  notes?: string
}

export const adminSinistresApi = {
  getAlertes: async (statut?: string): Promise<Alerte[]> => {
    const params = statut ? { statut } : {}
    const response = await client.get('/admin/sinistres/alertes', { params })
    return response.data.map(normalizeAlerte)
  },

  getSinistres: async (statut?: string): Promise<Sinistre[]> => {
    const params = statut ? { statut } : {}
    const response = await client.get('/admin/sinistres/sinistres', { params })
    return response.data
  },

  getSinistre: async (id: number): Promise<Sinistre> => {
    const response = await client.get(`/admin/sinistres/sinistres/${id}`)
    return response.data
  },

  assignHospital: async (sinistreId: number, data: AssignHospitalRequest): Promise<Sinistre> => {
    const response = await client.put(`/admin/sinistres/sinistres/${sinistreId}/assign-hospital`, data)
    return response.data
  },

  closeSinistre: async (sinistreId: number, data: CloseSinistreRequest): Promise<Sinistre> => {
    const response = await client.put(`/admin/sinistres/sinistres/${sinistreId}/close`, data)
    return response.data
  },

  updateNotes: async (sinistreId: number, notes: string): Promise<Sinistre> => {
    const response = await client.put(`/admin/sinistres/sinistres/${sinistreId}/update-notes`, { notes })
    return response.data
  },

  updateWorkflowStep: async (
    sinistreId: number,
    stepKey: string,
    data: UpdateWorkflowStepRequest,
  ) => {
    const response = await client.put(
      `/admin/sinistres/sinistres/${sinistreId}/workflow/${stepKey}`,
      data,
    )
    return response.data
  },
}

