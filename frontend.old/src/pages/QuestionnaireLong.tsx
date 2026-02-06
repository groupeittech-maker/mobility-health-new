import { useParams, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Formik, Form, Field, ErrorMessage } from 'formik'
import * as Yup from 'yup'
import { questionnairesApi } from '../api/questionnaires'
import './Questionnaire.css'

const validationSchema = Yup.object({
  informations_personnelles: Yup.object({
    date_naissance: Yup.string().required('La date de naissance est requise'),
    lieu_naissance: Yup.string().required('Le lieu de naissance est requis'),
    nationalite: Yup.string().required('La nationalité est requise'),
    profession: Yup.string().required('La profession est requise'),
  }),
  historique_medical: Yup.object({
    hospitalisations: Yup.string(),
    chirurgies: Yup.string(),
    accidents: Yup.string(),
    maladies_chroniques: Yup.string(),
  }),
  mode_de_vie: Yup.object({
    activite_physique: Yup.string().required('Ce champ est requis'),
    tabagisme: Yup.string().required('Ce champ est requis'),
    consommation_alcool: Yup.string().required('Ce champ est requis'),
    voyages_frequents: Yup.string().required('Ce champ est requis'),
  }),
  antecedents_familiaux: Yup.string(),
  informations_voyage: Yup.object({
    destinations_frequentes: Yup.string(),
    duree_sejours: Yup.string(),
    activites_risque: Yup.string(),
  }),
})

interface QuestionnaireLongValues {
  informations_personnelles: {
    date_naissance: string
    lieu_naissance: string
    nationalite: string
    profession: string
  }
  historique_medical: {
    hospitalisations: string
    chirurgies: string
    accidents: string
    maladies_chroniques: string
  }
  mode_de_vie: {
    activite_physique: string
    tabagisme: string
    consommation_alcool: string
    voyages_frequents: string
  }
  antecedents_familiaux: string
  informations_voyage: {
    destinations_frequentes: string
    duree_sejours: string
    activites_risque: string
  }
}

