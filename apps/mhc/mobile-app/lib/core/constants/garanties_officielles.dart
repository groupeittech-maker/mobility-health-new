/// Tableau officiel des garanties et exclusions Mobility Health Care.
/// Source : « TABLEAU DE GARANTIES & EXCLUSIONS.docx » (revue app 17/10/2026).
/// Affiché sur la fiche produit (mobile + web) — ne pas modifier sans
/// validation métier.
library;

/// Une ligne de garantie : [prestation] et [plafond] affichés en tableau.
class GarantieOfficielle {
  const GarantieOfficielle(this.prestation, this.plafond);

  final String prestation;
  final String plafond;
}

/// Un groupe de garanties (en-tête de section du tableau officiel).
class GarantieCategorieOfficielle {
  const GarantieCategorieOfficielle(this.titre, this.lignes, {this.sousTitre});

  final String titre;
  final String? sousTitre;
  final List<GarantieOfficielle> lignes;
}

/// Une exclusion officielle : [titre] en gras + [texte] intégral.
class ExclusionOfficielle {
  const ExclusionOfficielle(this.numero, this.titre, this.texte);

  final int numero;
  final String titre;
  final String texte;
}

const List<GarantieCategorieOfficielle> kCategoriesGarantiesOfficielles = [
  GarantieCategorieOfficielle('FRAIS MÉDICAUX', [
    GarantieOfficielle(
      'Frais médicaux et d’hospitalisation hors du pays de domicile '
      '(y compris pour le cas d’épidémie ou de pandémie) (A)',
      '(A) 10 000 000 F CFA (15 000 €)',
    ),
    GarantieOfficielle(
      'Frais médicaux dentaires d’urgence (B)',
      '(B) 100 000 F CFA (150 €)',
    ),
  ]),
  GarantieCategorieOfficielle(
    'ASSISTANCES AUX PERSONNES EN CAS DE MALADIE OU BLESSURE',
    [
      GarantieOfficielle(
        'Rapatriement médical (y compris pour les cas d’épidémie '
        'ou de pandémie) (C)',
        '(C) Frais réels',
      ),
    ],
  ),
  GarantieCategorieOfficielle('ASSISTANCE EN CAS DE DÉCÈS', [
    GarantieOfficielle('Transport de corps (D)', '(D) Frais réels'),
    GarantieOfficielle(
      'Frais de cercueil ou d’urne (E)',
      '(E) 1 000 000 F CFA (1 500 €)',
    ),
    GarantieOfficielle(
      'Présence hospitalière d’un proche (F)',
      '(F) Billet d’avion AR (Eco) ou billet de train',
    ),
    GarantieOfficielle(
      'Frais de séjour du membre de la famille accompagnateur (G)',
      '(G) 100 000 F CFA (150 €) par jour (max. 3 nuits)',
    ),
  ]),
  GarantieCategorieOfficielle(
    'ASSISTANCE VOYAGE',
    [
      GarantieOfficielle('Téléconsultation (H)', '(H) 1 appel'),
      GarantieOfficielle(
        'Informations pratiques avant le voyage (I)',
        '(I) Informations',
      ),
    ],
    sousTitre: 'Avant le voyage',
  ),
];

/// Paragraphes d'introduction de la section exclusions.
const List<String> kIntroExclusionsOfficielles = [
  'La couverture d’assistance est destinée à la prise en charge des urgences '
      'médicales couvertes, survenant pendant la période de la couverture et '
      'dans les territoires couverts.',
  'Les exclusions ci-dessous s’appliquent sous réserve des Conditions '
      'Générales ainsi que des Conditions particulières.',
];

/// Encadré « IMPORTANT » précédant les exclusions.
const String kImportantExclusionsOfficielles =
    'Une exclusion peut être totale, partielle ou temporaire selon le contrat '
    'applicable. En cas de doute sur la couverture d’une situation médicale '
    'particulière, le Bénéficiaire doit se référer à ses Conditions '
    'Particulières et contacter MHC avant tout engagement de soins lorsque '
    'cela est possible.';

