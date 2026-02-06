import type { Alerte, AssignedHospital } from '../types'

const sanitizeNumber = (value: unknown): number => {
  if (typeof value === 'number') {
    return value
  }
  if (typeof value === 'string') {
    const normalized = value
      .replace(',', '.')
      .trim()
    if (!normalized) {
      return Number.NaN
    }
    const parsed = Number(normalized)
    return Number.isFinite(parsed) ? parsed : Number.NaN
  }
  return Number.NaN
}

const toOptionalNumber = (value: unknown): number | null => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }
  if (typeof value === 'string') {
    const parsed = Number(value.replace(',', '.').trim())
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

const normalizeAssignedHospital = (hospital: any): AssignedHospital | undefined => {
  if (!hospital) {
    return undefined
  }
  return {
    id: hospital.id,
    nom: hospital.nom,
    adresse: hospital.adresse ?? undefined,
    ville: hospital.ville ?? undefined,
    pays: hospital.pays ?? undefined,
    telephone: hospital.telephone ?? undefined,
    email: hospital.email ?? undefined,
    latitude: sanitizeNumber(hospital.latitude),
    longitude: sanitizeNumber(hospital.longitude),
  }
}

export const normalizeAlerte = (raw: any): Alerte => {
  const assignedHospital = normalizeAssignedHospital(raw.assigned_hospital)
  const distance = toOptionalNumber(raw.distance_to_hospital_km)

  return {
    ...raw,
    latitude: sanitizeNumber(raw.latitude),
    longitude: sanitizeNumber(raw.longitude),
    assigned_hospital: assignedHospital,
    distance_to_hospital_km: distance,
  }
}



