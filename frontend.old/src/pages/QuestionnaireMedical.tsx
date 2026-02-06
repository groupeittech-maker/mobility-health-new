import { useParams, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Formik, Form, Field, ErrorMessage } from 'formik'
import * as Yup from 'yup'
import { questionnairesApi } from '../api/questionnaires'
import './Questionnaire.css'

const validationSchema = Yup.object({
  antecedents_medicaux: Yup.object({
    maladies_chroniques: Yup.array().of(Yup.string()),
    maladie_chronique_autre: Yup.string().when('maladies_chroniques', {
      is: (arr: string[]) => arr && arr.includes('autre'),
      then: (schema) => schema.required('Veuillez préciser la maladie chronique'),
      otherwise: (schema) => schema,
    }),
    traitement_medical: Yup.string().required('Ce champ est requis'),
    traitement_medical_details: Yup.string().when('traitement_medical', {
      is: 'oui',
      then: (schema) => schema.required('Veuillez préciser le traitement médical'),
      otherwise: (schema) => schema,
    }),
    hospitalisation_12mois: Yup.string().required('Ce champ est requis'),
    hospitalisation_12mois_details: Yup.string().when('hospitalisation_12mois', {
      is: 'oui',
      then: (schema) => schema.required('Veuillez préciser la raison de l\'hospitalisation'),
      otherwise: (schema) => schema,
    }),
    operation_5ans: Yup.string().required('Ce champ est requis'),
    operation_5ans_details: Yup.string().when('operation_5ans', {
      is: 'oui',
      then: (schema) => schema.required('Veuillez préciser l\'opération chirurgicale'),
      otherwise: (schema) => schema,
    }),
  }),
  symptomes_recents: Yup.object({
    douleurs_thoraciques: Yup.boolean(),
    essoufflement: Yup.boolean(),
    vertiges: Yup.boolean(),
    perte_connaissance: Yup.boolean(),
    fievre_persistante: Yup.boolean(),
    saignements_anormaux: Yup.boolean(),
    reactions_allergiques: Yup.boolean(),
    enceinte: Yup.string(),
  }),
  maladies_contagieuses: Yup.object({
    paludisme: Yup.boolean(),
    tuberculose: Yup.boolean(),
    hepatite: Yup.boolean(),
    infections_respiratoires: Yup.boolean(),
    autre_maladie_infectieuse: Yup.string(),
    contact_personne_malade: Yup.string().required('Ce champ est requis'),
    contact_personne_malade_details: Yup.string().when('contact_personne_malade', {
      is: 'oui',
      then: (schema) => schema.required('Veuillez préciser les détails'),
      otherwise: (schema) => schema,
    }),
  }),
  declaration: Yup.object({
    rien_omis: Yup.boolean().oneOf([true], 'Vous devez confirmer cette déclaration'),
    fausse_declaration: Yup.boolean().oneOf([true], 'Vous devez reconnaître cette condition'),
  }),
})

interface QuestionnaireMedicalValues {
  antecedents_medicaux: {
    maladies_chroniques: string[]
    maladie_chronique_autre: string
    traitement_medical: string
    traitement_medical_details: string
    hospitalisation_12mois: string
    hospitalisation_12mois_details: string
    operation_5ans: string
    operation_5ans_details: string
  }
  symptomes_recents: {
    douleurs_thoraciques: boolean
    essoufflement: boolean
    vertiges: boolean
    perte_connaissance: boolean
    fievre_persistante: boolean
    saignements_anormaux: boolean
    reactions_allergiques: boolean
    enceinte: string
  }
  maladies_contagieuses: {
    paludisme: boolean
    tuberculose: boolean
    hepatite: boolean
    infections_respiratoires: boolean
    autre_maladie_infectieuse: string
    contact_personne_malade: string
    contact_personne_malade_details: string
  }
  declaration: {
    rien_omis: boolean
    fausse_declaration: boolean
  }
}

const MALADIES_CHRONIQUES = [
  { value: 'hypertension', label: 'Hypertension' },
  { value: 'diabete', label: 'Diabète' },
  { value: 'asthme', label: 'Asthme' },
  { value: 'maladie_cardiaque', label: 'Maladie cardiaque' },
  { value: 'maladie_renale', label: 'Maladie rénale' },
  { value: 'maladie_hepatique', label: 'Maladie hépatique' },
  { value: 'autre', label: 'Autre (préciser)' },
]

