import { useParams, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Formik, Form, Field, ErrorMessage } from 'formik'
import * as Yup from 'yup'
import { questionnairesApi } from '../api/questionnaires'
import './Questionnaire.css'

const validationSchema = Yup.object({
  sante_generale: Yup.string()
    .required('Ce champ est requis'),
  allergies: Yup.string(),
  medicaments_actuels: Yup.string(),
  conditions_medicales: Yup.string(),
  assurance_actuelle: Yup.string(),
})

interface QuestionnaireShortValues {
  sante_generale: string
  allergies: string
  medicaments_actuels: string
  conditions_medicales: string
  assurance_actuelle: string
}

export default function QuestionnaireShort() {
  const { subscriptionId } = useParams<{ subscriptionId: string }>()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: (reponses: Record<string, any>) =>
      questionnairesApi.createShort(Number(subscriptionId), reponses),
    onSuccess: () => {
      alert('Questionnaire court enregistré avec succès!')
      navigate(-1)
    },
    onError: (error: any) => {
      alert(`Erreur: ${error.response?.data?.detail || error.message}`)
    },
  })

  const initialValues: QuestionnaireShortValues = {
    sante_generale: '',
    allergies: '',
    medicaments_actuels: '',
    conditions_medicales: '',
    assurance_actuelle: '',
  }

  return (
    <div className="questionnaire-container">
      <div className="questionnaire-header">
        <h1>Questionnaire Court</h1>
        <p>Veuillez remplir ce formulaire pour votre souscription #{subscriptionId}</p>
      </div>

      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={(values, { setSubmitting }) => {
          mutation.mutate(values, {
            onSettled: () => {
              setSubmitting(false)
            },
          })
        }}
      >
        {({ isSubmitting }) => (
          <Form className="questionnaire-form">
            <div className="form-group">
              <label htmlFor="sante_generale">
                État de santé général *
              </label>
              <Field
                as="select"
                id="sante_generale"
                name="sante_generale"
                className="form-control"
              >
                <option value="">Sélectionnez...</option>
                <option value="excellent">Excellent</option>
                <option value="bon">Bon</option>
                <option value="moyen">Moyen</option>
                <option value="faible">Faible</option>
              </Field>
              <ErrorMessage name="sante_generale" component="div" className="error-message" />
            </div>

            <div className="form-group">
              <label htmlFor="allergies">Allergies connues</label>
              <Field
                as="textarea"
                id="allergies"
                name="allergies"
                rows={3}
                className="form-control"
                placeholder="Listez vos allergies si vous en avez"
              />
              <ErrorMessage name="allergies" component="div" className="error-message" />
            </div>

            <div className="form-group">
              <label htmlFor="medicaments_actuels">Médicaments actuels</label>
              <Field
                as="textarea"
                id="medicaments_actuels"
                name="medicaments_actuels"
                rows={3}
                className="form-control"
                placeholder="Listez les médicaments que vous prenez actuellement"
              />
              <ErrorMessage name="medicaments_actuels" component="div" className="error-message" />
            </div>

            <div className="form-group">
              <label htmlFor="conditions_medicales">Conditions médicales existantes</label>
              <Field
                as="textarea"
                id="conditions_medicales"
                name="conditions_medicales"
                rows={3}
                className="form-control"
                placeholder="Décrivez vos conditions médicales si vous en avez"
              />
              <ErrorMessage name="conditions_medicales" component="div" className="error-message" />
            </div>

            <div className="form-group">
              <label htmlFor="assurance_actuelle">Assurance actuelle</label>
              <Field
                type="text"
                id="assurance_actuelle"
                name="assurance_actuelle"
                className="form-control"
                placeholder="Nom de votre assurance actuelle (si applicable)"
              />
              <ErrorMessage name="assurance_actuelle" component="div" className="error-message" />
            </div>

            <div className="form-actions">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="btn btn-secondary"
              >
                Annuler
              </button>
              <button
                type="submit"
                disabled={isSubmitting || mutation.isPending}
                className="btn btn-primary"
              >
                {mutation.isPending ? 'Enregistrement...' : 'Enregistrer'}
              </button>
            </div>
          </Form>
        )}
      </Formik>
    </div>
  )
}

