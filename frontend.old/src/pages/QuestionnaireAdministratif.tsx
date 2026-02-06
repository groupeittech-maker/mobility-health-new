import { useParams, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Formik, Form, Field, ErrorMessage } from 'formik'
import * as Yup from 'yup'
import { questionnairesApi } from '../api/questionnaires'
import { useState } from 'react'
import './Questionnaire.css'

const validationSchema = Yup.object({
  // 1. Informations personnelles
  nom: Yup.string().required('Le nom est requis'),
  prenom: Yup.string().required('Le prénom est requis'),
  date_naissance: Yup.date().required('La date de naissance est requise'),
  sexe: Yup.string().required('Le sexe est requis'),
  nationalite: Yup.string().required('La nationalité est requise'),
  profession: Yup.string().required('La profession est requise'),
  adresse_residence: Yup.string().required('L\'adresse de résidence est requise'),
  telephone: Yup.string().required('Le numéro de téléphone est requis'),
  email: Yup.string().email('Email invalide').required('L\'email est requis'),
  numero_piece_identite: Yup.string().required('Le numéro de pièce d\'identité est requis'),
  type_piece: Yup.string().required('Le type de pièce est requis'),
  date_delivrance: Yup.date().required('La date de délivrance est requise'),
  date_expiration: Yup.date().required('La date d\'expiration est requise'),
  lien_souscripteur: Yup.string(),

  // 2. Informations techniques
  deja_voyage: Yup.string().required('Ce champ est requis'),
  nombre_voyages_3ans: Yup.number().min(0, 'Le nombre doit être positif'),
  deja_expulse: Yup.string().required('Ce champ est requis'),
  deja_refuse_visa: Yup.string().required('Ce champ est requis'),
  motif_refus_visa: Yup.string().when('deja_refuse_visa', {
    is: 'oui',
    then: (schema) => schema.required('Le motif est requis si vous avez été refusé'),
    otherwise: (schema) => schema,
  }),
  transport_utilise: Yup.array().min(1, 'Sélectionnez au moins un moyen de transport'),
  activite_risque: Yup.string().required('Ce champ est requis'),
  activites_risque_details: Yup.array(),
  voyage_professionnel: Yup.string().required('Ce champ est requis'),
  transport_materiel: Yup.string().required('Ce champ est requis'),
  deja_assure_voyage: Yup.string().required('Ce champ est requis'),
  nom_assureur_precedent: Yup.string().when('deja_assure_voyage', {
    is: 'oui',
    then: (schema) => schema.required('Le nom de l\'assureur est requis'),
    otherwise: (schema) => schema,
  }),
  deja_sinistre_voyage: Yup.string().required('Ce champ est requis'),
  type_sinistre: Yup.string().when('deja_sinistre_voyage', {
    is: 'oui',
    then: (schema) => schema.required('Le type de sinistre est requis'),
    otherwise: (schema) => schema,
  }),
  indemnisation_recue: Yup.string().when('deja_sinistre_voyage', {
    is: 'oui',
    then: (schema) => schema.required('Ce champ est requis'),
    otherwise: (schema) => schema,
  }),

  // 3. Déclarations
  certifie_exactitude: Yup.boolean().oneOf([true], 'Vous devez certifier l\'exactitude des informations'),
  accepte_collecte_donnees: Yup.boolean().oneOf([true], 'Vous devez accepter la collecte de données'),
})

interface QuestionnaireAdministratifValues {
  // Informations personnelles
  nom: string
  prenom: string
  date_naissance: string
  sexe: string
  nationalite: string
  profession: string
  adresse_residence: string
  telephone: string
  email: string
  numero_piece_identite: string
  type_piece: string
  date_delivrance: string
  date_expiration: string
  lien_souscripteur: string
  documents: FileList | null

  // Informations techniques
  deja_voyage: string
  nombre_voyages_3ans: number
  deja_expulse: string
  deja_refuse_visa: string
  motif_refus_visa: string
  transport_utilise: string[]
  activite_risque: string
  activites_risque_details: string[]
  activite_risque_autre: string
  voyage_professionnel: string
  transport_materiel: string
  deja_assure_voyage: string
  nom_assureur_precedent: string
  deja_sinistre_voyage: string
  type_sinistre: string
  indemnisation_recue: string

