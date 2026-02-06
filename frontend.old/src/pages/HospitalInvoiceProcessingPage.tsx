import { FormEvent, useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { hospitalSinistresApi } from '../api/hospitalSinistres'
import { hospitalsApi, type ExamTarifPayload, type MedicalTarifPayload } from '../api/hospitals'
import type { HospitalMedicalCatalog, HospitalStay } from '../types'
import './HospitalInvoiceProcessingPage.css'

const DEFAULT_TVA = 0.18
const HOURLY_RATE = 15000
const DEFAULT_ACT_PRICE = 20000
const DEFAULT_EXAM_PRICE = 15000

const ACT_PRICES: Record<string, number> = {
  'Consultation médicale': 25000,
  'Stabilisation des fonctions vitales': 40000,
  "Pose d'une perfusion": 18000,
  "Administration de médicaments": 15000,
  Injection: 12000,
  'Immobilisation / plâtre': 35000,
  'Suture / pansement': 22000,
  'Surveillance post-opératoire': 30000,
}

const EXAM_PRICES: Record<string, number> = {
  'Analyse sanguine': 20000,
  'Analyse urinaire': 8000,
  Radiographie: 28000,
  Scanner: 60000,
  IRM: 85000,
  ECG: 18000,
  Échographie: 32000,
  'Test COVID / grippe': 15000,
}

type MedicalPricingCatalog = {
  hourlyRate: number
  defaultActPrice: number
  defaultExamPrice: number
  actPrices: Record<string, number>
  examPrices: Record<string, number>
}

const DEFAULT_PRICING: MedicalPricingCatalog = {
  hourlyRate: HOURLY_RATE,
  defaultActPrice: DEFAULT_ACT_PRICE,
  defaultExamPrice: DEFAULT_EXAM_PRICE,
  actPrices: { ...ACT_PRICES },
  examPrices: { ...EXAM_PRICES },
}

type InvoiceLine = {
  key: string
  label: string
  quantity: number
  unitPrice: number
  total: number
}

type BaseInvoiceLine = {
  label: string
  quantity: number
  unitPrice: number
  source: 'report' | 'manual'
  category: 'duration' | 'act' | 'exam' | 'custom'
}

type InvoiceDraftLine = BaseInvoiceLine & { id: string }

type InvoicePreview = {
  lines: InvoiceLine[]
  subtotal: number
  vatAmount: number
  total: number
}

const numberFormatter = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'XOF',
  maximumFractionDigits: 0,
})

const fallbackTags = (list?: string[] | null, emptyLabel = 'Aucun élément renseigné') =>
  Array.isArray(list) && list.length ? list : [emptyLabel]

const sanitizeQuantity = (value: number, fallback = 1) => {
  if (!Number.isFinite(value) || value <= 0) {
    const safeFallback = Number.isFinite(fallback) && fallback > 0 ? fallback : 1
    return Math.max(1, Math.round(safeFallback))
  }
  return Math.max(1, Math.round(value))
}

const sanitizeAmount = (value: number, fallback = 0) => {
  if (!Number.isFinite(value) || value < 0) {
    const safeFallback = Number.isFinite(fallback) && fallback >= 0 ? fallback : 0
    return Math.round(safeFallback)
  }
  return Math.round(value)
}

const resolveActPrice = (name: string, pricing: MedicalPricingCatalog) =>
  pricing.actPrices[name] ?? ACT_PRICES[name] ?? pricing.defaultActPrice ?? DEFAULT_PRICING.defaultActPrice

const resolveExamPrice = (name: string, pricing: MedicalPricingCatalog) =>
  pricing.examPrices[name] ?? EXAM_PRICES[name] ?? pricing.defaultExamPrice ?? DEFAULT_PRICING.defaultExamPrice

const buildDefaultInvoiceLineData = (stay: HospitalStay, pricing: MedicalPricingCatalog): BaseInvoiceLine[] => {
  const lines: BaseInvoiceLine[] = []
  const hours = Number(stay.report_duree_sejour_heures) || 0
  if (hours > 0) {
    lines.push({
      label: `Durée de séjour (${hours}h)`,
      quantity: hours,
      unitPrice: pricing.hourlyRate || DEFAULT_PRICING.hourlyRate,
      source: 'report',
      category: 'duration',
    })
  }

  const actes = Array.isArray(stay.report_actes) ? stay.report_actes : []
  actes.forEach((act) => {
    lines.push({
      label: `Acte - ${act}`,
      quantity: 1,
      unitPrice: resolveActPrice(act, pricing),
      source: 'report',
      category: 'act',
    })
  })

  const examens = Array.isArray(stay.report_examens) ? stay.report_examens : []
  examens.forEach((exam) => {
    lines.push({
      label: `Examen - ${exam}`,
      quantity: 1,
      unitPrice: resolveExamPrice(exam, pricing),
      source: 'report',
      category: 'exam',
    })
  })

  return lines
}

