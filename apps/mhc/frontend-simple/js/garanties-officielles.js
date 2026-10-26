// Tableau officiel des garanties et exclusions Mobility Health Care.
// Source : « TABLEAU DE GARANTIES & EXCLUSIONS.docx » (revue app 17/10/2026).
// Chargé avant subscription-wizard.js / product-detail.js.

// Garanties groupées par catégorie (en-têtes du tableau officiel).
window.MHC_GARANTIES_CATEGORIES = [
    {
        titre: 'FRAIS MÉDICAUX',
        lignes: [
            {
                prestation: 'Frais médicaux et d\u2019hospitalisation hors du pays de domicile (y compris pour le cas d\u2019\u00e9pid\u00e9mie ou de pand\u00e9mie) (A)',
                plafond: '(A) 10 000 000 F CFA (15 000 \u20ac)',
            },
            {
                prestation: 'Frais médicaux dentaires d\u2019urgence (B)',
                plafond: '(B) 100 000 F CFA (150 \u20ac)',
            },
        ],
    },
    {
        titre: 'ASSISTANCES AUX PERSONNES EN CAS DE MALADIE OU BLESSURE',
        lignes: [
            {
                prestation: 'Rapatriement médical (y compris pour les cas d\u2019\u00e9pid\u00e9mie ou de pand\u00e9mie) (C)',
                plafond: '(C) Frais réels',
            },
        ],
    },
    {
        titre: 'ASSISTANCE EN CAS DE DÉCÈS',
        lignes: [
            { prestation: 'Transport de corps (D)', plafond: '(D) Frais réels' },
            { prestation: 'Frais de cercueil ou d\u2019urne (E)', plafond: '(E) 1 000 000 F CFA (1 500 \u20ac)' },
            {
                prestation: 'Présence hospitalière d\u2019un proche (F)',
                plafond: '(F) Billet d\u2019avion AR (Eco) ou billet de train',
            },
            {
                prestation: 'Frais de séjour du membre de la famille accompagnateur (G)',
                plafond: '(G) 100 000 F CFA (150 \u20ac) par jour (max. 3 nuits)',
            },
        ],
    },
    {
        titre: 'ASSISTANCE VOYAGE',
        sousTitre: 'Avant le voyage',
        lignes: [
            { prestation: 'Téléconsultation (H)', plafond: '(H) 1 appel' },
            { prestation: 'Informations pratiques avant le voyage (I)', plafond: '(I) Informations' },
        ],
    },
];

// Paragraphes d'introduction de la section exclusions.
window.MHC_EXCLUSIONS_INTRO = [
    'La couverture d\u2019assistance est destinée à la prise en charge des urgences médicales couvertes, survenant pendant la période de la couverture et dans les territoires couverts.',
    'Les exclusions ci-dessous s\u2019appliquent sous réserve des Conditions Générales ainsi que des Conditions particulières.',
];

window.MHC_EXCLUSIONS_IMPORTANT =
    'Une exclusion peut être totale, partielle ou temporaire selon le contrat applicable. En cas de doute sur la couverture d\u2019une situation médicale particulière, le Bénéficiaire doit se référer à ses Conditions Particulières et contacter MHC avant tout engagement de soins lorsque cela est possible.';

// « Limites liées à la prise en charge par Mobility Health Care ».
window.MHC_LIMITES_PRISE_EN_CHARGE = [
    'Mobility Health Care intervient comme plateforme d\u2019assistance, de coordination et d\u2019orientation médicale. La prise en charge financière des prestations demeure soumise au contrat d\u2019assurance souscrit par le Bénéficiaire auprès de son Assureur, ainsi qu\u2019aux plafonds, conditions, exclusions, délais et territoires prévus aux Conditions Générales et aux Conditions Particulières.',
    'Lorsque l\u2019urgence médicale le permet, le Bénéficiaire doit déclencher l\u2019alerte SOS via la plateforme My MHC ou contacter MHC avant tout engagement de soins, afin de permettre l\u2019analyse de la situation, la validation de la prise en charge et l\u2019orientation vers un établissement adapté du Réseau des Partenaires-Santé. Les soins engagés sans alerte ni accord préalable, alors que cette démarche était raisonnablement possible, peuvent être refusés ou limités.',
    'La prise en charge directe est organisée prioritairement auprès des établissements agréés et médicalement adaptés du Réseau des Partenaires-Santé. Le choix unilatéral par le Bénéficiaire d\u2019un établissement hors réseau, d\u2019une ville ou d\u2019un pays déterminé ne peut être opposé à MHC ou à l\u2019Assureur lorsque MHC propose une solution médicale appropriée au regard de l\u2019état du patient, de l\u2019urgence, des capacités locales et des disponibilités du réseau.',
    'Le rapatriement médical ou funéraire n\u2019est pas automatique. Il est organisé uniquement lorsqu\u2019il est médicalement justifié, techniquement réalisable et préalablement validé par MHC et/ou l\u2019Assureur, sur la base des avis médicaux recueillis et des conditions applicables au contrat.',
    'La téléconsultation, lorsqu\u2019elle est disponible, constitue un service d\u2019orientation et d\u2019aide à la décision médicale. Elle ne se substitue pas à une consultation physique, à un examen clinique ou à une prise en charge d\u2019urgence lorsque l\u2019état du Bénéficiaire l\u2019exige.',
];