/// « Limites liées à la prise en charge par Mobility Health Care ».
const List<String> kLimitesPriseEnChargeOfficielles = [
  'Mobility Health Care intervient comme plateforme d’assistance, de '
      'coordination et d’orientation médicale. La prise en charge financière '
      'des prestations demeure soumise au contrat d’assurance souscrit par le '
      'Bénéficiaire auprès de son Assureur, ainsi qu’aux plafonds, conditions, '
      'exclusions, délais et territoires prévus aux Conditions Générales et '
      'aux Conditions Particulières.',
  'Lorsque l’urgence médicale le permet, le Bénéficiaire doit déclencher '
      'l’alerte SOS via la plateforme My MHC ou contacter MHC avant tout '
      'engagement de soins, afin de permettre l’analyse de la situation, la '
      'validation de la prise en charge et l’orientation vers un établissement '
      'adapté du Réseau des Partenaires-Santé. Les soins engagés sans alerte '
      'ni accord préalable, alors que cette démarche était raisonnablement '
      'possible, peuvent être refusés ou limités.',
  'La prise en charge directe est organisée prioritairement auprès des '
      'établissements agréés et médicalement adaptés du Réseau des '
      'Partenaires-Santé. Le choix unilatéral par le Bénéficiaire d’un '
      'établissement hors réseau, d’une ville ou d’un pays déterminé ne peut '
      'être opposé à MHC ou à l’Assureur lorsque MHC propose une solution '
      'médicale appropriée au regard de l’état du patient, de l’urgence, des '
      'capacités locales et des disponibilités du réseau.',
  'Le rapatriement médical ou funéraire n’est pas automatique. Il est '
      'organisé uniquement lorsqu’il est médicalement justifié, techniquement '
      'réalisable et préalablement validé par MHC et/ou l’Assureur, sur la '
      'base des avis médicaux recueillis et des conditions applicables au '
      'contrat.',
  'La téléconsultation, lorsqu’elle est disponible, constitue un service '
      'd’orientation et d’aide à la décision médicale. Elle ne se substitue '
      'pas à une consultation physique, à un examen clinique ou à une prise '
      'en charge d’urgence lorsque l’état du Bénéficiaire l’exige.',
];

