import client from './client'
import { HospitalStay } from '../types'

export interface HospitalStayFilters {
  status?: string
  report_status?: string
  invoice_status?: string
  hospital_id?: number
  search?: string
  skip?: number
  limit?: number
}

export interface HospitalStayInvoiceLinePayload {
  libelle: string
  quantite: number
  prix_unitaire: number
}

export interface HospitalStayInvoicePayload {
  taux_tva: number
  notes?: string
  lines?: HospitalStayInvoiceLinePayload[]
}

export const hospitalSinistresApi = {
  async getHospitalStays(filters: HospitalStayFilters = {}): Promise<HospitalStay[]> {
    const response = await client.get('/hospital-sinistres/hospital-stays', {
      params: filters,
    })
    return response.data
  },

  async getHospitalStay(stayId: number): Promise<HospitalStay> {
    const response = await client.get(`/hospital-sinistres/hospital-stays/${stayId}`)
    return response.data
  },

  async createInvoice(stayId: number, payload: HospitalStayInvoicePayload): Promise<HospitalStay> {
    const response = await client.post(`/hospital-sinistres/hospital-stays/${stayId}/invoice`, payload)
    return response.data
  },
}

