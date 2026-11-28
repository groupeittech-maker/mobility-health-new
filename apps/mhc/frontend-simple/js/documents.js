/**
 * Traçabilité des documents de prise en charge émis — tous assurés.
 * La liste est chargée une fois puis filtrée côté client ; le PDF est ouvert
 * via fetch + token (l'endpoint exige une authentification Bearer).
 */
(function () {
    'use strict';

    const TYPE_ORDER = ['bpcu', 'brpcu', 'bh', 'bph', 'bs', 'brs', 'ars', 'brf', 'arf'];
    const TYPE_LABELS = {
        bpcu: 'Bon de prise en charge (111)',
        brpcu: 'Refus de prise en charge (112)',
        bh: "Bon d'hospitalisation (113)",
        bph: "Prolongation d'hospitalisation",
        bs: 'Bulletin de sortie (114)',
        brs: 'Rapatriement sanitaire',
        ars: 'Retour de rapatriement (121)',
        brf: 'Rapatriement funéraire',
        arf: 'Attestation funéraire (122)',
    };
    const VALIDATION_LABELS = {
        valide: { text: 'Validé', cls: 'b-val-ok' },
        en_attente: { text: 'En attente', cls: 'b-val-attente' },
        non_requise: { text: '—', cls: 'b-val-na' },
    };
    const STATUT_LABELS = {
        emi: { text: 'Émis', cls: 'b-emi' },
        cloture: { text: 'Clôturé', cls: 'b-cloture' },
        expire: { text: 'Expiré', cls: 'b-expire' },
    };

    let allDocs = [];

    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        return String(text)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }

    function formatDateTime(value) {
        if (!value) return '—';
        const d = new Date(value);
        if (Number.isNaN(d.getTime())) return '—';
        return d.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
    }

    function toast(message, isError) {
        const el = document.getElementById('toast');
        if (!el) return;
        el.textContent = message;
        el.className = 'toast show' + (isError ? ' error' : '');
        setTimeout(() => { el.className = 'toast'; }, 3200);
    }

    async function loadDocuments() {
        const tbody = document.getElementById('docsBody');
        try {
            const data = await apiCall('/mhc/care-documents?limit=500');
            allDocs = Array.isArray(data) ? data : [];
            populateTypeFilter();
            renderDocuments();
        } catch (error) {
            console.error('Erreur chargement documents:', error);
            tbody.innerHTML = '<tr class="empty-row"><td colspan="8">Impossible de charger les documents.</td></tr>';
            toast(error.message || 'Chargement impossible', true);
        }
    }

    function populateTypeFilter() {
        const select = document.getElementById('docTypeFilter');
        if (!select || select.options.length > 1) return;
        const present = new Set(allDocs.map((d) => d.document_type));
        TYPE_ORDER.filter((t) => present.has(t)).forEach((t) => {
            const opt = document.createElement('option');
            opt.value = t;
            opt.textContent = TYPE_LABELS[t] || t;
            select.appendChild(opt);
        });
    }

    function currentFilters() {
        return {
            q: (document.getElementById('docSearch')?.value || '').trim().toLowerCase(),
            type: document.getElementById('docTypeFilter')?.value || '',
            statut: document.getElementById('docStatutFilter')?.value || '',
        };
    }

    function renderDocuments() {
        const tbody = document.getElementById('docsBody');
        const counter = document.getElementById('docCount');
        const f = currentFilters();
        const filtered = allDocs.filter((doc) => {
            if (f.type && doc.document_type !== f.type) return false;
            if (f.statut && doc.statut !== f.statut) return false;
            if (f.q) {
                const hay = [doc.assure_nom, doc.numero, doc.numero_sinistre, doc.titre]
                    .filter(Boolean).join(' ').toLowerCase();
                if (!hay.includes(f.q)) return false;
            }
            return true;
        });

        if (counter) {
            counter.textContent = `${filtered.length} document${filtered.length > 1 ? 's' : ''}`;
        }
        if (!filtered.length) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="8">Aucun document ne correspond aux critères.</td></tr>';
            return;
        }

        tbody.innerHTML = filtered.map((doc) => {
            const statut = STATUT_LABELS[doc.statut] || { text: doc.statut, cls: 'b-emi' };
            const validation = VALIDATION_LABELS[doc.validation_status] || VALIDATION_LABELS.non_requise;
            const typeLabel = TYPE_LABELS[doc.document_type] || doc.titre || doc.document_type;
            const sinistre = doc.numero_sinistre || (doc.sinistre_id ? `#${doc.sinistre_id}` : '—');
            const dossierLink = doc.alerte_id
                ? `<a href="hospital-alert-details.html?alert_id=${doc.alerte_id}" class="muted">${escapeHtml(sinistre)}</a>`
                : escapeHtml(sinistre);
            return `
                <tr>
                    <td style="white-space:nowrap">${formatDateTime(doc.issued_at)}</td>
                    <td class="assure-cell">
                        <strong>${escapeHtml(doc.assure_nom || '—')}</strong>
                        ${doc.hospital_nom ? `<span class="muted">${escapeHtml(doc.hospital_nom)}</span>` : ''}
                    </td>
                    <td>${dossierLink}</td>
                    <td>${escapeHtml(typeLabel)}</td>
                    <td style="white-space:nowrap">${escapeHtml(doc.numero)}</td>
                    <td><span class="badge ${statut.cls}">${escapeHtml(statut.text)}</span></td>
                    <td><span class="badge ${validation.cls}">${escapeHtml(validation.text)}</span></td>
                    <td><button type="button" class="btn-pdf" data-doc-id="${doc.id}">Consulter</button></td>
                </tr>
            `;
        }).join('');

        tbody.querySelectorAll('.btn-pdf').forEach((btn) => {
            btn.addEventListener('click', () => openPdf(Number(btn.getAttribute('data-doc-id'))));
        });
    }

    async function openPdf(docId) {
        if (!Number.isFinite(docId)) return;
        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            const base = (typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : '/api/v1');
            const res = await fetch(`${base}/mhc/care-documents/${docId}/pdf`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) {
                toast('PDF indisponible (HTTP ' + res.status + ')', true);
                return;
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank', 'noopener');
            setTimeout(() => URL.revokeObjectURL(url), 60000);
        } catch (error) {
            console.error('Erreur ouverture PDF:', error);
            toast('Impossible d’ouvrir le document', true);
        }
    }

    document.addEventListener('DOMContentLoaded', async () => {
        const authed = await requireAuth();
        if (!authed) return;
        // Profils hospitaliers (hors matrice interne) : accès restreint côté API
        // à leurs établissements. Profils internes : consultation des sinistres.
        const role = localStorage.getItem('user_role') || '';
        const hospitalRoles = ['medecin_hopital', 'hospital_admin', 'agent_reception_hopital', 'doctor'];
        const internalOk = window.MhPermissions && window.MhPermissions.can('sinistres', 'consultation');
        if (!hospitalRoles.includes(role) && !internalOk) {
            alert('Accès refusé.');
            window.location.href = 'bo-dashboard.html';
            return;
        }

        let searchTimer = null;
        document.getElementById('docSearch')?.addEventListener('input', () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(renderDocuments, 250);
        });
        document.getElementById('docTypeFilter')?.addEventListener('change', renderDocuments);
        document.getElementById('docStatutFilter')?.addEventListener('change', renderDocuments);
        document.getElementById('docRefreshBtn')?.addEventListener('click', loadDocuments);

        await loadDocuments();
    });
})();
