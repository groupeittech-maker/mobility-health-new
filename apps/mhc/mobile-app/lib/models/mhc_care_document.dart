/// Libellés et constantes des bons / attestations MHC (alignés sur le web).
class MhcCareDocumentLabels {
  MhcCareDocumentLabels._();

  static const labels = <String, String>{
    'bpcu': "Bon de prise en charge d'urgence",
    'brpcu': "Bon de refus de prise en charge d'urgence",
    'bh': "Bon d'hospitalisation",
    'bph': "Bon de prolongation d'hospitalisation",
    'bs': 'Bulletin de sortie',
    'brs': 'Bon de rapatriement sanitaire',
    'ars': 'Attestation de retour de rapatriement sanitaire',
    'brf': 'Bon de rapatriement funéraire',
    'arf': 'Attestation de rapatriement funéraire',
    'certificat_deces': 'Certificat de décès',
  };

  static const refusalMotifs = [
    "Prestation ou pathologie exclue des garanties la police d'assurance voyage.",
    "Absence du caractère d'urgence médicale obligatoire.",
    "Sinistre survenu en dehors des dates de validité ou d'effet du contrat.",
    "Situation médicale présente avant la souscription de la police d'assurance",
  ];

  static String labelFor(String type) => labels[type] ?? type.toUpperCase();
}
