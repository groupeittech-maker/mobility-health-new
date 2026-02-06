import client from './client'
import { Assureur, ProduitAssurance } from '../types'

export interface SearchParams {
  projet_voyage_id?: number
  destination?: string
  date_depart?: string
  nombre_participants?: number
}

export interface AssureurPayload {
  nom: string
  pays: string
  logo_url?: string
  adresse?: string
  telephone?: string
  agent_comptable_id?: number | null
}

export const assureursApi = {
  search: async (params: SearchParams): Promise<ProduitAssurance[]> => {
    const response = await client.get('/assureurs/search', { params })
    return response.data
  },
  listAdmin: async (search?: string): Promise<Assureur[]> => {
    const params = search ? { search } : undefined
    const response = await client.get('/admin/assureurs', { params })
    return response.data
  },
  createAdmin: async (payload: AssureurPayload): Promise<Assureur> => {
    const response = await client.post('/admin/assureurs', payload)
    return response.data
  },
  updateAdmin: async (id: number, payload: Partial<AssureurPayload>): Promise<Assureur> => {
    const response = await client.put(`/admin/assureurs/${id}`, payload)
    return response.data
  },
  getById: async (id: number): Promise<Assureur> => {
    const response = await client.get(`/admin/assureurs/${id}`)
    return response.data
  },
}
