"""Nomenclature MHC : codes opération, codes pays et structures de références.

Source : nomenclature_des_références_MHC.xlsx + Référentiel documentaire et tarifaire MHC.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Tuple


class MhcOperationCode(str, Enum):
    POLICE = "10"
    SINISTRE = "11"
    ATTESTATION_ASSURANCE = "101"
    BON_ANNULATION_POLICE = "102"
    BON_RESILIATION_POLICE = "103"
    BON_RENOUVELLEMENT = "104"
    BPCU = "111"
    BRPCU = "112"
    BH = "113"
    BS = "114"
    BRS = "115"
    BRF = "116"
    BPH = "117"
    CERTIFICAT_DECES = "118"
    ARS = "119"  # Attestation de retour de rapatriement sanitaire (code non fourni dans le tableur)
    ARF = "120"  # Attestation de rapatriement funéraire (code non fourni dans le tableur)


class MhcCareDocumentType(str, Enum):
    BPCU = "bpcu"
    BRPCU = "brpcu"
    BH = "bh"
    BPH = "bph"
    BS = "bs"
    BRS = "brs"
    ARS = "ars"
    BRF = "brf"
    ARF = "arf"


class MhcCareDocumentStatus(str, Enum):
    EMI = "emi"
    EXPIRE = "expire"
    CLOTURE = "cloture"


class MhcExitMode(str, Enum):
    GUERISON = "guerison"
    AMBULATOIRE = "ambulatoire"
    TRANSFERT = "transfert"
    RAPATRIEMENT_SANITAIRE = "rapatriement_sanitaire"
    AUTRE = "autre"


OPERATION_LABELS: Dict[str, str] = {
    MhcOperationCode.POLICE.value: "Police",
    MhcOperationCode.SINISTRE.value: "Sinistre",
    MhcOperationCode.ATTESTATION_ASSURANCE.value: "Attestation d'assurance",
    MhcOperationCode.BON_ANNULATION_POLICE.value: "Bon d'annulation de police",
    MhcOperationCode.BON_RESILIATION_POLICE.value: "Bon de résiliation de police",
    MhcOperationCode.BON_RENOUVELLEMENT.value: "Bon de renouvellement",
    MhcOperationCode.BPCU.value: "Bon de prise en charge d'urgence",
    MhcOperationCode.BRPCU.value: "Bon de refus de prise en charge d'urgence",
    MhcOperationCode.BH.value: "Bon d'hospitalisation",
    MhcOperationCode.BS.value: "Bulletin de sortie",
    MhcOperationCode.BRS.value: "Bon de rapatriement sanitaire",
    MhcOperationCode.BRF.value: "Bon de rapatriement funéraire",
    MhcOperationCode.BPH.value: "Bon de prolongation d'hospitalisation",
    MhcOperationCode.CERTIFICAT_DECES.value: "Certificat de décès",
    MhcOperationCode.ARS.value: "Attestation de retour de rapatriement sanitaire",
    MhcOperationCode.ARF.value: "Attestation de rapatriement funéraire",
}

DOCUMENT_TYPE_TO_OPERATION: Dict[MhcCareDocumentType, MhcOperationCode] = {
    MhcCareDocumentType.BPCU: MhcOperationCode.BPCU,
    MhcCareDocumentType.BRPCU: MhcOperationCode.BRPCU,
    MhcCareDocumentType.BH: MhcOperationCode.BH,
    MhcCareDocumentType.BPH: MhcOperationCode.BPH,
    MhcCareDocumentType.BS: MhcOperationCode.BS,
    MhcCareDocumentType.BRS: MhcOperationCode.BRS,
    MhcCareDocumentType.BRF: MhcOperationCode.BRF,
    MhcCareDocumentType.ARS: MhcOperationCode.ARS,
    MhcCareDocumentType.ARF: MhcOperationCode.ARF,
}

DOCUMENT_TITLES: Dict[MhcCareDocumentType, str] = {
    MhcCareDocumentType.BPCU: "Bon de prise en charge d'urgence",
    MhcCareDocumentType.BRPCU: "Bon de refus de prise en charge d'urgence",
    MhcCareDocumentType.BH: "Bon d'hospitalisation",
    MhcCareDocumentType.BPH: "Bon de prolongation d'hospitalisation",
    MhcCareDocumentType.BS: "Bulletin de sortie",
    MhcCareDocumentType.BRS: "Bon de rapatriement sanitaire",
    MhcCareDocumentType.ARS: "Attestation de retour de rapatriement sanitaire",
    MhcCareDocumentType.BRF: "Bon de rapatriement funéraire",
    MhcCareDocumentType.ARF: "Attestation de rapatriement funéraire",
}

# Validité en heures (None = pas de délai contractuel d'expiration)
DOCUMENT_VALIDITY_HOURS: Dict[MhcCareDocumentType, Optional[int]] = {
    MhcCareDocumentType.BPCU: 24,
    MhcCareDocumentType.BRPCU: None,
    MhcCareDocumentType.BH: 72,
    MhcCareDocumentType.BPH: 24,
    MhcCareDocumentType.BS: None,
    MhcCareDocumentType.BRS: None,
    MhcCareDocumentType.ARS: None,
    MhcCareDocumentType.BRF: None,
    MhcCareDocumentType.ARF: None,
}

EXIT_MODE_LABELS: Dict[str, str] = {
    MhcExitMode.GUERISON.value: "Guérison / amélioration — retour au domicile sans prescription médicale",
    MhcExitMode.AMBULATOIRE.value: "Sortie sous traitement médical ambulatoire avec prescription",
    MhcExitMode.TRANSFERT.value: "Transfert inter-hospitalier",
    MhcExitMode.RAPATRIEMENT_SANITAIRE.value: "Rapatriement sanitaire organisé par Mobility Health Care",
    MhcExitMode.AUTRE.value: "Autre modalité",
}

# Codes pays MHC (001-200) — feuille « Code Pays »
MHC_COUNTRY_CODES: Dict[int, str] = {
    1: "Angola",
    2: "Bénin",
    3: "Botswana",
    4: "Burkina Faso",
    5: "Burundi",
    6: "Cameroun",
    7: "Cap-Vert",
    8: "Rép. Centrafricaine",
    9: "Tchad",
    10: "Comores",
    11: "Congo",
    12: "Rép. Dém. du Congo",
    13: "Côte d'Ivoire",
    14: "Djibouti",
    15: "Égypte",
    16: "Guinée Équatoriale",
    17: "Érythrée",
    18: "Eswatini",
    19: "Éthiopie",
    20: "Gabon",
    21: "Gambie",
    22: "Ghana",
    23: "Guinée",
    24: "Guinée-Bissau",
    25: "Kenya",
    26: "Lesotho",
    27: "Liberia",
    28: "Libye",
    29: "Madagascar",
    30: "Malawi",
    31: "Mali",
    32: "Mauritanie",
    33: "Maurice",
    34: "Maroc",
    35: "Mozambique",
    36: "Namibie",
    37: "Niger",
    38: "Nigeria",
    39: "Rwanda",
    40: "Sao Tomé-et-Principe",
    41: "Sénégal",
    42: "Seychelles",
    43: "Sierra Leone",
    44: "Afrique du Sud",
    45: "Soudan du Sud",
    46: "Tanzanie",
    47: "Togo",
    48: "Tunisie",
    49: "Ouganda",
    50: "Zambie",
    51: "Zimbabwe",
    52: "Inde",
    53: "Émirats Arabes Unis",
    54: "Turquie",
    55: "Chine",
    56: "France",
    57: "Algérie",
}

_COUNTRY_ALIASES: Dict[str, int] = {
    "rdc": 12,
    "republique democratique du congo": 12,
    "democratic republic of the congo": 12,
    "congo-kinshasa": 12,
    "congo brazzaville": 11,
    "republique du congo": 11,
    "cote d'ivoire": 13,
    "ivory coast": 13,
    "south africa": 44,
    "rsa": 44,
    "uae": 53,
    "emirates": 53,
    "united arab emirates": 53,
    "central african republic": 8,
    "centrafrique": 8,
    "swaziland": 18,
    "france": 56,
    "ue": 56,
    "union europeenne": 56,
    "malawi": 30,
    "congo": 11,
}


def pad6(value: int) -> str:
    return f"{int(value):06d}"


def pad3(value: int) -> str:
    return f"{max(1, min(int(value), 999)):03d}"


def pad2(value: int) -> str:
    return f"{int(value):02d}"


def country_code_from_name(name: Optional[str], default: int = 11) -> int:
    """Retourne le code pays MHC (1-57) à partir d'un libellé. Défaut : Congo (siège MHC)."""
    if not name:
        return default
    raw = str(name).strip()
    if raw.isdigit():
        code = int(raw)
        return code if code in MHC_COUNTRY_CODES else default
    key = (
        raw.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ô", "o")
        .replace("î", "i")
        .replace("ç", "c")
        .replace("’", "'")
    )
    if key in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[key]
    for code, label in MHC_COUNTRY_CODES.items():
        label_key = (
            label.lower()
            .replace("é", "e")
            .replace("è", "e")
            .replace("ê", "e")
            .replace("à", "a")
            .replace("ô", "o")
            .replace("î", "i")
            .replace("ç", "c")
            .replace("’", "'")
        )
        if key == label_key or key in label_key or label_key in key:
            return code
    return default