export default function QuestionnaireLong() {
  const { subscriptionId } = useParams<{ subscriptionId: string }>()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: (reponses: Record<string, any>) =>
      questionnairesApi.createLong(Number(subscriptionId), reponses),
    onSuccess: () => {
      alert('Questionnaire long enregistré avec succès!')
      navigate(-1)
    },
    onError: (error: any) => {
      alert(`Erreur: ${error.response?.data?.detail || error.message}`)
    },
  })

  const initialValues: QuestionnaireLongValues = {
    informations_personnelles: {
      date_naissance: '',
      lieu_naissance: '',
      nationalite: '',
      profession: '',
    },
    historique_medical: {
      hospitalisations: '',
      chirurgies: '',
      accidents: '',
      maladies_chroniques: '',
    },
    mode_de_vie: {
      activite_physique: '',
      tabagisme: '',
      consommation_alcool: '',
      voyages_frequents: '',
    },
    antecedents_familiaux: '',
    informations_voyage: {
      destinations_frequentes: '',
      duree_sejours: '',
      activites_risque: '',
    },
  }

  return (
    <div className="questionnaire-container">
      <div className="questionnaire-header">
        <h1>Questionnaire Long</h1>
        <p>Veuillez remplir ce formulaire détaillé pour votre souscription #{subscriptionId}</p>
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
            <section className="form-section">
              <h2>Informations Personnelles</h2>
              
              <div className="form-group">
                <label htmlFor="informations_personnelles.date_naissance">
                  Date de naissance *
                </label>
                <Field
                  type="date"
                  id="informations_personnelles.date_naissance"
                  name="informations_personnelles.date_naissance"
                  className="form-control"
                />
                <ErrorMessage name="informations_personnelles.date_naissance" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label htmlFor="informations_personnelles.lieu_naissance">
                  Lieu de naissance *
                </label>
                <Field
                  type="text"
                  id="informations_personnelles.lieu_naissance"
                  name="informations_personnelles.lieu_naissance"
                  className="form-control"
                />
                <ErrorMessage name="informations_personnelles.lieu_naissance" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label htmlFor="informations_personnelles.nationalite">
                  Nationalité *
                </label>
                <Field
                  type="text"
                  id="informations_personnelles.nationalite"
                  name="informations_personnelles.nationalite"
                  className="form-control"
                />
                <ErrorMessage name="informations_personnelles.nationalite" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label htmlFor="informations_personnelles.profession">
                  Profession *
                </label>
                <Field
                  type="text"
                  id="informations_personnelles.profession"
                  name="informations_personnelles.profession"
                  className="form-control"
                />
                <ErrorMessage name="informations_personnelles.profession" component="div" className="error-message" />
              </div>
            </section>

            <section className="form-section">
              <h2>Historique Médical</h2>
              
              <div className="form-group">
                <label htmlFor="historique_medical.hospitalisations">
                  Hospitalisations récentes
                </label>
                <Field
                  as="textarea"
                  id="historique_medical.hospitalisations"
                  name="historique_medical.hospitalisations"
                  rows={3}
                  className="form-control"
                  placeholder="Décrivez vos hospitalisations récentes si applicable"
                />
              </div>

              <div className="form-group">
                <label htmlFor="historique_medical.chirurgies">
                  Chirurgies
                </label>
                <Field
                  as="textarea"
                  id="historique_medical.chirurgies"
                  name="historique_medical.chirurgies"
                  rows={3}
                  className="form-control"
                  placeholder="Listez vos chirurgies si applicable"
                />
              </div>

              <div className="form-group">
                <label htmlFor="historique_medical.accidents">
                  Accidents
                </label>
                <Field
                  as="textarea"
                  id="historique_medical.accidents"
                  name="historique_medical.accidents"
                  rows={3}
                  className="form-control"
                  placeholder="Décrivez les accidents significatifs si applicable"
                />
              </div>

              <div className="form-group">
                <label htmlFor="historique_medical.maladies_chroniques">
                  Maladies chroniques
                </label>
                <Field
                  as="textarea"
                  id="historique_medical.maladies_chroniques"
                  name="historique_medical.maladies_chroniques"
                  rows={3}
                  className="form-control"
                  placeholder="Listez vos maladies chroniques si applicable"
                />
              </div>
            </section>

            <section className="form-section">
              <h2>Mode de Vie</h2>
              
              <div className="form-group">
                <label htmlFor="mode_de_vie.activite_physique">
                  Activité physique *
                </label>
                <Field
                  as="select"
                  id="mode_de_vie.activite_physique"
                  name="mode_de_vie.activite_physique"
                  className="form-control"
                >
                  <option value="">Sélectionnez...</option>
                  <option value="aucune">Aucune</option>
                  <option value="legere">Légère (1-2 fois/semaine)</option>
                  <option value="moderee">Modérée (3-4 fois/semaine)</option>
                  <option value="intense">Intense (5+ fois/semaine)</option>
                </Field>
                <ErrorMessage name="mode_de_vie.activite_physique" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label htmlFor="mode_de_vie.tabagisme">
                  Tabagisme *
                </label>
                <Field
                  as="select"
                  id="mode_de_vie.tabagisme"
                  name="mode_de_vie.tabagisme"
                  className="form-control"
                >
                  <option value="">Sélectionnez...</option>
                  <option value="non">Non-fumeur</option>
                  <option value="occasionnel">Fumeur occasionnel</option>
                  <option value="regulier">Fumeur régulier</option>
                  <option value="ancien">Ancien fumeur</option>
                </Field>
                <ErrorMessage name="mode_de_vie.tabagisme" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label htmlFor="mode_de_vie.consommation_alcool">
                  Consommation d'alcool *
                </label>
                <Field
                  as="select"
                  id="mode_de_vie.consommation_alcool"
                  name="mode_de_vie.consommation_alcool"
                  className="form-control"
                >
                  <option value="">Sélectionnez...</option>
                  <option value="aucune">Aucune</option>
                  <option value="occasionnelle">Occasionnelle</option>
                  <option value="moderee">Modérée</option>
                  <option value="frequente">Fréquente</option>
                </Field>
                <ErrorMessage name="mode_de_vie.consommation_alcool" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label htmlFor="mode_de_vie.voyages_frequents">
                  Voyages fréquents *
                </label>
                <Field
                  as="select"
                  id="mode_de_vie.voyages_frequents"
                  name="mode_de_vie.voyages_frequents"
                  className="form-control"
                >
                  <option value="">Sélectionnez...</option>
                  <option value="non">Non</option>
                  <option value="rarement">Rarement (1-2 fois/an)</option>
                  <option value="occasionnellement">Occasionnellement (3-5 fois/an)</option>
                  <option value="frequemment">Fréquemment (6+ fois/an)</option>
                </Field>
                <ErrorMessage name="mode_de_vie.voyages_frequents" component="div" className="error-message" />
              </div>
            </section>

            <section className="form-section">
              <h2>Antécédents Familiaux</h2>
              
              <div className="form-group">
                <label htmlFor="antecedents_familiaux">
                  Antécédents familiaux
                </label>
                <Field
                  as="textarea"
                  id="antecedents_familiaux"
                  name="antecedents_familiaux"
                  rows={4}
                  className="form-control"
                  placeholder="Décrivez les antécédents médicaux familiaux significatifs"
                />
              </div>
            </section>

            <section className="form-section">
              <h2>Informations de Voyage</h2>
              
              <div className="form-group">
                <label htmlFor="informations_voyage.destinations_frequentes">
                  Destinations fréquentes
                </label>
                <Field
                  as="textarea"
                  id="informations_voyage.destinations_frequentes"
                  name="informations_voyage.destinations_frequentes"
                  rows={3}
                  className="form-control"
                  placeholder="Listez vos destinations de voyage fréquentes"
                />
              </div>

              <div className="form-group">
                <label htmlFor="informations_voyage.duree_sejours">
                  Durée des séjours
                </label>
                <Field
                  type="text"
                  id="informations_voyage.duree_sejours"
                  name="informations_voyage.duree_sejours"
                  className="form-control"
                  placeholder="Ex: 1-2 semaines, 1 mois, etc."
                />
              </div>

              <div className="form-group">
                <label htmlFor="informations_voyage.activites_risque">
                  Activités à risque
                </label>
                <Field
                  as="textarea"
                  id="informations_voyage.activites_risque"
                  name="informations_voyage.activites_risque"
                  rows={3}
                  className="form-control"
                  placeholder="Décrivez les activités à risque que vous pratiquez lors de vos voyages"
                />
              </div>
            </section>

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

