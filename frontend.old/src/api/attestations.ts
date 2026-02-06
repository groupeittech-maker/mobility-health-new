import client from './client'

export interface Attestation {
  id: number
  souscription_id: number
  paiement_id: number | null
  type_attestation: 'provisoire' | 'definitive'
  numero_attestation: string
  chemin_fichier_minio: string
  bucket_minio: string
  url_signee: string | null
  date_expiration_url: string | null
  est_valide: boolean
  created_at: string
  updated_at: string
  notes?: string
}

export interface AttestationWithURL {
  id: number
  type_attestation: 'provisoire' | 'definitive'
  numero_attestation: string
  url_signee: string
  date_expiration_url: string
  created_at: string
}

export interface ValidationAttestation {
  id: number
  attestation_id: number
  type_validation: 'medecin' | 'technique' | 'production'
  est_valide: boolean
  valide_par_user_id: number | null
  date_validation: string | null
  commentaires: string | null
  created_at: string
  updated_at: string
}

export const attestationsApi = {
  /**
   * Obtenir toutes les attestations d'une souscription
   */
  getBySubscription: async (subscriptionId: number): Promise<Attestation[]> => {
    const response = await client.get<Attestation[]>(
      `/subscriptions/${subscriptionId}/attestations`
    )
    return response.data
  },

  /**
   * Obtenir une attestation avec URL signée
   */
  getWithUrl: async (attestationId: number): Promise<AttestationWithURL> => {
    const response = await client.get<AttestationWithURL>(
      `/attestations/${attestationId}`
    )
    return response.data
  },

  /**
   * Obtenir les validations d'une attestation
   */
  getValidations: async (attestationId: number): Promise<ValidationAttestation[]> => {
    const response = await client.get<ValidationAttestation[]>(
      `/attestations/${attestationId}/validations`
    )
    return response.data
  },

  /**
   * Créer une validation pour une attestation
   */
  createValidation: async (
    attestationId: number,
    data: {
      type_validation: 'medecin' | 'technique' | 'production'
      est_valide: boolean
      commentaires?: string
    }
  ): Promise<ValidationAttestation> => {
    const response = await client.post<ValidationAttestation>(
      `/attestations/${attestationId}/validations`,
      data
    )
    return response.data
  },
}

