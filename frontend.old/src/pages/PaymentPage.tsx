import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { paymentsApi } from '../api/payments'
import { subscriptionsApi } from '../api/subscriptions'
import { Souscription, Currency } from '../types'
import './PaymentPage.css'

const CURRENCY_SYMBOLS: Record<Currency, string> = {
  EUR: '€',
  USD: '$',
  XOF: 'CFA',
  XAF: 'FCFA',
}

type PaymentMethod = 
  | 'carte_bancaire'
  | 'virement'
  | 'mobile_money_airtel'
  | 'mobile_money_mtn'
  | 'mobile_money_orange'
  | 'mobile_money_moov'
  | 'paiement_differe'

interface PaymentMethodOption {
  value: PaymentMethod
  label: string
  icon: string
  description: string
  available: boolean
}

const PAYMENT_METHODS: PaymentMethodOption[] = [
  {
    value: 'carte_bancaire',
    label: 'Carte bancaire',
    icon: '💳',
    description: 'Paiement sécurisé par carte bancaire (Visa, Mastercard)',
    available: true,
  },
  {
    value: 'virement',
    label: 'Virement bancaire',
    icon: '🏦',
    description: 'Virement bancaire direct',
    available: true,
  },
  {
    value: 'mobile_money_airtel',
    label: 'Airtel Money',
    icon: '📱',
    description: 'Paiement via Airtel Money',
    available: true,
  },
  {
    value: 'mobile_money_mtn',
    label: 'MTN Money',
    icon: '📱',
    description: 'Paiement via MTN Money',
    available: true,
  },
  {
    value: 'mobile_money_orange',
    label: 'Orange Money',
    icon: '📱',
    description: 'Paiement via Orange Money',
    available: true,
  },
  {
    value: 'mobile_money_moov',
    label: 'Moov Money',
    icon: '📱',
    description: 'Paiement via Moov Money',
    available: true,
  },
  {
    value: 'paiement_differe',
    label: 'Paiement différé (Entreprise)',
    icon: '🏢',
    description: 'Paiement différé pour les entreprises (sur facturation)',
    available: true,
  },
]