export default function QuestionnaireMedical() {
  const { subscriptionId } = useParams<{ subscriptionId: string }>()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: (reponses: Record<string, any>) =>
      questionnairesApi.createMedical(Number(subscriptionId), reponses),
    onSuccess: () => {
      alert('Questionnaire médical enregistré avec succès!')
      navigate(-1)
    },
    onError: (error: any) => {
      alert(`Erreur: ${error.response?.data?.detail || error.message}`)
    },
  })

  const initialValues: QuestionnaireMedicalValues = {
    antecedents_medicaux: {
      maladies_chroniques: [],
      maladie_chronique_autre: '',
      traitement_medical: '',
      traitement_medical_details: '',
      hospitalisation_12mois: '',
      hospitalisation_12mois_details: '',
      operation_5ans: '',
      operation_5ans_details: '',
    },
    symptomes_recents: {
      douleurs_thoraciques: false,
      essoufflement: false,
      vertiges: false,
      perte_connaissance: false,
      fievre_persistante: false,
      saignements_anormaux: false,
      reactions_allergiques: false,
      enceinte: '',
    },
    maladies_contagieuses: {
      paludisme: false,
      tuberculose: false,
      hepatite: false,
      infections_respiratoires: false,
      autre_maladie_infectieuse: '',
      contact_personne_malade: '',
      contact_personne_malade_details: '',
    },
    declaration: {
      rien_omis: false,
      fausse_declaration: false,
    },
  }

  return (
    <div className="questionnaire-container">
      <div className="questionnaire-header">
        <h1>Questionnaire Médical</h1>
        <p>Veuillez remplir ce formulaire médical pour votre souscription #{subscriptionId}</p>
        <p className="section-description">
          <strong>But :</strong> Déterminer si vous n'avez pas de maladie grave non déclarée et évaluer les risques avant de valider l'attestation définitive.
        </p>
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
        {({ isSubmitting, values, setFieldValue }) => (
          <Form className="questionnaire-form">
            {/* Section A: Antécédents médicaux généraux */}
            <section className="form-section">
              <h2>A. Antécédents médicaux généraux</h2>
              
              <div className="form-group">
                <label>
                  Souffrez-vous actuellement d'une maladie chronique ?
                </label>
                <div className="checkbox-group">
                  {MALADIES_CHRONIQUES.map((maladie) => (
                    <label key={maladie.value} className="checkbox-label">
                      <Field
                        type="checkbox"
                        name="antecedents_medicaux.maladies_chroniques"
                        value={maladie.value}
                        checked={values.antecedents_medicaux.maladies_chroniques.includes(maladie.value)}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                          const { checked, value } = e.target
                          const currentValues = values.antecedents_medicaux.maladies_chroniques || []
                          if (checked) {
                            setFieldValue(
                              'antecedents_medicaux.maladies_chroniques',
                              [...currentValues, value]
                            )
                          } else {
                            setFieldValue(
                              'antecedents_medicaux.maladies_chroniques',
                              currentValues.filter((v: string) => v !== value)
                            )
                          }
                        }}
                      />
                      {maladie.label}
                    </label>
                  ))}
                </div>
                {values.antecedents_medicaux.maladies_chroniques.includes('autre') && (
                  <div className="form-group" style={{ marginTop: '1rem' }}>
                    <Field
                      type="text"
                      name="antecedents_medicaux.maladie_chronique_autre"
                      placeholder="Précisez la maladie chronique"
                      className="form-control"
                    />
                    <ErrorMessage
                      name="antecedents_medicaux.maladie_chronique_autre"
                      component="div"
                      className="error-message"
                    />
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>
                  Suivez-vous un traitement médical régulier ? *
                </label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="antecedents_medicaux.traitement_medical" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="antecedents_medicaux.traitement_medical" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage
                  name="antecedents_medicaux.traitement_medical"
                  component="div"
                  className="error-message"
                />
                {values.antecedents_medicaux.traitement_medical === 'oui' && (
                  <div className="form-group" style={{ marginTop: '1rem' }}>
                    <Field
                      as="textarea"
                      name="antecedents_medicaux.traitement_medical_details"
                      placeholder="Si oui, lequel ?"
                      rows={3}
                      className="form-control"
                    />
                    <ErrorMessage
                      name="antecedents_medicaux.traitement_medical_details"
                      component="div"
                      className="error-message"
                    />
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>
                  Avez-vous été hospitalisé dans les 12 derniers mois ? *
                </label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="antecedents_medicaux.hospitalisation_12mois" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="antecedents_medicaux.hospitalisation_12mois" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage
                  name="antecedents_medicaux.hospitalisation_12mois"
                  component="div"
                  className="error-message"
                />
                {values.antecedents_medicaux.hospitalisation_12mois === 'oui' && (
                  <div className="form-group" style={{ marginTop: '1rem' }}>
                    <Field
                      as="textarea"
                      name="antecedents_medicaux.hospitalisation_12mois_details"
                      placeholder="Si oui, pourquoi ?"
                      rows={3}
                      className="form-control"
                    />
                    <ErrorMessage
                      name="antecedents_medicaux.hospitalisation_12mois_details"
                      component="div"
                      className="error-message"
                    />
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>
                  Avez-vous subi une opération chirurgicale dans les 5 dernières années ? *
                </label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="antecedents_medicaux.operation_5ans" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="antecedents_medicaux.operation_5ans" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage
                  name="antecedents_medicaux.operation_5ans"
                  component="div"
                  className="error-message"
                />
                {values.antecedents_medicaux.operation_5ans === 'oui' && (
                  <div className="form-group" style={{ marginTop: '1rem' }}>
                    <Field
                      as="textarea"
                      name="antecedents_medicaux.operation_5ans_details"
                      placeholder="Si oui, préciser"
                      rows={3}
                      className="form-control"
                    />
                    <ErrorMessage
                      name="antecedents_medicaux.operation_5ans_details"
                      component="div"
                      className="error-message"
                    />
                  </div>
                )}
              </div>
            </section>

            {/* Section B: Symptômes récents */}
            <section className="form-section">
              <h2>B. Symptômes récents</h2>
              
              <div className="form-group">
                <label>
                  Avez-vous récemment ressenti :
                </label>
                <div className="checkbox-group" style={{ flexDirection: 'column' }}>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="symptomes_recents.douleurs_thoraciques" />
                    Douleurs thoraciques
                  </label>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="symptomes_recents.essoufflement" />
                    Essoufflement inhabituel
                  </label>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="symptomes_recents.vertiges" />
                    Vertiges fréquents
                  </label>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="symptomes_recents.perte_connaissance" />
                    Perte de connaissance
                  </label>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="symptomes_recents.fievre_persistante" />
                    Fièvre persistante
                  </label>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="symptomes_recents.saignements_anormaux" />
                    Saignements anormaux
                  </label>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="symptomes_recents.reactions_allergiques" />
                    Réactions allergiques sévères
                  </label>
                </div>
              </div>

              <div className="form-group">
                <label>
                  Êtes-vous enceinte ? (Pour femmes)
                </label>
                <Field
                  as="select"
                  name="symptomes_recents.enceinte"
                  className="form-control"
                >
                  <option value="">Sélectionnez...</option>
                  <option value="non">Non</option>
                  <option value="oui">Oui</option>
                  <option value="ne_s_applique_pas">Ne s'applique pas</option>
                </Field>
              </div>
            </section>

            {/* Section C: Maladies contagieuses ou risques infectieux */}
            <section className="form-section">
              <h2>C. Maladies contagieuses ou risques infectieux</h2>
              
              <div className="form-group">
                <label>
                  Avez-vous été diagnostiqué récemment avec :
                </label>
                <div className="checkbox-group" style={{ flexDirection: 'column' }}>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="maladies_contagieuses.paludisme" />
                    Paludisme
                  </label>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="maladies_contagieuses.tuberculose" />
                    Tuberculose
                  </label>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="maladies_contagieuses.hepatite" />
                    Hépatite
                  </label>
                  <label className="checkbox-label">
                    <Field type="checkbox" name="maladies_contagieuses.infections_respiratoires" />
                    Infections respiratoires sévères
                  </label>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="maladies_contagieuses.autre_maladie_infectieuse">
                  Autre maladie infectieuse
                </label>
                <Field
                  type="text"
                  id="maladies_contagieuses.autre_maladie_infectieuse"
                  name="maladies_contagieuses.autre_maladie_infectieuse"
                  className="form-control"
                  placeholder="Précisez si applicable"
                />
              </div>

              <div className="form-group">
                <label>
                  Avez-vous été en contact avec une personne gravement malade récemment ? *
                </label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="maladies_contagieuses.contact_personne_malade" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="maladies_contagieuses.contact_personne_malade" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage
                  name="maladies_contagieuses.contact_personne_malade"
                  component="div"
                  className="error-message"
                />
                {values.maladies_contagieuses.contact_personne_malade === 'oui' && (
                  <div className="form-group" style={{ marginTop: '1rem' }}>
                    <Field
                      as="textarea"
                      name="maladies_contagieuses.contact_personne_malade_details"
                      placeholder="Précisez les détails"
                      rows={3}
                      className="form-control"
                    />
                    <ErrorMessage
                      name="maladies_contagieuses.contact_personne_malade_details"
                      component="div"
                      className="error-message"
                    />
                  </div>
                )}
              </div>
            </section>

            {/* Section D: Déclaration */}
            <section className="form-section">
              <h2>D. Déclaration</h2>
              
              <div className="form-group">
                <label className="checkbox-label" style={{ alignItems: 'flex-start' }}>
                  <Field
                    type="checkbox"
                    name="declaration.rien_omis"
                    style={{ marginTop: '0.25rem' }}
                  />
                  <span>
                    Je déclare n'avoir rien omis dans ce questionnaire. *
                  </span>
                </label>
                <ErrorMessage
                  name="declaration.rien_omis"
                  component="div"
                  className="error-message"
                />
              </div>

              <div className="form-group">
                <label className="checkbox-label" style={{ alignItems: 'flex-start' }}>
                  <Field
                    type="checkbox"
                    name="declaration.fausse_declaration"
                    style={{ marginTop: '0.25rem' }}
                  />
                  <span>
                    Je reconnais que toute fausse déclaration entraînera la nullité des garanties. *
                  </span>
                </label>
                <ErrorMessage
                  name="declaration.fausse_declaration"
                  component="div"
                  className="error-message"
                />
              </div>

              <div className="legal-notice">
                <strong>Important :</strong> Les informations fournies dans ce questionnaire sont essentielles pour l'évaluation des risques. 
                Toute omission ou fausse déclaration peut entraîner la nullité de votre assurance.
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
                {mutation.isPending ? 'Enregistrement...' : 'Enregistrer le questionnaire'}
              </button>
            </div>
          </Form>
        )}
      </Formik>
    </div>
  )
}

