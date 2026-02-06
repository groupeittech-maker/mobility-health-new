import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { assureursApi } from '../api/assureurs'
import { ProduitAssurance, CleRepartition, Currency, Garantie, ZonesGeographiques, CategorieAssure, Assureur } from '../types'
import './ProductForm.css'

interface ProductFormProps {
  product?: ProduitAssurance
  onSubmit: (data: Partial<ProduitAssurance>) => void
  onCancel: () => void
  currency: Currency
}

const CLE_REPARTITION_OPTIONS: { value: CleRepartition; label: string }[] = [
  { value: 'par_personne', label: 'Par personne' },
  { value: 'par_groupe', label: 'Par groupe' },
  { value: 'par_duree', label: 'Par durée' },
  { value: 'par_destination', label: 'Par destination' },
  { value: 'fixe', label: 'Fixe' },
]

const CATEGORIES_ASSURE_OPTIONS: { value: CategorieAssure; label: string }[] = [
  { value: 'individuel', label: 'Individuel' },
  { value: 'famille', label: 'Famille' },
  { value: 'groupe', label: 'Groupe' },
  { value: 'entreprise', label: 'Entreprise (Corporate)' },
]

const ZONES_OPTIONS = [
  'Afrique',
  'Europe',
  'Amérique',
  'Asie',
  'Océanie',
  'Monde',
  'Afrique Centrale',
  'Afrique de l\'Ouest',
  'Afrique du Nord',
  'Afrique de l\'Est',
  'Afrique Australe',
]

const GARANTIES_TYPES = [
  'Assistance médicale / Frais médicaux',
  'Hospitalisation',
  'Médicaments',
  'Soins d\'urgence',
  'Rapatriement sanitaire',
  'Organisation + Transport',
  'Responsabilité civile à l\'étranger',
  'Assurance bagages',
  'Perte, vol, retard',
  'Annulation / Interruption de voyage',
  'Décès / Invalidité accidentelle',
  'Assistance juridique',
  'Frais de retour anticipé',
  'Retour anticipé en cas de décès d\'un proche',
  'Assistance en cas de perte de documents',
]

const CURRENCY_SYMBOLS: Record<Currency, string> = {
  EUR: '€',
  USD: '$',
  XOF: 'CFA',
  XAF: 'FCFA',
}