// Les 19 exclusions officielles (titre + paragraphe intégral).
window.MHC_EXCLUSIONS_OFFICIELLES = [
    {
        titre: 'Maladies, conditions médicales préexistantes, malformations et maladies congénitales',
        texte: 'Toute pathologie diagnostiquée, traitée, signalée ou connue avant la souscription peut faire l\u2019objet d\u2019une exclusion totale, partielle ou temporaire, selon les conditions définies par l\u2019Assureur. Cela peut notamment concerner les maladies chroniques, cancers, handicaps, séquelles d\u2019accident, malformations congénitales, maladies héréditaires ou toute affection connue du Bénéficiaire ou de son représentant légal avant la souscription, sauf complication aiguë mettant en jeu le pronostic vital ou fonctionnel survenant pendant la période de couverture.',
    },
    {
        titre: 'Âge du bénéficiaire',
        texte: 'Toute personne ayant atteint l\u2019âge de 90 ans ou plus à la date de souscription est exclue du bénéfice de la couverture d\u2019assurance. Lorsque le bénéficiaire atteint l\u2019âge de 90 ans au cours d\u2019une période de couverture déjà en vigueur, la garantie demeure applicable jusqu\u2019au terme prévu au contrat, sauf stipulation contraire des Conditions Particulières.',
    },
    {
        titre: 'Grossesse et maternité',
        texte: 'Les femmes enceintes de plus de cinq (05) mois révolus à la date de souscription ne sont pas éligibles à la couverte d\u2019assurance voyage. Les frais liés à la grossesse, à la maternité et à l\u2019accouchement ne sont pas pris en charge, sauf disposition contraire prévue au contrat. Les interruptions volontaires de grossesse (IVG), les fécondations in vitro (FIV) et les actes liés à la procréation médicalement assistée sont exclus des garanties.',
    },
    {
        titre: 'Chirurgie esthétique et traitements non essentiels',
        texte: 'Sont exclus les actes qui ne sont pas médicalement indispensables au traitement d\u2019une urgence couverte, notamment la chirurgie esthétique non reconstructive, certains soins dentaires à visée exclusivement esthétique, les produits de pharmacie et compléments alimentaires, ainsi que les soins de confort ou de convenance. Sont également exclus les traitements de fertilité et tout acte dont le caractère non nécessaire est établi selon les conditions du contrat.',
    },
    {
        titre: 'Comportements à risque',
        texte: 'Ne sont pas pris en charge, dans les limites autorisées par la réglementation et le contrat, les frais résultant d\u2019un abus d\u2019alcool, de la consommation de drogues ou de stupéfiants non prescrits médicalement, d\u2019une tentative de suicide ou de la participation volontaire à des rixes, duels, émeutes ou actes violents.',
    },
    {
        titre: 'Guerres, troubles civils et évènements exceptionnels',
        texte: 'Sont exclus, sauf stipulation contraire des Conditions Particulières, les conséquences médicales résultant de guerres civiles ou étrangères, actes de terrorisme, émeutes, mouvements populaires, coups d\u2019État, prises d\u2019otage, grèves ou catastrophes naturelles, lorsque ces évènements constituent la cause directe de l\u2019urgence médicale.',
    },
    {
        titre: 'Soins réalisés hors de la zone de couverture',
        texte: 'Les soins et prises en charge réalisés en dehors des territoires couverts par le contrat ne sont pas pris en charge. Pour l\u2019assureur, la couverture territoriale est définie dans les Conditions Particulières et peut notamment comprendre les pays d\u2019Afrique couverts par le contrat ainsi que les destinations hors Afrique expressément retenues. Les déplacements entrepris volontairement dans un pays non couvert ou les soins engagés hors de la zone de garantie sont exclus.',
    },
    {
        titre: 'Non-respect des procédures de prise en charge',
        texte: 'La prise en charge peut être refusée ou limitée lorsque les procédures prévues au contrat et par MHC ne sont pas respectées, notamment en cas d\u2019absence d\u2019alerte SOS via My MHC ou de contact préalable avec MHC alors que cette démarche était raisonnablement possible, d\u2019absence de validation préalable, d\u2019utilisation d\u2019un établissement hors du Réseau des Partenaires-Santé sans accord de MHC ou de l\u2019Assureur, ou d\u2019engagement de soins avant la date d\u2019effet de la couverture. Les dépenses non justifiées médicalement, insuffisamment documentées ou manifestement disproportionnées par rapport aux soins nécessaires peuvent également être exclues ou limitées.',
    },
    {
        titre: 'Sports et activités à risque',
        texte: 'Sont exclus, sauf stipulation contraire des Conditions Particulières, les frais résultants de la pratique professionnelle d\u2019un sport ou de sports et activités à risque tels que la plongée sous-marine avec équipement autonome, l\u2019alpinisme, l\u2019escalade, les sports aériens, les sports mécaniques ou les sports de glisse hors-piste, ainsi que toute activité exercée sans encadrement qualifié ou en violation des consignes de sécurité. La pratique de ces activités dans un cadre de loisir encadré demeure couverte, sous réserve des Conditions Particulières applicables. La couverture peut néanmoins être engagée pour des urgences survenue hors de ces activités professionnelles.',
    },
    {
        titre: 'Frais de recherche et de secours',
        texte: 'Les frais engagés pour la recherche, la localisation ou le sauvetage d\u2019un Bénéficiaire en milieu isolé, maritime, montagneux ou difficile d\u2019accès ne sont pas pris en charge, sauf disposition contraire prévue au contrat. Seuls les frais médicaux et de transport consécutifs à une urgence médicale avérée, une fois le Bénéficiaire localisé et pris en charge, relèvent de la garantie.',
    },
    {
        titre: 'Médecines non conventionnelles',
        texte: 'Ne sont pas pris en charge les actes, consultations ou traitements relevant des médecines douces ou non conventionnelles, notamment l\u2019acupuncture, l\u2019homéopathie, l\u2019ostéopathie, la chiropraxie ou les cures thermales, sauf lorsqu\u2019ils sont prescrits par un médecin dans le cadre strict du traitement d\u2019une urgence couverte et acceptés par MHC.',
    },
    {
        titre: 'Prothèses, optique et soins dentaires de convenance',
        texte: 'Sont exclus l\u2019acquisition, le remplacement ou la réparation de lunettes, lentilles, appareils auditifs, prothèses dentaires ou orthopédiques et tout appareillage de convenance, ainsi que les soins dentaires ou optiques ne revêtant pas un caractère d\u2019urgence. Seuls les soins dentaires d\u2019urgence prévus au tableau de garanties demeurent couverts, dans la limite du plafond applicable.',
    },
    {
        titre: 'Troubles psychiatriques et affections nerveuses',
        texte: 'La prise en charge des troubles psychiatriques, psychologiques ou nerveux, y compris les états dépressifs, les troubles anxieux et les décompensations de pathologies préexistantes, est exclue, sauf en cas d\u2019urgence vitale immédiate dûment constatée et sous réserve des limites spécifiques prévues aux Conditions Particulières.',
    },
    {
        titre: 'Voyage entrepris à des fins médicales',
        texte: 'Sont exclus les frais afférents à un voyage dont l\u2019objet, principal ou accessoire, est la recherche, la poursuite ou l\u2019obtention d\u2019un diagnostic, d\u2019un traitement, d\u2019une intervention chirurgicale ou de tout autre acte médical dans le pays de destination, y compris lorsque ce déplacement est motivé par un accès facilité ou un coût réduit des soins.',
    },
    {
        titre: 'Zones sous sanctions internationales',
        texte: 'Aucune garantie ni prestation d\u2019assistance n\u2019est due par MHC ou l\u2019Assureur lorsque leur exécution exposerait MHC, l\u2019Assureur ou l\u2019un des membres du Réseau des Partenaires-Santé à une sanction, une interdiction ou une restriction prévue par une résolution des Nations Unies ou toute organisation compétente.',
    },
    {
        titre: 'Déplacement vers une destination déconseillée',
        texte: 'Sont exclus les frais liés à un déplacement entrepris ou poursuivi vers un pays ou une zone faisant l\u2019objet, à la date du départ, d\u2019un avis officiel déconseillant tout déplacement émis par les autorités compétentes du pays de résidence du Bénéficiaire, sauf accord préalable exprès de MHC.',
    },
    {
        titre: 'Fausse déclaration',
        texte: 'Toute fausse déclaration, omission ou inexactitude intentionnelle relative à l\u2019état de santé du Bénéficiaire, aux circonstances du sinistre ou à tout élément déterminant de l\u2019appréciation du risque entraîne la déchéance de garantie et le refus de prise en charge, sans préjudice des poursuites que MHC ou l\u2019Assureur pourraient engager.',
    },
    {
        titre: 'Accidents liés à une activité professionnelle exercée sur place',
        texte: 'Ne sont pas couverts les accidents ou pathologies survenant dans le cadre de l\u2019exercice d\u2019une activité professionnelle ou salariée dans le pays de destination, notamment les métiers manuels, physiques ou dangereux, sauf lorsque le voyage relève d\u2019une mission professionnelle ponctuelle expressément couverte par les Conditions Particulières. La couverture peut néanmoins être engagée pour des urgences survenue hors de ces activités professionnelles.',
    },
    {
        titre: 'Soins de contrôle et actes de prévention',
        texte: 'Sont exclus les bilans de santé, examens de contrôle, dépistages, vaccinations et actes de médecine préventive ne répondant pas au traitement d\u2019une urgence médicale survenue pendant la période de couverture.',
    },
];

