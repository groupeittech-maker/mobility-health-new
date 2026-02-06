import { useState } from 'react'
import { ProjetVoyage } from '../types'
import './TravelProjectForm.css'

interface TravelProjectFormProps {
  onSubmit: (data: Partial<ProjetVoyage>) => void
  onCancel?: () => void
  initialData?: Partial<ProjetVoyage>
}

export default function TravelProjectForm({ onSubmit, onCancel, initialData }: TravelProjectFormProps) {
  const [formData, setFormData] = useState({
    titre: initialData?.titre || '',
    description: initialData?.description || '',
    destination: initialData?.destination || '',
    date_depart: initialData?.date_depart 
      ? new Date(initialData.date_depart).toISOString().split('T')[0]
      : '',
    date_retour: initialData?.date_retour
      ? new Date(initialData.date_retour).toISOString().split('T')[0]
      : '',
    nombre_participants: initialData?.nombre_participants || 1,
    notes: initialData?.notes || '',
    budget_estime: initialData?.budget_estime ? String(initialData.budget_estime) : '',
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.titre.trim()) {
      newErrors.titre = 'Le titre est requis'
    }

    if (!formData.destination.trim()) {
      newErrors.destination = 'La destination est requise'
    }

    if (!formData.date_depart) {
      newErrors.date_depart = 'La date de départ est requise'
    }

    if (formData.date_retour && formData.date_retour <= formData.date_depart) {
      newErrors.date_retour = 'La date de retour doit être postérieure à la date de départ'
    }

    if (formData.nombre_participants < 1) {
      newErrors.nombre_participants = 'Le nombre de participants doit être au moins 1'
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

    onSubmit({
      titre: formData.titre.trim(),
      description: formData.description.trim() || undefined,
      destination: formData.destination.trim(),
      date_depart: new Date(formData.date_depart).toISOString(),
      date_retour: formData.date_retour ? new Date(formData.date_retour).toISOString() : undefined,
      nombre_participants: formData.nombre_participants,
      notes: formData.notes.trim() || undefined,
      budget_estime: formData.budget_estime ? parseFloat(formData.budget_estime) : undefined,
    })
  }

  const handleChange = (field: string, value: string | number) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="travel-project-form">
      <div className="form-group">
        <label htmlFor="titre">Titre du voyage *</label>
        <input
          id="titre"
          type="text"
          value={formData.titre}
          onChange={(e) => handleChange('titre', e.target.value)}
          placeholder="Ex: Voyage en Europe"
          className={errors.titre ? 'error' : ''}
        />
        {errors.titre && <span className="error-message">{errors.titre}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="destination">Destination *</label>
        <input
          id="destination"
          type="text"
          value={formData.destination}
          onChange={(e) => handleChange('destination', e.target.value)}
          placeholder="Ex: Paris, France"
          className={errors.destination ? 'error' : ''}
        />
        {errors.destination && <span className="error-message">{errors.destination}</span>}
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="date_depart">Date de départ *</label>
          <input
            id="date_depart"
            type="date"
            value={formData.date_depart}
            onChange={(e) => handleChange('date_depart', e.target.value)}
            min={new Date().toISOString().split('T')[0]}
            className={errors.date_depart ? 'error' : ''}
          />
          {errors.date_depart && <span className="error-message">{errors.date_depart}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="date_retour">Date de retour</label>
          <input
            id="date_retour"
            type="date"
            value={formData.date_retour}
            onChange={(e) => handleChange('date_retour', e.target.value)}
            min={formData.date_depart || new Date().toISOString().split('T')[0]}
          />
          {errors.date_retour && <span className="error-message">{errors.date_retour}</span>}
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="nombre_participants">Nombre de participants *</label>
        <input
          id="nombre_participants"
          type="number"
          min="1"
          value={formData.nombre_participants}
          onChange={(e) => handleChange('nombre_participants', parseInt(e.target.value) || 1)}
          className={errors.nombre_participants ? 'error' : ''}
        />
        {errors.nombre_participants && <span className="error-message">{errors.nombre_participants}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          value={formData.description}
          onChange={(e) => handleChange('description', e.target.value)}
          rows={4}
          placeholder="Décrivez votre projet de voyage..."
        />
      </div>

      <div className="form-group">
        <label htmlFor="budget_estime">Budget estimé (optionnel)</label>
        <input
          id="budget_estime"
          type="number"
          step="0.01"
          min="0"
          value={formData.budget_estime}
          onChange={(e) => handleChange('budget_estime', e.target.value)}
          placeholder="0.00"
        />
      </div>

      <div className="form-group">
        <label htmlFor="notes">Notes</label>
        <textarea
          id="notes"
          value={formData.notes}
          onChange={(e) => handleChange('notes', e.target.value)}
          rows={3}
          placeholder="Informations complémentaires..."
        />
      </div>

      <div className="form-actions">
        {onCancel && (
          <button type="button" onClick={onCancel} className="btn-secondary">
            Annuler
          </button>
        )}
        <button type="submit" className="btn-primary">
          Créer le projet
        </button>
      </div>
    </form>
  )
}
