import client from './client'
import {
  Hospital,
  HospitalMarker,
  HospitalMedicalCatalog,
  HospitalMedicalTarif,
  HospitalReceptionist,
} from '../types'

export interface HospitalPayload {
  nom: string
  adresse?: string
  ville?: string
  pays?: string
  code_postal?: string
  telephone?: string
  email?: string
  latitude: number
  longitude: number
  est_actif?: boolean
  specialites?: string
  capacite_lits?: number
  notes?: string
}

export interface ReceptionistPayload {
  email: string
  username: string
  password: string
  full_name?: string
  is_active?: boolean
}

export interface MedicalTarifPayload {
  nom: string
  montant: number
  code?: string
  description?: string
}

export interface ExamTarifPayload {
  nom: string
  montant: number
}

export const hospitalsApi = {
  getAll: async (): Promise<Hospital[]> => {
    const response = await client.get('/hospitals')
    return response.data
  },

  getMapMarkers: async (): Promise<HospitalMarker[]> => {
    const response = await client.get('/hospitals/map/markers')
    return response.data
  },

  create: async (data: HospitalPayload): Promise<Hospital> => {
    const response = await client.post('/hospitals', data)
    return response.data
  },

  getById: async (id: number): Promise<Hospital> => {
    const response = await client.get(`/hospitals/${id}`)
    return response.data
  },

  getReceptionists: async (hospitalId: number): Promise<HospitalReceptionist[]> => {
    const response = await client.get(`/hospitals/${hospitalId}/receptionists`)
    return response.data
  },

  createReceptionist: async (
    hospitalId: number,
    payload: ReceptionistPayload,
  ): Promise<HospitalReceptionist> => {
    const response = await client.post(`/hospitals/${hospitalId}/receptionists`, payload)
    return response.data
  },

  getMedicalCatalog: async (hospitalId: number): Promise<HospitalMedicalCatalog> => {
    const response = await client.get(`/hospitals/${hospitalId}/medical-catalog`)
    const data = response.data as HospitalMedicalCatalog
    return {
      ...data,
      actes: data.actes.map((act) => ({
        ...act,
        montant: Number(act.montant),
      })),
      examens: data.examens.map((exam) => ({
        ...exam,
        montant: Number(exam.montant),
      })),
      defaults: {
        hourly_rate: Number(data.defaults.hourly_rate),
        default_act_price: Number(data.defaults.default_act_price),
        default_exam_price: Number(data.defaults.default_exam_price),
      },
    }
  },

  createMedicalAct: async (hospitalId: number, payload: MedicalTarifPayload): Promise<HospitalMedicalTarif> => {
    const response = await client.post(`/hospitals/${hospitalId}/act-tarifs`, payload)
    const data = response.data as HospitalMedicalTarif
    return { ...data, montant: Number(data.montant) }
  },

  deleteMedicalAct: async (hospitalId: number, actId: number): Promise<void> => {
    await client.delete(`/hospitals/${hospitalId}/act-tarifs/${actId}`)
  },

  createMedicalExam: async (hospitalId: number, payload: ExamTarifPayload): Promise<HospitalMedicalTarif> => {
    const response = await client.post(`/hospitals/${hospitalId}/exam-tarifs`, payload)
    const data = response.data as HospitalMedicalTarif
    return { ...data, montant: Number(data.montant) }
  },

  deleteMedicalExam: async (hospitalId: number, examId: number): Promise<void> => {
    await client.delete(`/hospitals/${hospitalId}/exam-tarifs/${examId}`)
  },
}