// Compatibilité : liste aplatie des garanties.
window.MHC_GARANTIES_OFFICIELLES = (window.MHC_GARANTIES_CATEGORIES || [])
    .flatMap((c) => c.lignes);
window.MHC_NOTES_GARANTIES = window.MHC_LIMITES_PRISE_EN_CHARGE;

// Rend le tableau officiel « PRESTATIONS / PLAFONDS » groupé par catégorie.
window.mhcRenderOfficialGaranties = function () {
    const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    let html = '<table class="mh-price-table"><thead><tr><th>PRESTATIONS</th><th>PLAFONDS</th></tr></thead><tbody>';
    for (const cat of window.MHC_GARANTIES_CATEGORIES || []) {
        html += `<tr><td colspan="2" style="background:#EDE7F6;color:#4E267C;font-weight:700;font-size:0.8rem;letter-spacing:0.03em;">${esc(cat.titre)}${cat.sousTitre ? ` — <em>${esc(cat.sousTitre)}</em>` : ''}</td></tr>`;
        for (const g of cat.lignes) {
            html += `<tr><td>${esc(g.prestation)}</td><td><strong>${esc(g.plafond)}</strong></td></tr>`;
        }
    }
    return html + '</tbody></table>';
};

// Rend la section exclusions complète : intro + IMPORTANT + limites + 19 items.
window.mhcRenderOfficialExclusions = function () {
    const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const intro = (window.MHC_EXCLUSIONS_INTRO || []).map((p) => `<p>${esc(p)}</p>`).join('');
    const limites = (window.MHC_LIMITES_PRISE_EN_CHARGE || []).map((p) => `<p>${esc(p)}</p>`).join('');
    const items = (window.MHC_EXCLUSIONS_OFFICIELLES || []).map((e, i) =>
        `<div class="mh-exclusion" style="margin-bottom:12px;">
            <strong>Exclusion – ${i + 1}&nbsp;: ${esc(e.titre)}</strong>
            <p style="margin:4px 0 0;">${esc(e.texte)}</p>
        </div>`).join('');
    return `<div class="mh-muted" style="font-size:0.9rem;">
        ${intro}
        <div style="background:#F3EEF9;border-left:3px solid #4E267C;padding:10px;border-radius:6px;margin:10px 0;">
            <strong style="color:#4E267C;">IMPORTANT</strong>
            <p style="margin:4px 0 0;">${esc(window.MHC_EXCLUSIONS_IMPORTANT || '')}</p>
        </div>
        <h4 style="color:#4E267C;margin:14px 0 6px;">Limites liées à la prise en charge par Mobility Health Care</h4>
        ${limites}
        <hr style="margin:14px 0;border:none;border-top:1px solid #E2E8F0;">
        ${items}
    </div>`;
};