const normalizeInvoiceLines = (lines: Array<BaseInvoiceLine | InvoiceDraftLine>): InvoiceLine[] =>
  lines
    .map((line, index) => {
      const label = line.label?.trim()
      if (!label) {
        return null
      }
      const quantity = sanitizeQuantity(line.quantity)
      const unitPrice = sanitizeAmount(line.unitPrice)
      return {
        key: (line as InvoiceDraftLine).id || `${line.category}-${index}`,
        label,
        quantity,
        unitPrice,
        total: quantity * unitPrice,
      }
    })
    .filter(Boolean) as InvoiceLine[]

const getInvoiceLineBadgeLabel = (line: BaseInvoiceLine | InvoiceDraftLine) => {
  if (line.source !== 'report') {
    return ''
  }
  switch (line.category) {
    case 'duration':
      return 'Durée du séjour'
    case 'act':
      return 'Acte du rapport'
    case 'exam':
      return 'Examen du rapport'
    default:
      return 'Rapport'
  }
}

function buildInvoicePreview(
  stay: HospitalStay | null,
  tauxTva: number,
  pricing: MedicalPricingCatalog,
  overrideLines?: Array<BaseInvoiceLine | InvoiceDraftLine>,
): InvoicePreview {
  if (!stay && !overrideLines?.length) {
    return { lines: [], subtotal: 0, vatAmount: 0, total: 0 }
  }

  const baseLines =
    overrideLines && overrideLines.length
      ? overrideLines
      : stay
        ? buildDefaultInvoiceLineData(stay, pricing)
        : []

  const lines = normalizeInvoiceLines(baseLines)
  const subtotal = lines.reduce((sum, line) => sum + line.total, 0)
  const safeTva = Number.isFinite(tauxTva) ? Math.min(1, Math.max(0, tauxTva)) : DEFAULT_TVA
  const vatAmount = Math.round(subtotal * safeTva)
  const total = subtotal + vatAmount

  return { lines, subtotal, vatAmount, total }
}

const statusLabels: Record<string, string> = {
  in_progress: 'En cours',
  awaiting_validation: 'En attente de validation',
  validated: 'Validé',
  invoiced: 'Facturé',
  rejected: 'Rejeté',
}

const invoiceStatusLabels: Record<string, string> = {
  pending_medical: 'En attente accord médical',
  pending_sinistre: 'En attente validation sinistre',
  pending_compta: 'En attente comptabilité MH',
  validated: 'Validée',
  rejected: 'Rejetée',
}

const invoiceValidationStages = [
  {
    key: 'validation_medicale' as const,
    label: 'Pôle médical',
    approvedLabel: 'Accord médical',
    rejectedLabel: 'Refus médical',
    pendingLabel: 'En attente',
  },
  {
    key: 'validation_sinistre' as const,
    label: 'Pôle sinistre',
    approvedLabel: 'Bon pour paiement',
    rejectedLabel: 'Refus paiement',
    pendingLabel: 'En attente',
  },
  {
    key: 'validation_compta' as const,
    label: 'Comptabilité MH',
    approvedLabel: 'Paiement validé',
    rejectedLabel: 'Blocage comptable',
    pendingLabel: 'En attente',
  },
] as const

type InvoiceValidationStageKey = typeof invoiceValidationStages[number]['key']

const validationStatusLabels: Record<string, string> = {
  approved: 'Validé',
  pending: 'En attente',
  rejected: 'Rejeté',
}

const reportStatusLabels: Record<string, string> = {
  draft: 'Brouillon',
  submitted: 'Soumis',
  approved: 'Validé',
  rejected: 'Rejeté',
}

