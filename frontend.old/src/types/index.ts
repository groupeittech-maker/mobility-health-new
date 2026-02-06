export interface AgentComptableSummary {
  id: number
  email: string
  username: string
  full_name?: string
  role: string
  is_active: boolean
}

export interface Assureur {
  id: number
  nom: string
  pays: string
  logo_url?: string
  adresse?: string
  telephone?: string
  agent_comptable_id?: number | null
  agent_comptable?: AgentComptableSummary | null
  created_at: string
  updated_at: string
}

export interface ProduitAssurance {
  id: number
  code: string
  nom: string
  description?: string
  cout: number
  cle_repartition: string
  est_actif: boolean
  duree_validite_jours?: number
  conditions?: string
  garanties?: Garantie[] | string | any
  assureur?: string
  assureur_id?: number | null
  assureur_details?: Assureur | null
  image_url?: string
  version?: string
  zones_geographiques?: ZonesGeographiques
  duree_min_jours?: number
  duree_max_jours?: number
  reconduction_possible?: boolean
  couverture_multi_entrees?: boolean
  age_minimum?: number
  age_maximum?: number
  conditions_sante?: string
  categories_assures?: string[]
  exclusions_generales?: string[]
  created_at: string
  updated_at: string
}

export interface ZonesGeographiques {
  zones?: string[]  // Ex: ["Afrique", "Europe", "Monde"]
  pays_eligibles?: string[]  // Codes ISO des pays
  pays_exclus?: string[]  // Codes ISO des pays
  specificites?: string[]  // Ex: ["pays_en_guerre", "sanctions_internationales"]
}

export interface Garantie {
  id?: string  // ID temporaire pour la gestion dans le formulaire
  nom: string
  description: string
  plafond?: number
  franchise?: number
  delai_carence?: number  // En jours
  conditions_activation?: string
  exclusions_specifiques?: string[]
  devise?: string  // EUR, USD, XOF, XAF
}

export interface HistoriquePrix {
  id: number
  produit_assurance_id: number
  ancien_prix?: number
  nouveau_prix: number
  raison_modification?: string
  modifie_par_user_id?: number
  created_at: string
  updated_at: string
}

export interface ProjetVoyage {
  id: number
  user_id: number
  titre: string
  description?: string
  destination: string
  date_depart: string
  date_retour?: string
  nombre_participants: number
  statut: string
  notes?: string
  budget_estime?: number
  created_at: string
  updated_at: string
}

export interface Souscription {
  id: number
  user_id: number
  produit_assurance_id: number
  projet_voyage_id?: number
  numero_souscription: string
  prix_applique: number
  date_debut: string
  date_fin?: string
  statut: string
  notes?: string
  validation_medicale?: string
  validation_medicale_par?: number
  validation_medicale_date?: string
  validation_medicale_notes?: string
  validation_technique?: string
  validation_technique_par?: number
  validation_technique_date?: string
  validation_technique_notes?: string
  validation_finale?: string
  validation_finale_par?: number
  validation_finale_date?: string
  validation_finale_notes?: string
  created_at: string
  updated_at: string
}

export interface AssignedHospital {
  id: number
  nom: string
  adresse?: string
  ville?: string
  pays?: string
  telephone?: string
  email?: string
  latitude: number
  longitude: number
}

export interface Alerte {
  id: number
  user_id: number
  souscription_id?: number
  numero_alerte: string
  latitude: number
  longitude: number
  adresse?: string
  description?: string
  statut: string
  priorite: string
  created_at: string
  updated_at: string
  assigned_hospital?: AssignedHospital
  distance_to_hospital_km?: number | null
  user_full_name?: string
  user_email?: string
}

export interface Sinistre {
  id: number
  alerte_id: number
  souscription_id?: number
  hospital_id?: number
  numero_sinistre: string
  description?: string
  statut: string
  agent_sinistre_id?: number
  medecin_referent_id?: number
  notes?: string
  created_at: string
  updated_at: string
}

export interface Hospital {
  id: number
  nom: string
  adresse?: string
  ville?: string
  pays?: string
  latitude: number
  longitude: number
  est_actif: boolean
  created_at: string
  updated_at: string
  code_postal?: string
  telephone?: string
  email?: string
  specialites?: string
  capacite_lits?: number
  notes?: string
}

export interface HospitalMedicalTarif {
  id: number
  hospital_id: number
  nom: string
  montant: number
  code?: string | null
  description?: string | null
  created_at: string
  updated_at: string
}

export interface HospitalMedicalCatalogDefaults {
  hourly_rate: number
  default_act_price: number
  default_exam_price: number
}

export interface HospitalMedicalCatalog {
  hospital_id: number
  actes: HospitalMedicalTarif[]
  examens: HospitalMedicalTarif[]
  defaults: HospitalMedicalCatalogDefaults
}

export interface HospitalMarker {
  id: number
  nom: string
  latitude: number | string
  longitude: number | string
  ville?: string
  pays?: string
  est_actif: boolean
  specialites?: string
  adresse?: string
}

export interface HospitalReceptionist {
  id: number
  email: string
  username: string
  full_name?: string
  is_active: boolean
  role: string
  hospital_id?: number
}

export interface HospitalStayDoctorSummary {
  id: number
  full_name?: string | null
  email?: string | null
  username?: string | null
}

export interface HospitalStayPatientSummary {
  id: number
  full_name?: string | null
  email?: string | null
}

export interface HospitalStaySinistreSummary {
  id: number
  numero_sinistre?: string | null
  statut?: string | null
  description?: string | null
}

export interface HospitalStayInvoiceSummary {
  id: number
  numero_facture: string
  statut: string
  montant_ttc: number
  created_at: string
  validation_medicale?: string | null
  validation_sinistre?: string | null
  validation_compta?: string | null
}

export interface HospitalStay {
  id: number
  sinistre_id: number
  sinistre?: HospitalStaySinistreSummary | null
  hospital_id: number
  patient_id?: number | null
  patient?: HospitalStayPatientSummary | null
  doctor_id?: number | null
  assigned_doctor?: HospitalStayDoctorSummary | null
  created_by_id?: number | null
  status: string
  report_status?: string | null
  started_at?: string | null
  ended_at?: string | null
  orientation_notes?: string | null
  report_motif_consultation?: string | null
  report_motif_hospitalisation?: string | null
  report_duree_sejour_heures?: number | null
  report_actes: string[]
  report_examens: string[]
  report_resume?: string | null
  report_observations?: string | null
  report_submitted_at?: string | null
  validated_by_id?: number | null
  validated_at?: string | null
  validation_notes?: string | null
  invoice?: HospitalStayInvoiceSummary | null
  created_at: string
  updated_at: string
}

export type CleRepartition = 
  | 'par_personne'
  | 'par_groupe'
  | 'par_duree'
  | 'par_destination'
  | 'fixe'

export type Currency = 'EUR' | 'USD' | 'XOF' | 'XAF'

export type CategorieAssure = 'individuel' | 'famille' | 'groupe' | 'entreprise'