/// Les 19 exclusions officielles (titres + paragraphes intégraux).
const List<ExclusionOfficielle> kExclusionsOfficielles = [
  ExclusionOfficielle(
    1,
    'Maladies, conditions médicales préexistantes, malformations et maladies '
        'congénitales',
    'Toute pathologie diagnostiquée, traitée, signalée ou connue avant la '
        'souscription peut faire l’objet d’une exclusion totale, partielle ou '
        'temporaire, selon les conditions définies par l’Assureur. Cela peut '
        'notamment concerner les maladies chroniques, cancers, handicaps, '
        'séquelles d’accident, malformations congénitales, maladies '
        'héréditaires ou toute affection connue du Bénéficiaire ou de son '
        'représentant légal avant la souscription, sauf complication aiguë '
        'mettant en jeu le pronostic vital ou fonctionnel survenant pendant '
        'la période de couverture.',
  ),
  ExclusionOfficielle(
    2,
    'Âge du bénéficiaire',
    'Toute personne ayant atteint l’âge de 90 ans ou plus à la date de '
        'souscription est exclue du bénéfice de la couverture d’assurance. '
        'Lorsque le bénéficiaire atteint l’âge de 90 ans au cours d’une '
        'période de couverture déjà en vigueur, la garantie demeure '
        'applicable jusqu’au terme prévu au contrat, sauf stipulation '
        'contraire des Conditions Particulières.',
  ),
  ExclusionOfficielle(
    3,
    'Grossesse et maternité',
    'Les femmes enceintes de plus de cinq (05) mois révolus à la date de '
        'souscription ne sont pas éligibles à la couverte d’assurance voyage. '
        'Les frais liés à la grossesse, à la maternité et à l’accouchement ne '
        'sont pas pris en charge, sauf disposition contraire prévue au '
        'contrat. Les interruptions volontaires de grossesse (IVG), les '
        'fécondations in vitro (FIV) et les actes liés à la procréation '
        'médicalement assistée sont exclus des garanties.',
  ),
  ExclusionOfficielle(
    4,
    'Chirurgie esthétique et traitements non essentiels',
    'Sont exclus les actes qui ne sont pas médicalement indispensables au '
        'traitement d’une urgence couverte, notamment la chirurgie esthétique '
        'non reconstructive, certains soins dentaires à visée exclusivement '
        'esthétique, les produits de pharmacie et compléments alimentaires, '
        'ainsi que les soins de confort ou de convenance. Sont également '
        'exclus les traitements de fertilité et tout acte dont le caractère '
        'non nécessaire est établi selon les conditions du contrat.',
  ),
  ExclusionOfficielle(
    5,
    'Comportements à risque',
    'Ne sont pas pris en charge, dans les limites autorisées par la '
        'réglementation et le contrat, les frais résultant d’un abus '
        'd’alcool, de la consommation de drogues ou de stupéfiants non '
        'prescrits médicalement, d’une tentative de suicide ou de la '
        'participation volontaire à des rixes, duels, émeutes ou actes '
        'violents.',
  ),
  ExclusionOfficielle(
    6,
    'Guerres, troubles civils et évènements exceptionnels',
    'Sont exclus, sauf stipulation contraire des Conditions Particulières, '
        'les conséquences médicales résultant de guerres civiles ou '
        'étrangères, actes de terrorisme, émeutes, mouvements populaires, '
        'coups d’État, prises d’otage, grèves ou catastrophes naturelles, '
        'lorsque ces évènements constituent la cause directe de l’urgence '
        'médicale.',
  ),
  ExclusionOfficielle(
    7,
    'Soins réalisés hors de la zone de couverture',
    'Les soins et prises en charge réalisés en dehors des territoires '
        'couverts par le contrat ne sont pas pris en charge. Pour l’assureur, '
        'la couverture territoriale est définie dans les Conditions '
        'Particulières et peut notamment comprendre les pays d’Afrique '
        'couverts par le contrat ainsi que les destinations hors Afrique '
        'expressément retenues. Les déplacements entrepris volontairement '
        'dans un pays non couvert ou les soins engagés hors de la zone de '
        'garantie sont exclus.',
  ),
  ExclusionOfficielle(
    8,
    'Non-respect des procédures de prise en charge',
    'La prise en charge peut être refusée ou limitée lorsque les procédures '
        'prévues au contrat et par MHC ne sont pas respectées, notamment en '
        'cas d’absence d’alerte SOS via My MHC ou de contact préalable avec '
        'MHC alors que cette démarche était raisonnablement possible, '
        'd’absence de validation préalable, d’utilisation d’un établissement '
        'hors du Réseau des Partenaires-Santé sans accord de MHC ou de '
        'l’Assureur, ou d’engagement de soins avant la date d’effet de la '
        'couverture. Les dépenses non justifiées médicalement, insuffisamment '
        'documentées ou manifestement disproportionnées par rapport aux '
        'soins nécessaires peuvent également être exclues ou limitées.',
  ),
  ExclusionOfficielle(
    9,
    'Sports et activités à risque',
    'Sont exclus, sauf stipulation contraire des Conditions Particulières, '
        'les frais résultants de la pratique professionnelle d’un sport ou '
        'de sports et activités à risque tels que la plongée sous-marine '
        'avec équipement autonome, l’alpinisme, l’escalade, les sports '
        'aériens, les sports mécaniques ou les sports de glisse hors-piste, '
        'ainsi que toute activité exercée sans encadrement qualifié ou en '
        'violation des consignes de sécurité. La pratique de ces activités '
        'dans un cadre de loisir encadré demeure couverte, sous réserve des '
        'Conditions Particulières applicables. La couverture peut néanmoins '
        'être engagée pour des urgences survenue hors de ces activités '
        'professionnelles.',
  ),
  ExclusionOfficielle(
    10,
    'Frais de recherche et de secours',
    'Les frais engagés pour la recherche, la localisation ou le sauvetage '
        'd’un Bénéficiaire en milieu isolé, maritime, montagneux ou '
        'difficile d’accès ne sont pas pris en charge, sauf disposition '
        'contraire prévue au contrat. Seuls les frais médicaux et de '
        'transport consécutifs à une urgence médicale avérée, une fois le '
        'Bénéficiaire localisé et pris en charge, relèvent de la garantie.',
  ),
  ExclusionOfficielle(
    11,
    'Médecines non conventionnelles',
    'Ne sont pas pris en charge les actes, consultations ou traitements '
        'relevant des médecines douces ou non conventionnelles, notamment '
        'l’acupuncture, l’homéopathie, l’ostéopathie, la chiropraxie ou les '
        'cures thermales, sauf lorsqu’ils sont prescrits par un médecin dans '
        'le cadre strict du traitement d’une urgence couverte et acceptés '
        'par MHC.',
  ),
  ExclusionOfficielle(
    12,
    'Prothèses, optique et soins dentaires de convenance',
    'Sont exclus l’acquisition, le remplacement ou la réparation de '
        'lunettes, lentilles, appareils auditifs, prothèses dentaires ou '
        'orthopédiques et tout appareillage de convenance, ainsi que les '
        'soins dentaires ou optiques ne revêtant pas un caractère d’urgence. '
        'Seuls les soins dentaires d’urgence prévus au tableau de garanties '
        'demeurent couverts, dans la limite du plafond applicable.',
  ),
  ExclusionOfficielle(
    13,
    'Troubles psychiatriques et affections nerveuses',
    'La prise en charge des troubles psychiatriques, psychologiques ou '
        'nerveux, y compris les états dépressifs, les troubles anxieux et '
        'les décompensations de pathologies préexistantes, est exclue, sauf '
        'en cas d’urgence vitale immédiate dûment constatée et sous réserve '
        'des limites spécifiques prévues aux Conditions Particulières.',
  ),
  ExclusionOfficielle(
    14,
    'Voyage entrepris à des fins médicales',
    'Sont exclus les frais afférents à un voyage dont l’objet, principal ou '
        'accessoire, est la recherche, la poursuite ou l’obtention d’un '
        'diagnostic, d’un traitement, d’une intervention chirurgicale ou de '
        'tout autre acte médical dans le pays de destination, y compris '
        'lorsque ce déplacement est motivé par un accès facilité ou un coût '
        'réduit des soins.',
  ),
  ExclusionOfficielle(
    15,
    'Zones sous sanctions internationales',
    'Aucune garantie ni prestation d’assistance n’est due par MHC ou '
        'l’Assureur lorsque leur exécution exposerait MHC, l’Assureur ou '
        'l’un des membres du Réseau des Partenaires-Santé à une sanction, '
        'une interdiction ou une restriction prévue par une résolution des '
        'Nations Unies ou toute organisation compétente.',
  ),
  ExclusionOfficielle(
    16,
    'Déplacement vers une destination déconseillée',
    'Sont exclus les frais liés à un déplacement entrepris ou poursuivi '
        'vers un pays ou une zone faisant l’objet, à la date du départ, '
        'd’un avis officiel déconseillant tout déplacement émis par les '
        'autorités compétentes du pays de résidence du Bénéficiaire, sauf '
        'accord préalable exprès de MHC.',
  ),
  ExclusionOfficielle(
    17,
    'Fausse déclaration',
    'Toute fausse déclaration, omission ou inexactitude intentionnelle '
        'relative à l’état de santé du Bénéficiaire, aux circonstances du '
        'sinistre ou à tout élément déterminant de l’appréciation du risque '
        'entraîne la déchéance de garantie et le refus de prise en charge, '
        'sans préjudice des poursuites que MHC ou l’Assureur pourraient '
        'engager.',
  ),
  ExclusionOfficielle(
    18,
    'Accidents liés à une activité professionnelle exercée sur place',
    'Ne sont pas couverts les accidents ou pathologies survenant dans le '
        'cadre de l’exercice d’une activité professionnelle ou salariée '
        'dans le pays de destination, notamment les métiers manuels, '
        'physiques ou dangereux, sauf lorsque le voyage relève d’une '
        'mission professionnelle ponctuelle expressément couverte par les '
        'Conditions Particulières. La couverture peut néanmoins être '
        'engagée pour des urgences survenue hors de ces activités '
        'professionnelles.',
  ),
  ExclusionOfficielle(
    19,
    'Soins de contrôle et actes de prévention',
    'Sont exclus les bilans de santé, examens de contrôle, dépistages, '
        'vaccinations et actes de médecine préventive ne répondant pas au '
        'traitement d’une urgence médicale survenue pendant la période de '
        'couverture.',
  ),
];

// Compatibilité : anciens noms utilisés ailleurs dans le code.
List<GarantieOfficielle> get kGarantiesOfficielles => [
      for (final c in kCategoriesGarantiesOfficielles) ...c.lignes,
    ];

const List<String> kNotesGarantiesOfficielles = kLimitesPriseEnChargeOfficielles;