def code_from_id(entity_id: Optional[int], max_value: int = 500) -> int:
    if not entity_id:
        return 1
    return max(1, min(int(entity_id), max_value))


def format_police_number(order: int, country_code: int, assureur_code: int, year: int) -> str:
    return f"{pad6(order)}-{MhcOperationCode.POLICE.value}-{pad3(country_code)}-{pad3(assureur_code)}-{year}"


def format_sinistre_number(order: int, country_code: int, assureur_code: int, year: int) -> str:
    return f"{pad6(order)}-{MhcOperationCode.SINISTRE.value}-{pad3(country_code)}-{pad3(assureur_code)}-{year}"


def format_bpcu_like_number(
    order: int,
    sinistre_order: int,
    operation: MhcOperationCode,
    partner_code: int,
    doctor_code: int,
    year: int,
) -> str:
    return (
        f"{pad6(order)}-{pad6(sinistre_order)}-{operation.value}-"
        f"{pad3(partner_code)}-{pad3(doctor_code)}-{year}"
    )


def format_simple_document_number(order: int, sinistre_order: int, operation: MhcOperationCode) -> str:
    return f"{pad6(order)}-{pad6(sinistre_order)}-{operation.value}"


def format_bph_number(bh_order: int, sequence: int, sinistre_order: int) -> str:
    """N° prolongation : n° du bon d'hospitalisation / séquence + sinistre + 117."""
    return f"{pad6(bh_order)}/{pad2(sequence)}-{pad6(sinistre_order)}-{MhcOperationCode.BPH.value}"


def parse_order_from_reference(numero: Optional[str]) -> Optional[int]:
    if not numero:
        return None
    token = str(numero).split("-")[0].split("/")[0]
    digits = "".join(ch for ch in token if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def parse_sinistre_order(numero_sinistre: Optional[str]) -> int:
    order = parse_order_from_reference(numero_sinistre)
    return order or 1


def document_catalog() -> list:
    catalog = []
    for doc_type in MhcCareDocumentType:
        catalog.append(
            {
                "type": doc_type.value,
                "titre": DOCUMENT_TITLES[doc_type],
                "code_operation": DOCUMENT_TYPE_TO_OPERATION[doc_type].value,
                "validite_heures": DOCUMENT_VALIDITY_HOURS[doc_type],
            }
        )
    return catalog