export default function PaymentPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod | null>(null)
  const [currency, setCurrency] = useState<Currency>('EUR')
  const [mobileMoneyNumber, setMobileMoneyNumber] = useState('')
  const [isEnterprise, setIsEnterprise] = useState(false)
  const [enterpriseName, setEnterpriseName] = useState('')
  const [enterpriseEmail, setEnterpriseEmail] = useState('')

  const subscriptionId = searchParams.get('subscription_id')
  const paymentId = searchParams.get('payment_id')

  // Récupérer la souscription
  const { data: subscription } = useQuery({
    queryKey: ['subscription', subscriptionId],
    queryFn: () => subscriptionsApi.getById(Number(subscriptionId!)),
    enabled: !!subscriptionId,
  })

  // Récupérer le statut du paiement si payment_id est fourni
  const { data: paymentStatus, refetch: refetchPaymentStatus } = useQuery({
    queryKey: ['payment-status', paymentId],
    queryFn: () => paymentsApi.getStatus(Number(paymentId!)),
    enabled: !!paymentId,
    refetchInterval: (data) => {
      // Arrêter le polling si le paiement est terminé
      if (data?.status === 'valide' || data?.status === 'echoue') {
        return false
      }
      return 3000 // Poll toutes les 3 secondes
    },
  })

  const initiatePaymentMutation = useMutation({
    mutationFn: paymentsApi.initiate,
    onSuccess: (data) => {
      // Rediriger vers la page de traitement du paiement
      navigate(`/payment/process?payment_id=${data.payment_id}&subscription_id=${subscriptionId}&method=${selectedMethod}`)
    },
    onError: (error: any) => {
      alert(`Erreur lors de l'initiation du paiement: ${error.response?.data?.detail || error.message}`)
    },
  })

  const formatPrice = (price: number) => {
    return `${price.toFixed(2)} ${CURRENCY_SYMBOLS[currency]}`
  }

  const handlePaymentMethodSelect = (method: PaymentMethod) => {
    setSelectedMethod(method)
    if (method === 'paiement_differe') {
      setIsEnterprise(true)
    } else {
      setIsEnterprise(false)
    }
  }

  const handleInitiatePayment = () => {
    if (!selectedMethod) {
      alert('Veuillez sélectionner un mode de paiement')
      return
    }

    if (!subscription) {
      alert('Souscription non trouvée')
      return
    }

    // Validation selon le mode de paiement
    if (selectedMethod.startsWith('mobile_money_') && !mobileMoneyNumber) {
      alert('Veuillez entrer votre numéro de Mobile Money')
      return
    }

    if (selectedMethod === 'paiement_differe') {
      if (!enterpriseName || !enterpriseEmail) {
        alert('Veuillez remplir les informations de l\'entreprise')
        return
      }
    }

    initiatePaymentMutation.mutate({
      subscription_id: subscription.id,
      amount: subscription.prix_applique,
      payment_type: selectedMethod,
    })
  }

  // Si le paiement est en cours de traitement, afficher le statut
  useEffect(() => {
    if (paymentStatus?.status === 'valide') {
      // Rediriger vers la page de succès avec l'attestation
      navigate(`/payment/success?payment_id=${paymentId}&subscription_id=${subscriptionId}`)
    } else if (paymentStatus?.status === 'echoue') {
      alert('Le paiement a échoué. Veuillez réessayer.')
    }
  }, [paymentStatus, paymentId, subscriptionId, navigate])

  if (!subscriptionId) {
    return (
      <div className="payment-page">
        <div className="error-message">
          <h2>Informations manquantes</h2>
          <p>Veuillez sélectionner une souscription.</p>
          <button onClick={() => navigate('/')} className="btn-primary">
            Retour à l'accueil
          </button>
        </div>
      </div>
    )
  }

  if (!subscription) {
    return (
      <div className="payment-page">
        <div className="loading">Chargement de la souscription...</div>
      </div>
    )
  }

  return (
    <div className="payment-page">
      <div className="subscription-steps-indicator">
        <div className="step completed">
          <div className="step-circle">1</div>
          <div className="step-label">Projet de voyage</div>
        </div>
        <div className="step completed">
          <div className="step-circle">2</div>
          <div className="step-label">Choix du produit</div>
        </div>
        <div className="step completed">
          <div className="step-circle">3</div>
          <div className="step-label">Questionnaire</div>
        </div>
        <div className="step completed">
          <div className="step-circle">4</div>
          <div className="step-label">Validation</div>
        </div>
        <div className="step active">
          <div className="step-circle">5</div>
          <div className="step-label">Paiement</div>
        </div>
      </div>

      <div className="page-header">
        <h1>Étape 5 : Paiement</h1>
        <p>Finalisez votre souscription en effectuant le paiement</p>
      </div>

      <div className="payment-content">
        <div className="payment-summary">
          <h2>Résumé de la souscription</h2>
          <div className="summary-item">
            <span>Numéro de souscription:</span>
            <strong>{subscription.numero_souscription}</strong>
          </div>
          <div className="summary-item">
            <span>Montant à payer:</span>
            <strong className="amount">{formatPrice(subscription.prix_applique)}</strong>
          </div>
          <div className="currency-selector">
            <label>Devise:</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value as Currency)}
            >
              <option value="EUR">EUR (€)</option>
              <option value="USD">USD ($)</option>
              <option value="XOF">XOF (CFA)</option>
              <option value="XAF">XAF (FCFA)</option>
            </select>
          </div>
        </div>

        <div className="payment-methods">
          <h2>Sélectionnez votre mode de paiement</h2>
          
          <div className="payment-methods-grid">
            {PAYMENT_METHODS.map((method) => (
              <div
                key={method.value}
                className={`payment-method-card ${selectedMethod === method.value ? 'selected' : ''} ${!method.available ? 'disabled' : ''}`}
                onClick={() => method.available && handlePaymentMethodSelect(method.value)}
              >
                <div className="method-icon">{method.icon}</div>
                <div className="method-info">
                  <h3>{method.label}</h3>
                  <p>{method.description}</p>
                </div>
                {selectedMethod === method.value && (
                  <div className="method-check">✓</div>
                )}
              </div>
            ))}
          </div>

          {/* Champs spécifiques selon le mode de paiement */}
          {selectedMethod && (
            <div className="payment-method-details">
              {selectedMethod.startsWith('mobile_money_') && (
                <div className="form-group">
                  <label htmlFor="mobile-money-number">
                    Numéro de téléphone Mobile Money *
                  </label>
                  <input
                    type="tel"
                    id="mobile-money-number"
                    value={mobileMoneyNumber}
                    onChange={(e) => setMobileMoneyNumber(e.target.value)}
                    placeholder="Ex: +225 07 12 34 56 78"
                    className="form-control"
                  />
                </div>
              )}

              {selectedMethod === 'paiement_differe' && (
                <div className="enterprise-form">
                  <h3>Informations entreprise</h3>
                  <div className="form-group">
                    <label htmlFor="enterprise-name">Nom de l'entreprise *</label>
                    <input
                      type="text"
                      id="enterprise-name"
                      value={enterpriseName}
                      onChange={(e) => setEnterpriseName(e.target.value)}
                      className="form-control"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="enterprise-email">Email de facturation *</label>
                    <input
                      type="email"
                      id="enterprise-email"
                      value={enterpriseEmail}
                      onChange={(e) => setEnterpriseEmail(e.target.value)}
                      className="form-control"
                      required
                    />
                  </div>
                  <p className="info-text">
                    Une facture sera envoyée à cette adresse email. Le paiement devra être effectué dans les 30 jours.
                  </p>
                </div>
              )}

              {selectedMethod === 'virement' && (
                <div className="bank-transfer-info">
                  <h3>Informations pour le virement</h3>
                  <div className="bank-details">
                    <p><strong>Banque:</strong> [Nom de la banque]</p>
                    <p><strong>IBAN:</strong> [IBAN]</p>
                    <p><strong>BIC/SWIFT:</strong> [BIC]</p>
                    <p><strong>Référence:</strong> {subscription.numero_souscription}</p>
                    <p className="info-text">
                      Veuillez utiliser le numéro de souscription comme référence lors du virement.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="payment-actions">
            <button
              onClick={() => navigate(-1)}
              className="btn-secondary"
              disabled={initiatePaymentMutation.isPending}
            >
              Retour
            </button>
            <button
              onClick={handleInitiatePayment}
              className="btn-primary"
              disabled={!selectedMethod || initiatePaymentMutation.isPending}
            >
              {initiatePaymentMutation.isPending ? 'Traitement...' : 'Procéder au paiement'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

