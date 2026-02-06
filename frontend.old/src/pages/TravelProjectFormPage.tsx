import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { voyagesApi } from '../api/voyages'
import TravelProjectForm from '../components/TravelProjectForm'
import { ProjetVoyage } from '../types'
import './TravelProjectFormPage.css'

export default function TravelProjectFormPage() {
  const navigate = useNavigate()

  const createMutation = useMutation({
    mutationFn: (data: Partial<ProjetVoyage>) => {
      // Récupérer l'ID utilisateur depuis le localStorage ou le contexte
      // Pour l'instant, on suppose qu'il y a un user_id dans le localStorage
      const userId = parseInt(localStorage.getItem('user_id') || '1')
      return voyagesApi.create({ ...data, user_id: userId })
    },
    onSuccess: (projet) => {
      // Rediriger vers la page de recherche de produits avec l'ID du projet
      navigate(`/products?projet_id=${projet.id}`)
    },
    onError: (error: any) => {
      alert(`Erreur lors de la création du projet: ${error.response?.data?.detail || error.message}`)
    },
  })

  const handleSubmit = (data: Partial<ProjetVoyage>) => {
    createMutation.mutate(data)
  }

  return (
    <div className="travel-project-form-page">
      <div className="page-header">
        <h1>Créer un projet de voyage</h1>
        <p className="subtitle">Remplissez les informations sur votre voyage pour trouver les meilleures assurances</p>
      </div>

      {createMutation.isPending ? (
        <div className="loading">Création du projet en cours...</div>
      ) : (
        <TravelProjectForm onSubmit={handleSubmit} />
      )}
    </div>
  )
}
