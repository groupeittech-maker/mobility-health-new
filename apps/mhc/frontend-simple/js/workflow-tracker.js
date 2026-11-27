/**
 * Suivi visuel du workflow sinistre — composant partagé.
 *
 * Les 16 étapes plates étaient illisibles : étapes manuelles figées « en cours »
 * alors que la suite est terminée, branche « fausse alerte » affichée en attente
 * à vie, aucun lien avec les documents générés. Ce composant regroupe les étapes
 * en phases, calcule la position réelle du dossier et attache les documents
 * (BPCU, facture…) aux étapes qui les produisent.
 *
 * Usage : window.MhWorkflowTracker.render(container, { steps, documents, invoice, careDocumentPdfUrl })
 */
(function () {
    'use strict';

    const PHASES = [
        { key: 'alerte', titre: 'Alerte & activation', steps: [1, 2, 3, 4, 5] },
        { key: 'mobilisation', titre: 'Mobilisation terrain', steps: [6, 7] },
        { key: 'validation', titre: 'Validation médicale & prise en charge', steps: [8, 9, 10, 11, 12] },
        { key: 'facturation', titre: 'Facturation & clôture', steps: [13, 14, 15, 16] },
    ];

    const ACTORS = {
        1: 'Assuré', 2: 'Centre des opérations MHC', 3: 'Médecin référent', 4: 'Centre des opérations',
        5: 'Centre des opérations', 6: 'Réception de l’hôpital', 7: 'Médecin référent', 8: 'Automatique',
        9: 'Médecin référent', 10: 'Médecin référent', 11: 'Médecin référent',
        12: 'Médecin hospitalier → médecin-conseil', 13: 'Comptable de l’hôpital',
        14: 'Médecin-conseil', 15: 'Affaires médicales MHC', 16: 'Comptabilité MHC',
    };

    const CONDITIONAL_STEP = 'suspension_si_fausse';

    /** Type de document de prise en charge → étape qui le produit. */
    const DOC_TYPE_TO_STEP = {
        bpcu: 11, brpcu: 11,
        bh: 12, bph: 12, bs: 12, brs: 12, ars: 12, brf: 12, arf: 12,
    };

    const DOC_TYPE_LABELS = {
        bpcu: 'Bon de prise en charge',
        brpcu: 'Refus de prise en charge',
        bh: 'Bon d’hospitalisation',
        bph: 'Prolongation d’hospitalisation',
        bs: 'Bulletin de sortie',
        brs: 'Rapatriement sanitaire',
        ars: 'Retour de rapatriement',
        brf: 'Rapatriement funéraire',
        arf: 'Attestation funéraire',
    };

    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        return String(text)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }

    function formatDateTime(value) {
        if (!value) return '';
        const d = new Date(value);
        if (Number.isNaN(d.getTime())) return '';
        return d.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
    }

    /**
     * Étape « courante » = la plus avancée en cours ; sinon la première en attente
     * après la dernière terminée. Les étapes manuelles figées (ambulance, médecin
     * en route) alors qu'une étape plus tardive est terminée sont marquées
     * « non confirmée » plutôt que de bloquer la lecture.
     */
    function computePosition(steps) {
        const main = steps.filter((s) => s.step_key !== CONDITIONAL_STEP);
        const maxCompleted = Math.max(0, ...main.filter((s) => s.statut === 'completed').map((s) => s.ordre));
        // Les étapes manuelles restées « en cours » alors que des étapes plus tardives
        // sont terminées ne représentent pas la position réelle : on les ignore.
        const inProgress = main.filter((s) => s.statut === 'in_progress' && s.ordre >= maxCompleted);
        let current = null;
        if (inProgress.length) {
            current = inProgress.reduce((a, b) => (a.ordre > b.ordre ? a : b));
        } else {
            current = main.find((s) => s.statut !== 'completed' && s.statut !== 'cancelled') || null;
        }
        const allDone = main.every((s) => s.statut === 'completed' || s.statut === 'cancelled');
        const cancelled = main.some((s) => s.statut === 'cancelled');
        const doneCount = main.filter((s) => s.statut === 'completed').length;
        return { current, allDone, cancelled, doneCount, total: main.length, maxCompleted };
    }

    function stepDisplayState(step, maxCompleted) {
        if (step.statut === 'completed') return { cls: 'done', label: 'Terminé' };
        if (step.statut === 'cancelled') return { cls: 'cancelled', label: 'Annulé' };
        if (step.statut === 'in_progress') {
            // Étape manuelle dépassée par la suite du workflow : pas une vraie position.
            if (step.ordre < maxCompleted) return { cls: 'stale', label: 'Non confirmée' };
            return { cls: 'current', label: 'En cours' };
        }
        return { cls: 'pending', label: 'À venir' };
    }

    function documentsForStep(documents, ordre) {
        return (documents || []).filter((doc) => DOC_TYPE_TO_STEP[(doc.document_type || '').toLowerCase()] === ordre);
    }

    function render(container, options = {}) {
        if (!container) return;
        const steps = [...(options.steps || [])].sort((a, b) => a.ordre - b.ordre);
        if (!steps.length) {
            container.innerHTML = '<p class="muted">Aucune étape disponible.</p>';
            return;
        }
        const documents = options.documents || [];
        const invoice = options.invoice || null;
        const pdfUrl = options.careDocumentPdfUrl || null;
        const pos = computePosition(steps);
        const conditional = steps.find((s) => s.step_key === CONDITIONAL_STEP);

        // ---- En-tête : position réelle du dossier
        let headText;
        let headCls;
        if (pos.cancelled) {
            headText = 'Dossier suspendu ou annulé';
            headCls = 'wft-head--cancelled';
        } else if (pos.allDone) {
            headText = 'Dossier clôturé — facture réglée';
            headCls = 'wft-head--done';
        } else if (pos.current) {
            headText = `Étape ${pos.current.ordre} sur ${pos.total} — ${pos.current.titre}`;
            headCls = 'wft-head--active';
        } else {
            headText = 'En attente de démarrage';
            headCls = '';
        }
        const pct = Math.round((pos.doneCount / pos.total) * 100);

        // ---- Branche fausse alerte : repliée, visible seulement si déclenchée
        let branchHtml = '';
        if (conditional) {
            const triggered = conditional.statut === 'completed' || conditional.statut === 'in_progress';
            if (triggered) {
                branchHtml = `
                <div class="wft-branch wft-branch--triggered">
                    <strong>Branche « fausse alerte » déclenchée</strong>
                    <span>La prise en charge a été suspendue après vérification de l'urgence.</span>
                </div>`;
            }
        }

        // ---- Phases
        const phasesHtml = PHASES.map((phase) => {
            const phaseSteps = steps.filter((s) => phase.steps.includes(s.ordre) && s.step_key !== CONDITIONAL_STEP);
            if (!phaseSteps.length) return '';
            const doneInPhase = phaseSteps.filter((s) => s.statut === 'completed').length;
            const phaseDone = doneInPhase === phaseSteps.length;
            const hasCurrent = pos.current && phaseSteps.some((s) => s.ordre === pos.current.ordre);
            const rows = phaseSteps.map((step) => {
                const state = stepDisplayState(step, pos.maxCompleted);
                const docs = documentsForStep(documents, step.ordre);
                const docsHtml = docs.map((doc) => {
                    const label = DOC_TYPE_LABELS[(doc.document_type || '').toLowerCase()] || doc.document_type;
                    const href = pdfUrl ? pdfUrl(doc) : null;
                    const inner = `${escapeHtml(label)}${doc.numero ? ` · ${escapeHtml(doc.numero)}` : ''}`;
                    return href
                        ? `<a class="wft-doc" href="${escapeHtml(href)}" target="_blank" rel="noopener">${inner}</a>`
                        : `<span class="wft-doc">${inner}</span>`;
                }).join('');
                const invoiceHtml = (step.ordre === 13 && invoice)
                    ? `<span class="wft-doc">Facture · ${escapeHtml(invoice.numero_facture || '')} — ${escapeHtml(invoice.statut || '')}</span>`
                    : '';
                const isCurrent = pos.current && pos.current.ordre === step.ordre && state.cls === 'current';
                return `
                <li class="wft-step wft-step--${state.cls}${isCurrent ? ' is-current' : ''}">
                    <span class="wft-step__marker">${state.cls === 'done' ? '✓' : step.ordre}</span>
                    <div class="wft-step__body">
                        <div class="wft-step__line">
                            <strong>${escapeHtml(step.titre)}</strong>
                            <span class="wft-step__status wft-step__status--${state.cls}">${escapeHtml(state.label)}</span>
                        </div>
                        <div class="wft-step__meta">
                            <span>${escapeHtml(ACTORS[step.ordre] || '')}</span>
                            ${step.completed_at ? `<span>· ${escapeHtml(formatDateTime(step.completed_at))}</span>` : ''}
                        </div>
                        ${docsHtml || invoiceHtml ? `<div class="wft-step__docs">${docsHtml}${invoiceHtml}</div>` : ''}
                    </div>
                </li>`;
            }).join('');
            const collapsed = !hasCurrent;
            return `
            <section class="wft-phase${phaseDone ? ' wft-phase--done' : ''}${hasCurrent ? ' wft-phase--active' : ''}${collapsed ? ' wft-phase--collapsed' : ''}">
                <header class="wft-phase__head" role="button" tabindex="0" aria-expanded="${collapsed ? 'false' : 'true'}">
                    <span class="wft-phase__chevron">▸</span>
                    <span class="wft-phase__titre">${escapeHtml(phase.titre)}</span>
                    <span class="wft-phase__count">${doneInPhase}/${phaseSteps.length}</span>
                </header>
                <ol class="wft-steps">${rows}</ol>
            </section>`;
        }).join('');

        container.innerHTML = `
        <div class="wft">
            <div class="wft-head ${headCls}">
                <div class="wft-head__position">${escapeHtml(headText)}</div>
                <div class="wft-head__progress">
                    <div class="wft-head__bar"><span style="width: ${pct}%"></span></div>
                    <span class="wft-head__count">${pos.doneCount}/${pos.total} étapes</span>
                </div>
            </div>
            ${branchHtml}
            ${phasesHtml}
        </div>`;
    }

    // Repli/dépli des phases au clic (délégation — une seule fois par conteneur).
    function bindCollapse(container) {
        if (!container || container.dataset.wftCollapseBound) return;
        container.dataset.wftCollapseBound = '1';
        const toggle = (event) => {
            const head = event.target.closest && event.target.closest('.wft-phase__head');
            if (!head) return;
            if (event.type === 'keydown' && event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            const phase = head.parentElement;
            const collapsed = phase.classList.toggle('wft-phase--collapsed');
            head.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        };
        container.addEventListener('click', toggle);
        container.addEventListener('keydown', toggle);
    }

    window.MhWorkflowTracker = { render, computePosition, bindCollapse };
})();