export default function ProductForm({ product, onSubmit, onCancel, currency }: ProductFormProps) {
  // Parse garanties
  const parseGaranties = (garanties: any): Garantie[] => {
    if (!garanties) return []
    if (typeof garanties === 'string') {
      try {
        const parsed = JSON.parse(garanties)
        return Array.isArray(parsed) ? parsed : []
      } catch {
        return []
      }
    }
    if (Array.isArray(garanties)) {
      return garanties
    }
    return []
  }

  // Parse zones géographiques
  const parseZonesGeographiques = (zones: any): ZonesGeographiques => {
    if (!zones) return {}
    if (typeof zones === 'string') {
      try {
        return JSON.parse(zones)
      } catch {
        return {}
      }
    }
    return zones || {}
  }

  const [activeSection, setActiveSection] = useState<string>('general')
  const [formData, setFormData] = useState({
    // 1. Informations générales
    code: product?.code || '',
    nom: product?.nom || '',
    description: product?.description || '',
    version: product?.version || '',
    est_actif: product?.est_actif ?? true,
    assureur_id: product?.assureur_id ? String(product.assureur_id) : '',
    assureur: product?.assureur || '',
    image_url: product?.image_url || '',
    cout: product?.cout ? String(product.cout) : '',
    cle_repartition: (product?.cle_repartition as CleRepartition) || 'fixe',
    
    // 2. Zone géographique
    zones_geographiques: parseZonesGeographiques(product?.zones_geographiques),
    
    // 3. Durée du voyage
    duree_min_jours: product?.duree_min_jours ? String(product.duree_min_jours) : '',
    duree_max_jours: product?.duree_max_jours ? String(product.duree_max_jours) : '',
    duree_validite_jours: product?.duree_validite_jours ? String(product.duree_validite_jours) : '',
    reconduction_possible: product?.reconduction_possible ?? false,
    couverture_multi_entrees: product?.couverture_multi_entrees ?? false,
    
    // 4. Profil des assurés
    age_minimum: product?.age_minimum ? String(product.age_minimum) : '',
    age_maximum: product?.age_maximum ? String(product.age_maximum) : '',
    conditions_sante: product?.conditions_sante || '',
    categories_assures: product?.categories_assures || [] as CategorieAssure[],
    
    // 5. Garanties
    garanties: parseGaranties(product?.garanties),
    
    // 6. Exclusions générales
    exclusions_generales: product?.exclusions_generales || [] as string[],
    
    // Legacy
    conditions: product?.conditions || '',
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [newExclusion, setNewExclusion] = useState('')
  const [newPaysEligible, setNewPaysEligible] = useState('')
  const [newPaysExclus, setNewPaysExclus] = useState('')

  const {
    data: assureurs = [],
    isLoading: assureursLoading,
    isError: assureursError,
    error: assureursFetchError,
    refetch: refetchAssureurs,
  } = useQuery<Assureur[], Error>({
    queryKey: ['admin-assureurs'],
    queryFn: () => assureursApi.listAdmin(),
  })

  const selectedAssureur = assureurs.find((item) => String(item.id) === formData.assureur_id) || null
  const noAssureurAvailable = !assureursLoading && !assureursError && assureurs.length === 0

  // Gestion des garanties
  const addGarantie = () => {
    const newGarantie: Garantie = {
      id: Date.now().toString(),
      nom: '',
      description: '',
      devise: currency,
    }
    setFormData(prev => ({
      ...prev,
      garanties: [...prev.garanties, newGarantie],
    }))
  }

  const updateGarantie = (id: string, field: keyof Garantie, value: any) => {
    setFormData(prev => ({
      ...prev,
      garanties: prev.garanties.map(g =>
        g.id === id ? { ...g, [field]: value } : g
      ),
    }))
  }

  const removeGarantie = (id: string) => {
    setFormData(prev => ({
      ...prev,
      garanties: prev.garanties.filter(g => g.id !== id),
    }))
  }

  // Gestion des zones géographiques
  const toggleZone = (zone: string) => {
    setFormData(prev => {
      const zones = prev.zones_geographiques?.zones || []
      const newZones = zones.includes(zone)
        ? zones.filter(z => z !== zone)
        : [...zones, zone]
      return {
        ...prev,
        zones_geographiques: {
          ...prev.zones_geographiques,
          zones: newZones,
        },
      }
    })
  }

  const addPaysEligible = () => {
    if (!newPaysEligible.trim()) return
    setFormData(prev => ({
      ...prev,
      zones_geographiques: {
        ...prev.zones_geographiques,
        pays_eligibles: [...(prev.zones_geographiques?.pays_eligibles || []), newPaysEligible.trim()],
      },
    }))
    setNewPaysEligible('')
  }

  const removePaysEligible = (pays: string) => {
    setFormData(prev => ({
      ...prev,
      zones_geographiques: {
        ...prev.zones_geographiques,
        pays_eligibles: prev.zones_geographiques?.pays_eligibles?.filter(p => p !== pays) || [],
      },
    }))
  }

  const addPaysExclus = () => {
    if (!newPaysExclus.trim()) return
    setFormData(prev => ({
      ...prev,
      zones_geographiques: {
        ...prev.zones_geographiques,
        pays_exclus: [...(prev.zones_geographiques?.pays_exclus || []), newPaysExclus.trim()],
      },
    }))
    setNewPaysExclus('')
  }

  const removePaysExclus = (pays: string) => {
    setFormData(prev => ({
      ...prev,
      zones_geographiques: {
        ...prev.zones_geographiques,
        pays_exclus: prev.zones_geographiques?.pays_exclus?.filter(p => p !== pays) || [],
      },
    }))
  }

  const toggleCategorieAssure = (categorie: CategorieAssure) => {
    setFormData(prev => {
      const categories = prev.categories_assures || []
      const newCategories = categories.includes(categorie)
        ? categories.filter(c => c !== categorie)
        : [...categories, categorie]
      return {
        ...prev,
        categories_assures: newCategories,
      }
    })
  }

  const handleAssureurSelect = (value: string) => {
    const entity = assureurs.find(item => String(item.id) === value)
    setFormData(prev => ({
      ...prev,
      assureur_id: value,
      assureur: entity?.nom || '',
    }))
    if (errors.assureur_id) {
      setErrors(prevErrors => {
        const next = { ...prevErrors }
        delete next.assureur_id
        return next
      })
    }
  }

  const addExclusion = () => {
    if (!newExclusion.trim()) return
    setFormData(prev => ({
      ...prev,
      exclusions_generales: [...prev.exclusions_generales, newExclusion.trim()],
    }))
    setNewExclusion('')
  }

  const removeExclusion = (exclusion: string) => {
    setFormData(prev => ({
      ...prev,
      exclusions_generales: prev.exclusions_generales.filter(e => e !== exclusion),
    }))
  }

  const validate = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.code.trim()) {
      newErrors.code = 'Le code est requis'
    }

    if (!formData.nom.trim()) {
      newErrors.nom = 'Le nom est requis'
    }

    if (!formData.assureur_id) {
      newErrors.assureur_id = 'Sélectionnez un assureur'
    }

    if (!formData.cout || parseFloat(formData.cout) <= 0) {
      newErrors.cout = 'Le coût doit être supérieur à 0'
    }

    // Validation de la durée
    if (formData.duree_min_jours && formData.duree_max_jours) {
      if (parseInt(formData.duree_min_jours) > parseInt(formData.duree_max_jours)) {
        newErrors.duree = 'La durée minimale doit être inférieure ou égale à la durée maximale'
      }
    }

    // Validation de l'âge
    if (formData.age_minimum && formData.age_maximum) {
      if (parseInt(formData.age_minimum) > parseInt(formData.age_maximum)) {
        newErrors.age = 'L\'âge minimum doit être inférieur ou égal à l\'âge maximum'
      }
    }

    return newErrors
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const validationErrors = validate()
    
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    // Nettoyer les garanties : retirer les IDs temporaires et les garanties vides
    const garantiesCleaned = formData.garanties
      .filter(g => g.nom && g.description) // Garder seulement les garanties valides
      .map(({ id, ...garantie }) => garantie) // Retirer l'ID temporaire
    
    // Nettoyer les zones géographiques : enlever les objets vides
    const zonesCleaned = formData.zones_geographiques && 
      (formData.zones_geographiques.zones?.length > 0 || 
       formData.zones_geographiques.pays_eligibles?.length > 0 || 
       formData.zones_geographiques.pays_exclus?.length > 0 ||
       formData.zones_geographiques.specificites?.length > 0)
      ? formData.zones_geographiques
      : undefined

    // Préparer les données pour l'API
    const submitData: Partial<ProduitAssurance> = {
      code: formData.code.trim(),
      nom: formData.nom.trim(),
      description: formData.description.trim() || undefined,
      version: formData.version.trim() || undefined,
      est_actif: formData.est_actif,
      assureur: formData.assureur.trim() || undefined,
      image_url: formData.image_url.trim() || undefined,
      cout: parseFloat(formData.cout),
      cle_repartition: formData.cle_repartition,
      
      zones_geographiques: zonesCleaned,
      
      duree_min_jours: formData.duree_min_jours ? parseInt(formData.duree_min_jours) : undefined,
      duree_max_jours: formData.duree_max_jours ? parseInt(formData.duree_max_jours) : undefined,
      duree_validite_jours: formData.duree_validite_jours ? parseInt(formData.duree_validite_jours) : undefined,
      reconduction_possible: formData.reconduction_possible,
      couverture_multi_entrees: formData.couverture_multi_entrees,
      
      age_minimum: formData.age_minimum ? parseInt(formData.age_minimum) : undefined,
      age_maximum: formData.age_maximum ? parseInt(formData.age_maximum) : undefined,
      conditions_sante: formData.conditions_sante.trim() || undefined,
      categories_assures: formData.categories_assures.length > 0 ? formData.categories_assures : undefined,
      
      garanties: garantiesCleaned.length > 0 ? garantiesCleaned : undefined,
      exclusions_generales: formData.exclusions_generales.length > 0 ? formData.exclusions_generales : undefined,
      
      conditions: formData.conditions.trim() || undefined,
    }

    if (formData.assureur_id) {
      submitData.assureur_id = Number(formData.assureur_id)
    }
    if (selectedAssureur) {
      submitData.assureur = selectedAssureur.nom
    }

    onSubmit(submitData)
  }

  const handleChange = (field: string, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  const sections = [
    { id: 'general', label: '1. Informations générales', icon: '📋' },
    { id: 'zones', label: '2. Zone géographique', icon: '🌍' },
    { id: 'duree', label: '3. Durée du voyage', icon: '📅' },
    { id: 'profils', label: '4. Profil des assurés', icon: '👥' },
    { id: 'garanties', label: '5. Garanties incluses', icon: '🛡️' },
    { id: 'exclusions', label: '6. Exclusions générales', icon: '⚠️' },
  ]

  return (
    <form onSubmit={handleSubmit} className="product-form">
      {/* Navigation des sections */}
      <div className="form-sections-nav">
        {sections.map(section => (
          <button
            key={section.id}
            type="button"
            className={`section-nav-btn ${activeSection === section.id ? 'active' : ''}`}
            onClick={() => setActiveSection(section.id)}
          >
            <span className="section-icon">{section.icon}</span>
            <span className="section-label">{section.label}</span>
          </button>
        ))}
      </div>

      {/* Section 1: Informations générales */}
      {activeSection === 'general' && (
        <div className="form-section">
          <h2 className="section-title">Informations générales du produit</h2>
          
          <div className="form-group">
            <label htmlFor="code">Code produit *</label>
            <input
              id="code"
              type="text"
              value={formData.code}
              onChange={(e) => handleChange('code', e.target.value)}
              disabled={!!product}
              className={errors.code ? 'error' : ''}
              placeholder="Ex: VOY-STD-001"
            />
            {errors.code && <span className="error-message">{errors.code}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="nom">Nom du produit *</label>
            <input
              id="nom"
              type="text"
              value={formData.nom}
              onChange={(e) => handleChange('nom', e.target.value)}
              className={errors.nom ? 'error' : ''}
              placeholder="Ex: Voyage Standard, Premium+, VIP Business"
            />
            {errors.nom && <span className="error-message">{errors.nom}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="description">Description rapide</label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              rows={3}
              placeholder="Objectif et description du produit"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="version">Version</label>
              <input
                id="version"
                type="text"
                value={formData.version}
                onChange={(e) => handleChange('version', e.target.value)}
                placeholder="Ex: 1.0, 2.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="assureur_id">Assureur *</label>
              {assureursLoading ? (
                <div className="helper-text">Chargement des assureurs...</div>
              ) : assureursError ? (
                <div className="alert alert-error">
                  <div>
                    Impossible de charger les assureurs
                    {assureursFetchError?.message ? ` : ${assureursFetchError.message}` : '.'}
                  </div>
                  <button type="button" className="link-button" onClick={() => refetchAssureurs()}>
                    Réessayer
                  </button>
                </div>
              ) : (
                <select
                  id="assureur_id"
                  value={formData.assureur_id}
                  onChange={(e) => handleAssureurSelect(e.target.value)}
                  className={errors.assureur_id ? 'error' : ''}
                  disabled={noAssureurAvailable}
                >
                  <option value="">Sélectionner un assureur</option>
                  {assureurs.map((assureur) => (
                    <option key={assureur.id} value={assureur.id}>
                      {assureur.nom} — {assureur.pays}
                    </option>
                  ))}
                </select>
              )}
              {noAssureurAvailable && (
                <p className="helper-text">
                  Aucun assureur enregistré. Ouvrez{' '}
                  <a href="/backoffice/assureurs" target="_blank" rel="noreferrer">
                    Gestion des assureurs
                  </a>{' '}
                  pour en créer un avant d’ajouter un produit.
                </p>
              )}
              {errors.assureur_id && <span className="error-message">{errors.assureur_id}</span>}
            </div>
          </div>

          {(selectedAssureur || formData.assureur) && (
            <div className="assureur-summary">
              <div className="assureur-summary-header">
                {selectedAssureur?.logo_url && (
                  <img src={selectedAssureur.logo_url} alt={selectedAssureur.nom} className="assureur-logo" />
                )}
                <div>
                  <strong>{selectedAssureur?.nom || formData.assureur}</strong>
                  <p>{selectedAssureur?.pays || 'Assureur hérité (à mettre à jour)'}</p>
                </div>
              </div>
              <div className="assureur-summary-body">
                {selectedAssureur?.adresse && (
                  <p>
                    <span>Adresse</span>
                    {selectedAssureur.adresse}
                  </p>
                )}
                {selectedAssureur?.telephone && (
                  <p>
                    <span>Téléphone</span>
                    {selectedAssureur.telephone}
                  </p>
                )}
                {selectedAssureur?.agent_comptable && (
                  <p>
                    <span>Agent comptable</span>
                    {selectedAssureur.agent_comptable.full_name || selectedAssureur.agent_comptable.username}
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="image_url">URL de l'image</label>
            <input
              id="image_url"
              type="url"
              value={formData.image_url}
              onChange={(e) => handleChange('image_url', e.target.value)}
              placeholder="https://..."
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="cout">
                Coût ({CURRENCY_SYMBOLS[currency]}) *
              </label>
              <div className="input-with-symbol">
                <input
                  id="cout"
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.cout}
                  onChange={(e) => handleChange('cout', e.target.value)}
                  className={errors.cout ? 'error' : ''}
                />
                <span className="currency-symbol">{CURRENCY_SYMBOLS[currency]}</span>
              </div>
              {errors.cout && <span className="error-message">{errors.cout}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="cle_repartition">Clé de répartition *</label>
              <select
                id="cle_repartition"
                value={formData.cle_repartition}
                onChange={(e) => handleChange('cle_repartition', e.target.value)}
              >
                {CLE_REPARTITION_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={formData.est_actif}
                onChange={(e) => handleChange('est_actif', e.target.checked)}
              />
              Produit actif
            </label>
          </div>
        </div>
      )}

      {/* Section 2: Zone géographique */}
      {activeSection === 'zones' && (
        <div className="form-section">
          <h2 className="section-title">Zone géographique couverte</h2>
          
          <div className="form-group">
            <label>Zones géographiques</label>
            <div className="zones-grid">
              {ZONES_OPTIONS.map(zone => (
                <label key={zone} className="zone-checkbox">
                  <input
                    type="checkbox"
                    checked={formData.zones_geographiques?.zones?.includes(zone) || false}
                    onChange={() => toggleZone(zone)}
                  />
                  {zone}
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Pays éligibles</label>
            <div className="tags-input-container">
              <div className="input-with-button">
                <input
                  type="text"
                  value={newPaysEligible}
                  onChange={(e) => setNewPaysEligible(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addPaysEligible())}
                  placeholder="Entrer un code pays (ex: FR, US, CM) puis appuyer sur Entrée"
                />
                <button type="button" onClick={addPaysEligible} className="btn-add">+</button>
              </div>
              {formData.zones_geographiques?.pays_eligibles && formData.zones_geographiques.pays_eligibles.length > 0 && (
                <div className="tags-list">
                  {formData.zones_geographiques.pays_eligibles.map((pays, index) => (
                    <span key={index} className="tag">
                      {pays}
                      <button type="button" onClick={() => removePaysEligible(pays)} className="tag-remove">×</button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="form-group">
            <label>Pays exclus</label>
            <div className="tags-input-container">
              <div className="input-with-button">
                <input
                  type="text"
                  value={newPaysExclus}
                  onChange={(e) => setNewPaysExclus(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addPaysExclus())}
                  placeholder="Entrer un code pays puis appuyer sur Entrée"
                />
                <button type="button" onClick={addPaysExclus} className="btn-add">+</button>
              </div>
              {formData.zones_geographiques?.pays_exclus && formData.zones_geographiques.pays_exclus.length > 0 && (
                <div className="tags-list">
                  {formData.zones_geographiques.pays_exclus.map((pays, index) => (
                    <span key={index} className="tag">
                      {pays}
                      <button type="button" onClick={() => removePaysExclus(pays)} className="tag-remove">×</button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="specificites">Spécificités</label>
            <textarea
              id="specificites"
              value={formData.zones_geographiques?.specificites?.join(', ') || ''}
              onChange={(e) => {
                const specificites = e.target.value.split(',').map(s => s.trim()).filter(s => s)
                setFormData(prev => ({
                  ...prev,
                  zones_geographiques: {
                    ...prev.zones_geographiques,
                    specificites,
                  },
                }))
              }}
              rows={2}
              placeholder="Pays en guerre, sanctions internationales, etc. (séparés par des virgules)"
            />
          </div>
        </div>
      )}

      {/* Section 3: Durée du voyage */}
      {activeSection === 'duree' && (
        <div className="form-section">
          <h2 className="section-title">Durée du voyage</h2>
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="duree_min_jours">Durée minimale (jours)</label>
              <input
                id="duree_min_jours"
                type="number"
                min="1"
                value={formData.duree_min_jours}
                onChange={(e) => handleChange('duree_min_jours', e.target.value)}
              />
            </div>

            <div className="form-group">
              <label htmlFor="duree_max_jours">Durée maximale (jours)</label>
              <input
                id="duree_max_jours"
                type="number"
                min="1"
                value={formData.duree_max_jours}
                onChange={(e) => handleChange('duree_max_jours', e.target.value)}
              />
            </div>
          </div>

          {errors.duree && <span className="error-message">{errors.duree}</span>}

          <div className="form-group">
            <label htmlFor="duree_validite_jours">Durée de validité (jours)</label>
            <input
              id="duree_validite_jours"
              type="number"
              min="1"
              value={formData.duree_validite_jours}
              onChange={(e) => handleChange('duree_validite_jours', e.target.value)}
            />
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={formData.reconduction_possible}
                onChange={(e) => handleChange('reconduction_possible', e.target.checked)}
              />
              Reconduction possible
            </label>
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={formData.couverture_multi_entrees}
                onChange={(e) => handleChange('couverture_multi_entrees', e.target.checked)}
              />
              Couverture multi-entrées
            </label>
          </div>
        </div>
      )}

      {/* Section 4: Profil des assurés */}
      {activeSection === 'profils' && (
        <div className="form-section">
          <h2 className="section-title">Profil des assurés</h2>
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="age_minimum">Âge minimum</label>
              <input
                id="age_minimum"
                type="number"
                min="0"
                max="120"
                value={formData.age_minimum}
                onChange={(e) => handleChange('age_minimum', e.target.value)}
              />
            </div>

            <div className="form-group">
              <label htmlFor="age_maximum">Âge maximum</label>
              <input
                id="age_maximum"
                type="number"
                min="0"
                max="120"
                value={formData.age_maximum}
                onChange={(e) => handleChange('age_maximum', e.target.value)}
              />
            </div>
          </div>

          {errors.age && <span className="error-message">{errors.age}</span>}

          <div className="form-group">
            <label>Catégories d'assurés</label>
            <div className="categories-grid">
              {CATEGORIES_ASSURE_OPTIONS.map(cat => (
                <label key={cat.value} className="category-checkbox">
                  <input
                    type="checkbox"
                    checked={formData.categories_assures?.includes(cat.value) || false}
                    onChange={() => toggleCategorieAssure(cat.value)}
                  />
                  {cat.label}
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="conditions_sante">Conditions de santé particulières</label>
            <textarea
              id="conditions_sante"
              value={formData.conditions_sante}
              onChange={(e) => handleChange('conditions_sante', e.target.value)}
              rows={4}
              placeholder="Ex: Personnes âgées avec supplément, conditions préexistantes, etc."
            />
          </div>
        </div>
      )}

      {/* Section 5: Garanties incluses */}
      {activeSection === 'garanties' && (
        <div className="form-section">
          <h2 className="section-title">Garanties incluses</h2>
          
          <p className="section-description">
            Configurez chaque garantie avec ses détails (nom, description, plafond, franchise, délai de carence, etc.)
          </p>

          <div className="garanties-list">
            {formData.garanties.map((garantie, index) => (
              <div key={garantie.id || index} className="garantie-card">
                <div className="garantie-header">
                  <h3>Garantie {index + 1}</h3>
                  <button
                    type="button"
                    onClick={() => removeGarantie(garantie.id!)}
                    className="btn-remove"
                  >
                    Supprimer
                  </button>
                </div>

                <div className="form-group">
                  <label>Type de garantie</label>
                  <select
                    value={GARANTIES_TYPES.includes(garantie.nom) ? garantie.nom : ''}
                    onChange={(e) => {
                      const value = e.target.value
                      if (value) {
                        updateGarantie(garantie.id!, 'nom', value)
                      }
                    }}
                  >
                    <option value="">Sélectionner ou saisir manuellement</option>
                    {GARANTIES_TYPES.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Nom de la garantie *</label>
                  <input
                    type="text"
                    value={garantie.nom}
                    onChange={(e) => updateGarantie(garantie.id!, 'nom', e.target.value)}
                    placeholder="Nom de la garantie"
                  />
                </div>

                <div className="form-group">
                  <label>Description *</label>
                  <textarea
                    value={garantie.description}
                    onChange={(e) => updateGarantie(garantie.id!, 'description', e.target.value)}
                    rows={3}
                    placeholder="Description détaillée de la garantie"
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Plafond ({CURRENCY_SYMBOLS[currency]})</label>
                    <div className="input-with-symbol">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={garantie.plafond || ''}
                        onChange={(e) => updateGarantie(garantie.id!, 'plafond', e.target.value ? parseFloat(e.target.value) : undefined)}
                      />
                      <span className="currency-symbol">{CURRENCY_SYMBOLS[currency]}</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Franchise ({CURRENCY_SYMBOLS[currency]})</label>
                    <div className="input-with-symbol">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={garantie.franchise || ''}
                        onChange={(e) => updateGarantie(garantie.id!, 'franchise', e.target.value ? parseFloat(e.target.value) : undefined)}
                      />
                      <span className="currency-symbol">{CURRENCY_SYMBOLS[currency]}</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Délai de carence (jours)</label>
                    <input
                      type="number"
                      min="0"
                      value={garantie.delai_carence || ''}
                      onChange={(e) => updateGarantie(garantie.id!, 'delai_carence', e.target.value ? parseInt(e.target.value) : undefined)}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Conditions d'activation</label>
                  <textarea
                    value={garantie.conditions_activation || ''}
                    onChange={(e) => updateGarantie(garantie.id!, 'conditions_activation', e.target.value)}
                    rows={2}
                    placeholder="Conditions spécifiques pour activer cette garantie"
                  />
                </div>

                <div className="form-group">
                  <label>Exclusions spécifiques</label>
                  <textarea
                    value={garantie.exclusions_specifiques?.join(', ') || ''}
                    onChange={(e) => {
                      const exclusions = e.target.value.split(',').map(s => s.trim()).filter(s => s)
                      updateGarantie(garantie.id!, 'exclusions_specifiques', exclusions.length > 0 ? exclusions : undefined)
                    }}
                    rows={2}
                    placeholder="Exclusions spécifiques à cette garantie (séparées par des virgules)"
                  />
                </div>
              </div>
            ))}
          </div>

          <button type="button" onClick={addGarantie} className="btn-add-large">
            + Ajouter une garantie
          </button>
        </div>
      )}

      {/* Section 6: Exclusions générales */}
      {activeSection === 'exclusions' && (
        <div className="form-section">
          <h2 className="section-title">Exclusions générales</h2>
          
          <div className="form-group">
            <label>Ajouter une exclusion</label>
            <div className="input-with-button">
              <input
                type="text"
                value={newExclusion}
                onChange={(e) => setNewExclusion(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addExclusion())}
                placeholder="Ex: Guerre, terrorisme, activités sportives extrêmes, etc."
              />
              <button type="button" onClick={addExclusion} className="btn-add">+</button>
            </div>
          </div>

          {formData.exclusions_generales.length > 0 && (
            <div className="exclusions-list">
              {formData.exclusions_generales.map((exclusion, index) => (
                <div key={index} className="exclusion-item">
                  <span>{exclusion}</span>
                  <button
                    type="button"
                    onClick={() => removeExclusion(exclusion)}
                    className="btn-remove-small"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="conditions">Conditions générales (texte libre)</label>
            <textarea
              id="conditions"
              value={formData.conditions}
              onChange={(e) => handleChange('conditions', e.target.value)}
              rows={6}
              placeholder="Conditions générales supplémentaires du produit"
            />
          </div>
        </div>
      )}

      {/* Actions du formulaire */}
      <div className="form-actions">
        <button type="button" onClick={onCancel} className="btn-secondary">
          Annuler
        </button>
        <button
          type="submit"
          className="btn-primary"
          disabled={noAssureurAvailable}
          title={noAssureurAvailable ? 'Créez d’abord un assureur dans le back-office' : undefined}
        >
          {product ? 'Mettre à jour' : 'Créer'}
        </button>
      </div>
    </form>
  )
}
