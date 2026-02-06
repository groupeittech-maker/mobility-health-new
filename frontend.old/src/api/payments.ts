import client from './client'

export interface PaymentInitiateRequest {
  subscription_id: number
  amount: number
  payment_type: string
}

export interface PaymentInitiateResponse {
  payment_id: number
  payment_url: string
  status: string
}

export interface PaymentStatusResponse {
  payment_id: number
  status: string
  amount: number
  subscription_id: number
  subscription_status: string
  created_at: string
}

export interface PaymentWebhookRequest {
  payment_id: number
  external_reference: string
  status: 'success' | 'failed' | 'pending'
  amount?: number
}

export const paymentsApi = {
  /**
   * Initier un paiement
   */
  initiate: async (data: PaymentInitiateRequest): Promise<PaymentInitiateResponse> => {
    const response = await client.post<PaymentInitiateResponse>('/payments/initiate', data)
    return response.data
  },

  /**
   * Obtenir le statut d'un paiement
   */
  getStatus: async (paymentId: number): Promise<PaymentStatusResponse> => {
    const response = await client.get<PaymentStatusResponse>(`/payments/${paymentId}/status`)
    return response.data
  },

  /**
   * Simuler un webhook de paiement (pour les tests)
   */
  webhook: async (data: PaymentWebhookRequest): Promise<any> => {
    const response = await client.post('/payments/webhook', data)
    return response.data
  },
}