export default function HospitalInvoiceProcessingPage() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<'validated' | 'awaiting_validation' | 'in_progress' | 'all'>('validated')
  const [reportFilter, setReportFilter] = useState<'approved' | 'submitted' | 'all'>('approved')
  const [invoiceFilter, setInvoiceFilter] = useState<
    'none' | 'pending_medical' | 'pending_sinistre' | 'pending_compta' | 'validated' | 'rejected' | 'all'
  >('none')
  const [searchInput, setSearchInput] = useState('')
  const deferredSearch = useDeferredValue(searchInput)

  const [selectedStayId, setSelectedStayId] = useState<number | null>(null)
  const [tauxTva, setTauxTva] = useState(DEFAULT_TVA)
  const [notes, setNotes] = useState('')
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [actForm, setActForm] = useState({ nom: '', montant: '' })
  const [examForm, setExamForm] = useState({ nom: '', montant: '' })
  const [catalogFeedback, setCatalogFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [actDeletingId, setActDeletingId] = useState<number | null>(null)
  const [examDeletingId, setExamDeletingId] = useState<number | null>(null)
  const [invoiceLines, setInvoiceLines] = useState<InvoiceDraftLine[]>([])
  const lineCounterRef = useRef(0)
  const nextLineId = () => {
    lineCounterRef.current += 1
    return `line-${lineCounterRef.current}`
  }

  const filters = useMemo(
    () => ({
      status: statusFilter === 'all' ? undefined : statusFilter,
      report_status: reportFilter === 'all' ? undefined : reportFilter,
      invoice_status: invoiceFilter === 'all' ? undefined : invoiceFilter,
      search: deferredSearch.trim() ? deferredSearch.trim() : undefined,
      limit: 100,
    }),
    [deferredSearch, invoiceFilter, reportFilter, statusFilter],
  )

  const { data: stays = [], isLoading, isFetching } = useQuery({
    queryKey: ['hospital-stays', filters],
    queryFn: () => hospitalSinistresApi.getHospitalStays(filters),
    staleTime: 15_000,
  })

  const catalogQuery = useQuery({
    queryKey: catalogQueryKey,
    queryFn: () => {
      if (!hospitalId) {
        return Promise.resolve(null)
      }
      return hospitalsApi.getMedicalCatalog(hospitalId)
    },
    enabled: Boolean(hospitalId),
    staleTime: 30_000,
  })
  const medicalCatalog = hospitalId ? ((catalogQuery.data as HospitalMedicalCatalog | null) ?? null) : null
  const pricing = useMemo<MedicalPricingCatalog>(() => {
    const actPrices = { ...ACT_PRICES }
    const examPrices = { ...EXAM_PRICES }
    if (!medicalCatalog) {
      return {
        ...DEFAULT_PRICING,
        actPrices,
        examPrices,
      }
    }
    medicalCatalog.actes.forEach((act) => {
      actPrices[act.nom] = act.montant
    })
    medicalCatalog.examens.forEach((exam) => {
      examPrices[exam.nom] = exam.montant
    })
    return {
      hourlyRate: medicalCatalog.defaults?.hourly_rate || DEFAULT_PRICING.hourlyRate,
      defaultActPrice: medicalCatalog.defaults?.default_act_price || DEFAULT_PRICING.defaultActPrice,
      defaultExamPrice: medicalCatalog.defaults?.default_exam_price || DEFAULT_PRICING.defaultExamPrice,
      actPrices,
      examPrices,
    }
  }, [medicalCatalog])

  useEffect(() => {
    if (!stays.length) {
      setSelectedStayId(null)
      return
    }
    if (!selectedStayId || !stays.some((stay) => stay.id === selectedStayId)) {
      setSelectedStayId(stays[0].id)
    }
  }, [stays, selectedStayId])

  const selectedStay = stays.find((stay) => stay.id === selectedStayId) ?? null
  const hospitalId = selectedStay?.hospital_id ?? (stays.length ? stays[0].hospital_id : null)
  const catalogQueryKey = ['hospital-medical-catalog', hospitalId ?? 'none'] as const

  useEffect(() => {
    setTauxTva(DEFAULT_TVA)
    setNotes('')
    setFeedback(null)
  }, [selectedStayId])

  useEffect(() => {
    setActForm({ nom: '', montant: '' })
    setExamForm({ nom: '', montant: '' })
    setCatalogFeedback(null)
    setActDeletingId(null)
    setExamDeletingId(null)
  }, [hospitalId])

useEffect(() => {
  if (!selectedStay) {
    setInvoiceLines([])
    return
  }
  lineCounterRef.current = 0
  const defaults = buildDefaultInvoiceLineData(selectedStay, pricing).map((line) => ({
    ...line,
    id: nextLineId(),
  }))
  setInvoiceLines(defaults)
}, [selectedStay?.id, pricing])

  const invoicePreview = useMemo(
  () => buildInvoicePreview(selectedStay, tauxTva, pricing, invoiceLines),
  [selectedStay, tauxTva, pricing, invoiceLines],
  )

  const mutation = useMutation({
    mutationFn: (payload: { stayId: number; notes?: string; taux_tva: number; lines: InvoiceLine[] }) =>
      hospitalSinistresApi.createInvoice(payload.stayId, {
        notes: payload.notes,
        taux_tva: payload.taux_tva,
        lines: payload.lines.map((line) => ({
          libelle: line.label.trim(),
          quantite: line.quantity,
          prix_unitaire: line.unitPrice,
        })),
      }),
    onSuccess: () => {
      setFeedback({
        type: 'success',
        message: 'Facture générée avec succès. Elle est transmise au pôle médical pour accord.',
      })
      queryClient.invalidateQueries({ queryKey: ['hospital-stays'] })
      if (invoiceFilter === 'none') {
        setSelectedStayId(null)
      }
    },
    onError: (error: any) => {
      const apiMessage = error?.response?.data?.detail
      setFeedback({
        type: 'error',
        message: apiMessage || "La génération de la facture a échoué. Merci d'essayer à nouveau.",
      })
    },
  })

  const invalidateCatalog = () => {
    if (!hospitalId) {
      return
    }
    queryClient.invalidateQueries({ queryKey: catalogQueryKey })
  }

  const createActMutation = useMutation({
    mutationFn: (payload: MedicalTarifPayload) => {
      if (!hospitalId) {
        throw new Error("Aucun hôpital associé")
      }
      return hospitalsApi.createMedicalAct(hospitalId, payload)
    },
    onSuccess: () => {
      setCatalogFeedback({
        type: 'success',
        message: 'Acte médical enregistré.',
      })
      setActForm({ nom: '', montant: '' })
      invalidateCatalog()
    },
    onError: (error: any) => {
      const apiMessage = error?.response?.data?.detail
      setCatalogFeedback({
        type: 'error',
        message: apiMessage || "Impossible d'enregistrer l'acte. Merci de réessayer.",
      })
    },
  })

  const deleteActMutation = useMutation({
    mutationFn: (actId: number) => {
      if (!hospitalId) {
        throw new Error("Aucun hôpital associé")
      }
      return hospitalsApi.deleteMedicalAct(hospitalId, actId)
    },
    onSuccess: () => {
      setCatalogFeedback({
        type: 'success',
        message: 'Acte supprimé.',
      })
      invalidateCatalog()
    },
    onError: (error: any) => {
      const apiMessage = error?.response?.data?.detail
      setCatalogFeedback({
        type: 'error',
        message: apiMessage || "Impossible de supprimer l'acte. Merci de réessayer.",
      })
    },
    onSettled: () => {
      setActDeletingId(null)
    },
  })

  const createExamMutation = useMutation({
    mutationFn: (payload: ExamTarifPayload) => {
      if (!hospitalId) {
        throw new Error("Aucun hôpital associé")
      }
      return hospitalsApi.createMedicalExam(hospitalId, payload)
    },
    onSuccess: () => {
      setCatalogFeedback({
        type: 'success',
        message: 'Examen enregistré.',
      })
      setExamForm({ nom: '', montant: '' })
      invalidateCatalog()
    },
    onError: (error: any) => {
      const apiMessage = error?.response?.data?.detail
      setCatalogFeedback({
        type: 'error',
        message: apiMessage || "Impossible d'enregistrer l'examen. Merci de réessayer.",
      })
    },
  })

  const deleteExamMutation = useMutation({
    mutationFn: (examId: number) => {
      if (!hospitalId) {
        throw new Error("Aucun hôpital associé")
      }
      return hospitalsApi.deleteMedicalExam(hospitalId, examId)
    },
    onSuccess: () => {
      setCatalogFeedback({
        type: 'success',
        message: 'Examen supprimé.',
      })
      invalidateCatalog()
    },
    onError: (error: any) => {
      const apiMessage = error?.response?.data?.detail
      setCatalogFeedback({
        type: 'error',
        message: apiMessage || "Impossible de supprimer l'examen. Merci de réessayer.",
      })
    },
    onSettled: () => {
      setExamDeletingId(null)
    },
  })

  const canGenerateInvoice = Boolean(
    selectedStay && !selectedStay.invoice && invoicePreview.lines.length && !mutation.isPending,
  )

  const staysWithoutInvoice = stays.filter((stay) => !stay.invoice).length
  const totalPotential = stays.reduce(
    (sum, stay) => sum + buildInvoicePreview(stay, DEFAULT_TVA, pricing).subtotal,
    0,
  )
  const isActFormValid = Boolean(actForm.nom.trim()) && Number(actForm.montant) > 0
  const isExamFormValid = Boolean(examForm.nom.trim()) && Number(examForm.montant) > 0
  const isCatalogLoading = catalogQuery.isLoading && Boolean(hospitalId)
  const isCatalogRefreshing = catalogQuery.isFetching && !catalogQuery.isLoading && Boolean(hospitalId)
  const catalogError = catalogQuery.error as any
  const canEditInvoice = Boolean(selectedStay && !selectedStay.invoice)
  const invoiceHelperText = !selectedStay
    ? 'Sélectionnez un séjour validé pour préparer la facture.'
    : selectedStay.invoice
      ? 'Facture déjà envoyée : modifications désactivées.'
      : "Ajustez librement les libellés, quantités et montants avant l'envoi de la facture."

  const handleCreateAct = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!hospitalId || !isActFormValid || createActMutation.isPending) {
      return
    }
    setCatalogFeedback(null)
    createActMutation.mutate({
      nom: actForm.nom.trim(),
      montant: Number(actForm.montant),
    })
  }

  const handleCreateExam = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!hospitalId || !isExamFormValid || createExamMutation.isPending) {
      return
    }
    setCatalogFeedback(null)
    createExamMutation.mutate({
      nom: examForm.nom.trim(),
      montant: Number(examForm.montant),
    })
  }

  const handleDeleteAct = (actId: number) => {
    if (!hospitalId || deleteActMutation.isPending) {
      return
    }
    setCatalogFeedback(null)
    setActDeletingId(actId)
    deleteActMutation.mutate(actId)
  }

  const handleDeleteExam = (examId: number) => {
    if (!hospitalId || deleteExamMutation.isPending) {
      return
    }
    setCatalogFeedback(null)
    setExamDeletingId(examId)
    deleteExamMutation.mutate(examId)
  }

  const handleAddInvoiceLine = () => {
    if (!canEditInvoice) {
      return
    }
    setInvoiceLines((prev) => [
      ...prev,
      {
        id: nextLineId(),
        label: 'Nouvelle ligne',
        quantity: 1,
        unitPrice: pricing.defaultActPrice || DEFAULT_PRICING.defaultActPrice,
        source: 'manual',
        category: 'custom',
      },
    ])
  }

  const handleInvoiceLineChange = (lineId: string, field: 'label' | 'quantity' | 'unitPrice', value: string) => {
    if (!canEditInvoice) {
      return
    }
    setInvoiceLines((prev) =>
      prev.map((line) => {
        if (line.id !== lineId) {
          return line
        }
        if (field === 'label') {
          return { ...line, label: value }
        }
        const numericValue = Number(value)
        if (field === 'quantity') {
          return { ...line, quantity: Number.isNaN(numericValue) ? 0 : numericValue }
        }
        return { ...line, unitPrice: Number.isNaN(numericValue) ? 0 : numericValue }
      }),
    )
  }

  const handleRemoveInvoiceLine = (lineId: string) => {
    if (!canEditInvoice) {
      return
    }
    setInvoiceLines((prev) => prev.filter((line) => line.id !== lineId))
  }

  const handleResetInvoiceLines = () => {
    if (!selectedStay) {
      return
    }
    lineCounterRef.current = 0
    const defaults = buildDefaultInvoiceLineData(selectedStay, pricing).map((line) => ({
      ...line,
      id: nextLineId(),
    }))
    setInvoiceLines(defaults)
  }

  const handleGenerateInvoice = () => {
    if (!selectedStay) {
      return
    }
    if (!invoiceLines.length) {
      setFeedback({
        type: 'error',
        message: 'Ajoutez au moins une ligne de facture avant de générer.',
      })
      return
    }
    if (invoiceLines.some((line) => !line.label.trim())) {
      setFeedback({
        type: 'error',
        message: 'Complétez le libellé de chaque ligne de facture.',
      })
      return
    }
    if (
      invoiceLines.some(
        (line) =>
          !Number.isFinite(line.quantity) ||
          line.quantity <= 0 ||
          !Number.isFinite(line.unitPrice) ||
          line.unitPrice < 0,
      )
    ) {
      setFeedback({
        type: 'error',
        message: 'Vérifiez les quantités et montants indiqués pour chaque ligne.',
      })
      return
    }
    if (!invoicePreview.lines.length) {
      setFeedback({
        type: 'error',
        message: 'Ajoutez au moins une ligne valide avant de générer la facture.',
      })
      return
    }
    setFeedback(null)
    mutation.mutate({
      stayId: selectedStay.id,
      notes: notes || undefined,
      taux_tva: tauxTva,
      lines: invoicePreview.lines,
    })
  }

  return (
    <div className="hospital-invoice-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Comptabilité hospitalière</p>
          <h1>Traitement des factures</h1>
          <p className="subtitle">
            Vérifiez les éléments du rapport médical validé, ajustez le taux de TVA et générez la facture à transmettre au
            back-office Mobility Health.
          </p>
        </div>
        <div className="summary-cards">
          <div className="summary-card">
            <span className="summary-label">Séjours prêts à facturer</span>
            <strong className="summary-value">{staysWithoutInvoice}</strong>
          </div>
          <div className="summary-card">
            <span className="summary-label">Potentiel HT estimé</span>
            <strong className="summary-value">{numberFormatter.format(totalPotential)}</strong>
          </div>
        </div>
      </header>

      <section className="filters-panel">
        <div className="filter-group">
          <label htmlFor="statusFilter">Statut du séjour</label>
          <select
            id="statusFilter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
          >
            <option value="validated">Validés</option>
            <option value="awaiting_validation">En validation</option>
            <option value="in_progress">En cours</option>
            <option value="all">Tous</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="reportFilter">Rapport médical</label>
          <select
            id="reportFilter"
            value={reportFilter}
            onChange={(e) => setReportFilter(e.target.value as typeof reportFilter)}
          >
            <option value="approved">Validé</option>
            <option value="submitted">Soumis</option>
            <option value="all">Tous</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="invoiceFilter">Facture</label>
          <select
            id="invoiceFilter"
            value={invoiceFilter}
            onChange={(e) => setInvoiceFilter(e.target.value as typeof invoiceFilter)}
          >
            <option value="none">À générer</option>
            <option value="pending_medical">En attente accord médical</option>
            <option value="pending_sinistre">En attente pôle sinistre</option>
            <option value="pending_compta">En attente comptabilité MH</option>
            <option value="validated">Validées</option>
            <option value="rejected">Refusées</option>
            <option value="all">Toutes</option>
          </select>
        </div>
        <div className="filter-group search-group">
          <label htmlFor="searchStay">Recherche</label>
          <input
            id="searchStay"
            type="search"
            placeholder="Numéro de sinistre ou patient"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>
      </section>

      <section className="catalog-panel">
        <div className="catalog-header">
          <div>
            <p className="eyebrow">Catalogue médical</p>
            <h2>Actes & examens facturables</h2>
            <p className="subtitle">
              Définissez les tarifs de référence utilisés lors de la génération automatique des factures.
            </p>
          </div>
          <div className="catalog-meta">
            {hospitalId && <span className="pill pill-neutral">Hôpital #{hospitalId}</span>}
            {isCatalogRefreshing && <span className="pill">Actualisation...</span>}
          </div>
        </div>

        {!hospitalId ? (
          <div className="panel-empty">
            <p>Associez votre compte à un hôpital pour gérer le catalogue des actes et examens.</p>
          </div>
        ) : catalogQuery.isError ? (
          <div className="panel-empty">
            <p>Impossible de charger le catalogue médical.</p>
            <small>{catalogError?.response?.data?.detail || catalogError?.message || 'Erreur inconnue'}</small>
          </div>
        ) : (
          <>
            {catalogFeedback && (
              <div className={`feedback ${catalogFeedback.type}`}>
                <p>{catalogFeedback.message}</p>
              </div>
            )}
            <div className="catalog-grid">
              <div className="catalog-card">
                <div className="catalog-card-header">
                  <div>
                    <h3>Actes médicaux</h3>
                    <p className="catalog-subtitle">Montants appliqués pour chaque acte clinique</p>
                  </div>
                  <span className="pill">
                    {(medicalCatalog?.actes.length ?? 0).toString()} acte{(medicalCatalog?.actes.length ?? 0) > 1 ? 's' : ''}
                  </span>
                </div>
                {isCatalogLoading ? (
                  <div className="panel-empty">
                    <p>Chargement des actes...</p>
                  </div>
                ) : (
                  <>
                    <ul className="catalog-list">
                      {!medicalCatalog || medicalCatalog.actes.length === 0 ? (
                        <li className="catalog-empty">Aucun acte enregistré pour le moment.</li>
                      ) : (
                        medicalCatalog.actes.map((act) => (
                          <li key={act.id} className="catalog-item">
                            <div className="catalog-item-info">
                              <strong>{act.nom}</strong>
                              <span>{numberFormatter.format(act.montant)}</span>
                            </div>
                            <button
                              type="button"
                              className="catalog-delete"
                              onClick={() => handleDeleteAct(act.id)}
                              disabled={deleteActMutation.isPending && actDeletingId === act.id}
                            >
                              {deleteActMutation.isPending && actDeletingId === act.id ? 'Suppression...' : 'Supprimer'}
                            </button>
                          </li>
                        ))
                      )}
                    </ul>
                    <form className="catalog-form" onSubmit={handleCreateAct}>
                      <div className="catalog-form-row">
                        <input
                          type="text"
                          placeholder="Libellé de l'acte"
                          value={actForm.nom}
                          onChange={(e) => setActForm((prev) => ({ ...prev, nom: e.target.value }))}
                        />
                        <input
                          type="number"
                          min="0"
                          step="1000"
                          placeholder="Montant (XOF)"
                          value={actForm.montant}
                          onChange={(e) => setActForm((prev) => ({ ...prev, montant: e.target.value }))}
                        />
                      </div>
                      <button type="submit" disabled={!isActFormValid || createActMutation.isPending}>
                        {createActMutation.isPending ? 'Ajout en cours...' : 'Ajouter un acte'}
                      </button>
                    </form>
                  </>
                )}
              </div>

              <div className="catalog-card">
                <div className="catalog-card-header">
                  <div>
                    <h3>Examens</h3>
                    <p className="catalog-subtitle">Tarifs appliqués aux examens et analyses</p>
                  </div>
                  <span className="pill">
                    {(medicalCatalog?.examens.length ?? 0).toString()} examen
                    {(medicalCatalog?.examens.length ?? 0) > 1 ? 's' : ''}
                  </span>
                </div>
                {isCatalogLoading ? (
                  <div className="panel-empty">
                    <p>Chargement des examens...</p>
                  </div>
                ) : (
                  <>
                    <ul className="catalog-list">
                      {!medicalCatalog || medicalCatalog.examens.length === 0 ? (
                        <li className="catalog-empty">Aucun examen enregistré pour le moment.</li>
                      ) : (
                        medicalCatalog.examens.map((exam) => (
                          <li key={exam.id} className="catalog-item">
                            <div className="catalog-item-info">
                              <strong>{exam.nom}</strong>
                              <span>{numberFormatter.format(exam.montant)}</span>
                            </div>
                            <button
                              type="button"
                              className="catalog-delete"
                              onClick={() => handleDeleteExam(exam.id)}
                              disabled={deleteExamMutation.isPending && examDeletingId === exam.id}
                            >
                              {deleteExamMutation.isPending && examDeletingId === exam.id
                                ? 'Suppression...'
                                : 'Supprimer'}
                            </button>
                          </li>
                        ))
                      )}
                    </ul>
                    <form className="catalog-form" onSubmit={handleCreateExam}>
                      <div className="catalog-form-row">
                        <input
                          type="text"
                          placeholder="Libellé de l'examen"
                          value={examForm.nom}
                          onChange={(e) => setExamForm((prev) => ({ ...prev, nom: e.target.value }))}
                        />
                        <input
                          type="number"
                          min="0"
                          step="1000"
                          placeholder="Montant (XOF)"
                          value={examForm.montant}
                          onChange={(e) => setExamForm((prev) => ({ ...prev, montant: e.target.value }))}
                        />
                      </div>
                      <button type="submit" disabled={!isExamFormValid || createExamMutation.isPending}>
                        {createExamMutation.isPending ? 'Ajout en cours...' : 'Ajouter un examen'}
                      </button>
                    </form>
                  </>
                )}
              </div>
            </div>
          </>
        )}
      </section>

      <div className="content-grid">
        <section className="stays-panel">
          <div className="panel-header">
            <h2>Séjours hospitaliers</h2>
            {isFetching && <span className="pill">Actualisation...</span>}
          </div>
          {isLoading ? (
            <div className="panel-empty">Chargement des séjours...</div>
          ) : stays.length === 0 ? (
            <div className="panel-empty">
              <p>Aucun séjour ne correspond aux filtres actuels.</p>
              <small>Vérifiez le statut sélectionné ou élargissez votre recherche.</small>
            </div>
          ) : (
            <ul className="stay-list">
              {stays.map((stay) => (
                <li
                  key={stay.id}
                  className={`stay-card ${selectedStayId === stay.id ? 'selected' : ''}`}
                  onClick={() => setSelectedStayId(stay.id)}
                >
                  <div className="stay-card-header">
                    <strong>{stay.sinistre?.numero_sinistre || `Sinistre #${stay.sinistre_id}`}</strong>
                    <span className={`status-badge status-${stay.status}`}>
                      {statusLabels[stay.status] || stay.status}
                    </span>
                  </div>
                  <div className="stay-card-body">
                    <p className="muted">
                      Rapport&nbsp;: {reportStatusLabels[stay.report_status ?? ''] || 'Non communiqué'}
                    </p>
                    {stay.assigned_doctor?.full_name && (
                      <p className="muted">Médecin : {stay.assigned_doctor.full_name}</p>
                    )}
                  </div>
                  <div className="stay-card-footer">
                    {stay.invoice ? (
                      <span className="pill pill-success">
                        Facture #{stay.invoice.numero_facture} ·{' '}
                        {invoiceStatusLabels[stay.invoice.statut] || stay.invoice.statut}
                      </span>
                    ) : (
                      <span className="pill">Facture à créer</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="details-panel">
          {!selectedStay ? (
            <div className="panel-empty">
              <p>Sélectionnez un séjour pour vérifier le rapport et préparer la facture.</p>
            </div>
          ) : (
            <>
              <div className="details-header">
                <div>
                  <p className="eyebrow">Sinistre</p>
                  <h2>{selectedStay.sinistre?.numero_sinistre || `#${selectedStay.sinistre_id}`}</h2>
                  <p className="muted">
                    Rapport{' '}
                    <strong>{reportStatusLabels[selectedStay.report_status ?? ''] || selectedStay.report_status}</strong>
                    {selectedStay.patient?.full_name && (
                      <>
                        {' '}
                        · Patient {selectedStay.patient.full_name}
                      </>
                    )}
                  </p>
                </div>
                <div className="status-stack">
                  <span className={`status-badge status-${selectedStay.status}`}>
                    {statusLabels[selectedStay.status] || selectedStay.status}
                  </span>
                  {selectedStay.invoice && (
                    <span className="status-badge status-invoiced">
                      Facture #{selectedStay.invoice.numero_facture}
                    </span>
                  )}
                </div>
              </div>

              <div className="report-section">
                <div>
                  <h3>Résumé médical</h3>
                  <dl className="report-grid">
                    <div>
                      <dt>Motif de consultation</dt>
                      <dd>{selectedStay.report_motif_consultation || 'Non renseigné'}</dd>
                    </div>
                    <div>
                      <dt>Motif d’hospitalisation</dt>
                      <dd>{selectedStay.report_motif_hospitalisation || 'Non renseigné'}</dd>
                    </div>
                    <div>
                      <dt>Durée du séjour</dt>
                      <dd>{selectedStay.report_duree_sejour_heures ? `${selectedStay.report_duree_sejour_heures} h` : '—'}</dd>
                    </div>
                    <div>
                      <dt>Médecin référent</dt>
                      <dd>{selectedStay.assigned_doctor?.full_name || '—'}</dd>
                    </div>
                  </dl>
                  {selectedStay.report_resume && (
                    <div className="rich-card">
                      <p className="muted">Résumé</p>
                      <p>{selectedStay.report_resume}</p>
                    </div>
                  )}
                </div>

                <div className="tags-grid">
                  <div>
                    <h4>Actes réalisés</h4>
                    <div className="tags-container">
                      {fallbackTags(selectedStay.report_actes, 'Aucun acte renseigné').map((act, index) => (
                        <span key={`${act}-${index}`} className="tag">
                          {act}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h4>Examens effectués</h4>
                    <div className="tags-container">
                      {fallbackTags(selectedStay.report_examens, 'Aucun examen renseigné').map((exam, index) => (
                        <span key={`${exam}-${index}`} className="tag">
                          {exam}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="invoice-section">
                <div className="invoice-header">
                  <div>
                    <h3>Prévisualisation de la facture</h3>
                    <p className="muted">
                      Les montants sont calculés automatiquement à partir du rapport validé et suivent ensuite le circuit
                      d’accord médical &amp; sinistre.
                    </p>
                  </div>
                  <div className="tva-inputs">
                    <label htmlFor="tvaRate">TVA</label>
                    <input
                      id="tvaRate"
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={tauxTva}
                      onChange={(e) => {
                        const value = Number(e.target.value)
                        if (Number.isNaN(value)) return
                        setTauxTva(Math.min(1, Math.max(0, value)))
                      }}
                    />
                    <span className="tva-hint">{(tauxTva * 100).toFixed(0)}%</span>
                  </div>
                </div>

                <div className="invoice-builder-toolbar">
                  <div className="builder-actions">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={handleAddInvoiceLine}
                      disabled={!canEditInvoice}
                    >
                      Ajouter une ligne libre
                    </button>
                    <button
                      type="button"
                      className="ghost-button"
                      onClick={handleResetInvoiceLines}
                      disabled={!canEditInvoice}
                    >
                      Recharger le rapport
                    </button>
                  </div>
                  <p className="muted helper-text">{invoiceHelperText}</p>
                </div>

                {invoiceLines.length === 0 ? (
                  <div className="panel-empty">
                    <p>Aucune ligne n'est définie. Ajoutez une ligne libre ou rechargez les éléments du rapport médical.</p>
                  </div>
                ) : (
                  <table className="invoice-table">
                    <thead>
                      <tr>
                        <th>Libellé</th>
                        <th>Quantité</th>
                        <th>PU (HT)</th>
                        <th>Montant (HT)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoiceLines.map((line) => {
                        const badge = getInvoiceLineBadgeLabel(line)
                        const safeQuantity = sanitizeQuantity(line.quantity, 1)
                        const safePrice = sanitizeAmount(line.unitPrice, 0)
                        const totalValue = numberFormatter.format(safeQuantity * safePrice)
                        return (
                          <tr key={line.id}>
                            <td>
                              <input
                                type="text"
                                className="invoice-line-input line-label-input"
                                value={line.label}
                                placeholder="Libellé de la ligne"
                                disabled={!canEditInvoice}
                                onChange={(e) => handleInvoiceLineChange(line.id, 'label', e.target.value)}
                              />
                              {badge && <small className="invoice-line-badge">{badge}</small>}
                            </td>
                            <td>
                              <input
                                type="number"
                                min={1}
                                step={1}
                                className="invoice-line-input line-qty-input"
                                value={line.quantity}
                                disabled={!canEditInvoice}
                                onChange={(e) => handleInvoiceLineChange(line.id, 'quantity', e.target.value)}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                min={0}
                                step={100}
                                className="invoice-line-input line-price-input"
                                value={line.unitPrice}
                                disabled={!canEditInvoice}
                                onChange={(e) => handleInvoiceLineChange(line.id, 'unitPrice', e.target.value)}
                              />
                            </td>
                            <td>
                              <div className="line-total-cell">
                                <span className="line-total-value">{totalValue}</span>
                                <button
                                  type="button"
                                  className="icon-button"
                                  aria-label="Supprimer la ligne"
                                  onClick={() => handleRemoveInvoiceLine(line.id)}
                                  disabled={!canEditInvoice}
                                >
                                  &times;
                                </button>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td colSpan={3}>Montant HT</td>
                        <td>{numberFormatter.format(invoicePreview.subtotal)}</td>
                      </tr>
                      <tr>
                        <td colSpan={3}>TVA ({(tauxTva * 100).toFixed(0)}%)</td>
                        <td>{numberFormatter.format(invoicePreview.vatAmount)}</td>
                      </tr>
                      <tr>
                        <td colSpan={3}>
                          <strong>Total TTC</strong>
                        </td>
                        <td>
                          <strong>{numberFormatter.format(invoicePreview.total)}</strong>
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                )}

                <div className="notes-field">
                  <label htmlFor="invoiceNotes">Notes internes (optionnel)</label>
                  <textarea
                    id="invoiceNotes"
                    placeholder="Ajouter une précision pour le back-office Mobility Health..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </div>

                {feedback && (
                  <div className={`feedback ${feedback.type}`}>
                    <p>{feedback.message}</p>
                  </div>
                )}

                {selectedStay.invoice && (
                  <div className="invoice-validation-card">
                    <h4>Suivi des validations</h4>
                    <ul className="validation-list">
                      {invoiceValidationStages.map((stage) => {
                        const status = selectedStay.invoice?.[stage.key] as string | undefined
                        const label =
                          status === 'approved'
                            ? stage.approvedLabel
                            : status === 'rejected'
                              ? stage.rejectedLabel
                              : stage.pendingLabel
                        const statusClass = status ? `validation-${status}` : 'validation-pending'
                        return (
                          <li key={stage.key}>
                            <span>{stage.label}</span>
                            <span className={`validation-pill ${statusClass}`}>
                              {label} · {validationStatusLabels[status || 'pending']}
                            </span>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                )}

                <button
                  type="button"
                  className="primary-button"
                  disabled={!canGenerateInvoice}
                  onClick={handleGenerateInvoice}
                >
                  {mutation.isPending ? 'Création de la facture...' : 'Générer la facture'}
                </button>
                {selectedStay.invoice && (
                  <p className="muted invoice-info">
                    Facture #{selectedStay.invoice.numero_facture} ·{' '}
                    {invoiceStatusLabels[selectedStay.invoice.statut] || selectedStay.invoice.statut}
                  </p>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}