  // Déclarations
  certifie_exactitude: boolean
  accepte_collecte_donnees: boolean
}

export default function QuestionnaireAdministratif() {
  const { subscriptionId } = useParams<{ subscriptionId: string }>()
  const navigate = useNavigate()
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])

  const mutation = useMutation({
    mutationFn: (reponses: Record<string, any>) =>
      questionnairesApi.createAdministratif(Number(subscriptionId), reponses),
    onSuccess: () => {
      alert('Questionnaire administratif/technique enregistré avec succès!')
      navigate(-1)
    },
    onError: (error: any) => {
      alert(`Erreur: ${error.response?.data?.detail || error.message}`)
    },
  })

  const initialValues: QuestionnaireAdministratifValues = {
    nom: '',
    prenom: '',
    date_naissance: '',
    sexe: '',
    nationalite: '',
    profession: '',
    adresse_residence: '',
    telephone: '',
    email: '',
    numero_piece_identite: '',
    type_piece: '',
    date_delivrance: '',
    date_expiration: '',
    lien_souscripteur: '',
    documents: null,
    deja_voyage: '',
    nombre_voyages_3ans: 0,
    deja_expulse: '',
    deja_refuse_visa: '',
    motif_refus_visa: '',
    transport_utilise: [],
    activite_risque: '',
    activites_risque_details: [],
    activite_risque_autre: '',
    voyage_professionnel: '',
    transport_materiel: '',
    deja_assure_voyage: '',
    nom_assureur_precedent: '',
    deja_sinistre_voyage: '',
    type_sinistre: '',
    indemnisation_recue: '',
    certifie_exactitude: false,
    accepte_collecte_donnees: false,
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>, setFieldValue: any) => {
    const files = event.target.files
    if (files) {
      const fileArray = Array.from(files)
      setUploadedFiles(fileArray)
      setFieldValue('documents', files)
    }
  }

  return (
    <div className="questionnaire-container">
      <div className="questionnaire-header">
        <h1>Questionnaire Administratif / Technique</h1>
        <p>Complément au questionnaire médical – utilisé pour l'analyse du risque, la tarification, et l'émission de l'attestation provisoire</p>
        <p className="subtitle">Souscription #{subscriptionId}</p>
      </div>

      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={(values, { setSubmitting }) => {
          // Préparer les données pour l'API
          const reponses = {
            // Informations personnelles
            informations_personnelles: {
              nom: values.nom,
              prenom: values.prenom,
              date_naissance: values.date_naissance,
              sexe: values.sexe,
              nationalite: values.nationalite,
              profession: values.profession,
              adresse_residence: values.adresse_residence,
              telephone: values.telephone,
              email: values.email,
              piece_identite: {
                numero: values.numero_piece_identite,
                type: values.type_piece,
                date_delivrance: values.date_delivrance,
                date_expiration: values.date_expiration,
              },
              lien_souscripteur: values.lien_souscripteur || null,
              documents_uploades: uploadedFiles.map(f => f.name),
            },
            // Informations techniques
            informations_techniques: {
              voyages_precedents: {
                deja_voyage: values.deja_voyage,
                nombre_voyages_3ans: values.nombre_voyages_3ans,
                deja_expulse: values.deja_expulse,
                deja_refuse_visa: values.deja_refuse_visa,
                motif_refus_visa: values.motif_refus_visa || null,
              },
              risques_voyage: {
                transport_utilise: values.transport_utilise,
                activite_risque: values.activite_risque,
                activites_risque_details: values.activites_risque_details,
                activite_risque_autre: values.activite_risque_autre || null,
                voyage_professionnel: values.voyage_professionnel,
                transport_materiel: values.transport_materiel,
              },
              couvertures_anterieures: {
                deja_assure_voyage: values.deja_assure_voyage,
                nom_assureur_precedent: values.nom_assureur_precedent || null,
                deja_sinistre_voyage: values.deja_sinistre_voyage,
                type_sinistre: values.type_sinistre || null,
                indemnisation_recue: values.indemnisation_recue || null,
              },
            },
            // Déclarations
            declarations: {
              certifie_exactitude: values.certifie_exactitude,
              accepte_collecte_donnees: values.accepte_collecte_donnees,
              date_signature: new Date().toISOString(),
            },
          }

          mutation.mutate(reponses, {
            onSettled: () => {
              setSubmitting(false)
            },
          })
        }}
      >
        {({ values, setFieldValue, isSubmitting }) => (
          <Form className="questionnaire-form">
            {/* Section 1: Informations personnelles */}
            <section className="form-section">
              <h2>1. Informations personnelles de l'assuré</h2>
              <p className="section-description">
                Objectif : Identifier clairement l'assuré et son statut administratif.
              </p>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="nom">Nom *</label>
                  <Field type="text" id="nom" name="nom" className="form-control" />
                  <ErrorMessage name="nom" component="div" className="error-message" />
                </div>

                <div className="form-group">
                  <label htmlFor="prenom">Prénom *</label>
                  <Field type="text" id="prenom" name="prenom" className="form-control" />
                  <ErrorMessage name="prenom" component="div" className="error-message" />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="date_naissance">Date de naissance *</label>
                  <Field type="date" id="date_naissance" name="date_naissance" className="form-control" />
                  <ErrorMessage name="date_naissance" component="div" className="error-message" />
                </div>

                <div className="form-group">
                  <label htmlFor="sexe">Sexe *</label>
                  <Field as="select" id="sexe" name="sexe" className="form-control">
                    <option value="">Sélectionnez...</option>
                    <option value="M">Masculin</option>
                    <option value="F">Féminin</option>
                    <option value="Autre">Autre</option>
                  </Field>
                  <ErrorMessage name="sexe" component="div" className="error-message" />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="nationalite">Nationalité *</label>
                  <Field type="text" id="nationalite" name="nationalite" className="form-control" />
                  <ErrorMessage name="nationalite" component="div" className="error-message" />
                </div>

                <div className="form-group">
                  <label htmlFor="profession">Profession *</label>
                  <Field type="text" id="profession" name="profession" className="form-control" />
                  <ErrorMessage name="profession" component="div" className="error-message" />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="adresse_residence">Adresse de résidence *</label>
                <Field as="textarea" id="adresse_residence" name="adresse_residence" className="form-control" rows={3} />
                <ErrorMessage name="adresse_residence" component="div" className="error-message" />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="telephone">Numéro de téléphone *</label>
                  <Field type="tel" id="telephone" name="telephone" className="form-control" />
                  <ErrorMessage name="telephone" component="div" className="error-message" />
                </div>

                <div className="form-group">
                  <label htmlFor="email">Adresse e-mail *</label>
                  <Field type="email" id="email" name="email" className="form-control" />
                  <ErrorMessage name="email" component="div" className="error-message" />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="numero_piece_identite">Numéro pièce d'identité (Passeport / CNI) *</label>
                <Field type="text" id="numero_piece_identite" name="numero_piece_identite" className="form-control" />
                <ErrorMessage name="numero_piece_identite" component="div" className="error-message" />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="type_piece">Type de pièce *</label>
                  <Field as="select" id="type_piece" name="type_piece" className="form-control">
                    <option value="">Sélectionnez...</option>
                    <option value="passeport">Passeport</option>
                    <option value="cni">Carte Nationale d'Identité</option>
                    <option value="autre">Autre</option>
                  </Field>
                  <ErrorMessage name="type_piece" component="div" className="error-message" />
                </div>

                <div className="form-group">
                  <label htmlFor="date_delivrance">Date de délivrance *</label>
                  <Field type="date" id="date_delivrance" name="date_delivrance" className="form-control" />
                  <ErrorMessage name="date_delivrance" component="div" className="error-message" />
                </div>

                <div className="form-group">
                  <label htmlFor="date_expiration">Date d'expiration *</label>
                  <Field type="date" id="date_expiration" name="date_expiration" className="form-control" />
                  <ErrorMessage name="date_expiration" component="div" className="error-message" />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="lien_souscripteur">Lien avec le souscripteur (si différent)</label>
                <Field as="select" id="lien_souscripteur" name="lien_souscripteur" className="form-control">
                  <option value="">N/A (même personne)</option>
                  <option value="conjoint">Conjoint(e)</option>
                  <option value="enfant">Enfant</option>
                  <option value="parent">Parent</option>
                  <option value="autre">Autre</option>
                </Field>
              </div>

              <div className="form-group">
                <label htmlFor="documents">Joindre des documents</label>
                <input
                  type="file"
                  id="documents"
                  name="documents"
                  multiple
                  onChange={(e) => handleFileChange(e, setFieldValue)}
                  className="form-control"
                />
                {uploadedFiles.length > 0 && (
                  <div className="uploaded-files">
                    <p>Fichiers sélectionnés :</p>
                    <ul>
                      {uploadedFiles.map((file, index) => (
                        <li key={index}>{file.name}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>

            {/* Section 2: Informations techniques */}
            <section className="form-section">
              <h2>2. Informations techniques pour la couverture</h2>
              <p className="section-description">
                Objectif : Analyse technique du risque (non médical).
              </p>

              <h3>2.1. Informations sur les précédents voyages</h3>
              <div className="form-group">
                <label>Avez-vous déjà voyagé hors du pays ? *</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="deja_voyage" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="deja_voyage" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage name="deja_voyage" component="div" className="error-message" />
              </div>

              {values.deja_voyage === 'oui' && (
                <div className="form-group">
                  <label htmlFor="nombre_voyages_3ans">Nombre de voyages au cours des 3 dernières années</label>
                  <Field type="number" id="nombre_voyages_3ans" name="nombre_voyages_3ans" className="form-control" min="0" />
                </div>
              )}

              <div className="form-group">
                <label>Avez-vous déjà été expulsé/refoulé d'un pays ? *</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="deja_expulse" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="deja_expulse" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage name="deja_expulse" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label>Avez-vous déjà été refusé de visa ? *</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="deja_refuse_visa" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="deja_refuse_visa" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage name="deja_refuse_visa" component="div" className="error-message" />
              </div>

              {values.deja_refuse_visa === 'oui' && (
                <div className="form-group">
                  <label htmlFor="motif_refus_visa">Motif du refus *</label>
                  <Field as="textarea" id="motif_refus_visa" name="motif_refus_visa" className="form-control" rows={3} />
                  <ErrorMessage name="motif_refus_visa" component="div" className="error-message" />
                </div>
              )}

              <h3>2.2. Risques liés au voyage</h3>
              <div className="form-group">
                <label>Transport utilisé *</label>
                <div className="checkbox-group">
                  {['avion', 'bateau', 'vehicule', 'autres'].map((transport) => (
                    <label key={transport} className="checkbox-label">
                      <Field
                        type="checkbox"
                        name="transport_utilise"
                        value={transport}
                        checked={values.transport_utilise.includes(transport)}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                          const newValue = e.target.checked
                            ? [...values.transport_utilise, transport]
                            : values.transport_utilise.filter((t) => t !== transport)
                          setFieldValue('transport_utilise', newValue)
                        }}
                      />
                      {transport.charAt(0).toUpperCase() + transport.slice(1)}
                    </label>
                  ))}
                </div>
                <ErrorMessage name="transport_utilise" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label>Allez-vous pratiquer une activité à risque ? *</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="activite_risque" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="activite_risque" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage name="activite_risque" component="div" className="error-message" />
              </div>

              {values.activite_risque === 'oui' && (
                <>
                  <div className="form-group">
                    <label>Types d'activités à risque</label>
                    <div className="checkbox-group">
                      {[
                        { value: 'sports_extremes', label: 'Sports extrêmes' },
                        { value: 'travail_hauteur', label: 'Travail en hauteur' },
                        { value: 'zones_sensibles', label: 'Zones sensibles' },
                        { value: 'operation_machines', label: 'Opération de machines' },
                      ].map((activite) => (
                        <label key={activite.value} className="checkbox-label">
                          <Field
                            type="checkbox"
                            name="activites_risque_details"
                            value={activite.value}
                            checked={values.activites_risque_details.includes(activite.value)}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                              const newValue = e.target.checked
                                ? [...values.activites_risque_details, activite.value]
                                : values.activites_risque_details.filter((a) => a !== activite.value)
                              setFieldValue('activites_risque_details', newValue)
                            }}
                          />
                          {activite.label}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="form-group">
                    <label htmlFor="activite_risque_autre">Autres activités à risque</label>
                    <Field type="text" id="activite_risque_autre" name="activite_risque_autre" className="form-control" />
                  </div>
                </>
              )}

              <div className="form-group">
                <label>Voyage professionnel impliquant une responsabilité particulière ? *</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="voyage_professionnel" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="voyage_professionnel" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage name="voyage_professionnel" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label>Transport de matériel professionnel important ? *</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="transport_materiel" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="transport_materiel" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage name="transport_materiel" component="div" className="error-message" />
              </div>

              <h3>2.3. Couvertures antérieures</h3>
              <div className="form-group">
                <label>Avez-vous déjà souscrit une assurance voyage ? *</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="deja_assure_voyage" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="deja_assure_voyage" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage name="deja_assure_voyage" component="div" className="error-message" />
              </div>

              {values.deja_assure_voyage === 'oui' && (
                <div className="form-group">
                  <label htmlFor="nom_assureur_precedent">Nom de l'assureur précédent *</label>
                  <Field type="text" id="nom_assureur_precedent" name="nom_assureur_precedent" className="form-control" />
                  <ErrorMessage name="nom_assureur_precedent" component="div" className="error-message" />
                </div>
              )}

              <div className="form-group">
                <label>Avez-vous déjà déclaré un sinistre voyage ? *</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <Field type="radio" name="deja_sinistre_voyage" value="oui" />
                    Oui
                  </label>
                  <label className="radio-label">
                    <Field type="radio" name="deja_sinistre_voyage" value="non" />
                    Non
                  </label>
                </div>
                <ErrorMessage name="deja_sinistre_voyage" component="div" className="error-message" />
              </div>

              {values.deja_sinistre_voyage === 'oui' && (
                <>
                  <div className="form-group">
                    <label htmlFor="type_sinistre">Type de sinistre *</label>
                    <Field as="textarea" id="type_sinistre" name="type_sinistre" className="form-control" rows={3} />
                    <ErrorMessage name="type_sinistre" component="div" className="error-message" />
                  </div>
                  <div className="form-group">
                    <label>Indemnisation reçue ? *</label>
                    <div className="radio-group">
                      <label className="radio-label">
                        <Field type="radio" name="indemnisation_recue" value="oui" />
                        Oui
                      </label>
                      <label className="radio-label">
                        <Field type="radio" name="indemnisation_recue" value="non" />
                        Non
                      </label>
                    </div>
                    <ErrorMessage name="indemnisation_recue" component="div" className="error-message" />
                  </div>
                </>
              )}
            </section>

            {/* Section 3: Déclarations */}
            <section className="form-section">
              <h2>3. Déclarations et consentements</h2>
              <p className="section-description">
                Objectif : Validation légale pour émettre l'attestation provisoire.
              </p>

              <div className="form-group">
                <label className="checkbox-label">
                  <Field type="checkbox" name="certifie_exactitude" />
                  Je certifie que les informations fournies sont exactes. *
                </label>
                <ErrorMessage name="certifie_exactitude" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <Field type="checkbox" name="accepte_collecte_donnees" />
                  J'accepte la collecte de mes données personnelles pour l'analyse du risque. *
                </label>
                <ErrorMessage name="accepte_collecte_donnees" component="div" className="error-message" />
              </div>

              <div className="form-group">
                <p className="legal-notice">
                  <strong>Note légale :</strong> Je comprends que toute fausse déclaration entraîne la nullité de la police.
                </p>
              </div>
            </section>

            <div className="form-actions">
              <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
                Annuler
              </button>
              <button type="submit" disabled={isSubmitting} className="btn-primary">
                {isSubmitting ? 'Enregistrement...' : 'Enregistrer le questionnaire'}
              </button>
            </div>
          </Form>
        )}
      </Formik>
    </div>
  )
}

