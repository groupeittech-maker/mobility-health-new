import client from './client'

export interface QuestionnaireResponse {
  id: number
  souscription_id: number
  type_questionnaire: 'short' | 'long' | 'administratif' | 'medical'
  version: number
  reponses: Record<string, any>
  statut: string
  created_at: string
  updated_at: string
  notes?: string
}

export interface QuestionnaireStatusResponse {
  id: number
  type_questionnaire: 'short' | 'long' | 'administratif'
  statut: string
  version: number
  created_at: string
  updated_at: string
}

export const questionnairesApi = {
  /**
   * Créer ou mettre à jour un questionnaire court
   */
  createShort: async (subscriptionId: number, reponses: Record<string, any>): Promise<QuestionnaireResponse> => {
    const response = await client.post<QuestionnaireResponse>(
      `/subscriptions/${subscriptionId}/questionnaire/short`,
      reponses
    )
    return response.data
  },

  /**
   * Créer ou mettre à jour un questionnaire long
   */
  createLong: async (subscriptionId: number, reponses: Record<string, any>): Promise<QuestionnaireResponse> => {
    const response = await client.post<QuestionnaireResponse>(
      `/subscriptions/${subscriptionId}/questionnaire/long`,
      reponses
    )
    return response.data
  },

  /**
   * Obtenir le statut d'un questionnaire
   */
  getStatus: async (questionnaireId: number): Promise<QuestionnaireStatusResponse> => {
    const response = await client.get<QuestionnaireStatusResponse>(
      `/questionnaire/${questionnaireId}/status`
    )
    return response.data
  },

  /**
   * Créer ou mettre à jour un questionnaire administratif/technique
   */
  createAdministratif: async (subscriptionId: number, reponses: Record<string, any>): Promise<QuestionnaireResponse> => {
    const response = await client.post<QuestionnaireResponse>(
      `/subscriptions/${subscriptionId}/questionnaire/administratif`,
      reponses
    )
    return response.data
  },

  /**
   * Créer ou mettre à jour un questionnaire médical
   */
  createMedical: async (subscriptionId: number, reponses: Record<string, any>): Promise<QuestionnaireResponse> => {
    const response = await client.post<QuestionnaireResponse>(
      `/subscriptions/${subscriptionId}/questionnaire/medical`,
      reponses
    )
    return response.data
  },

  /**
   * Obtenir un questionnaire par souscription et type
   */
  getBySubscription: async (
    subscriptionId: number,
    type: 'short' | 'long' | 'administratif' | 'medical'
  ): Promise<QuestionnaireResponse> => {
    const response = await client.get<QuestionnaireResponse>(
      `/subscriptions/${subscriptionId}/questionnaire/${type}`
    )
    return response.data
  },
}

