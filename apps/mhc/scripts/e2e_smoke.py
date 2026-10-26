"""
Smoke test E2E du back-office MHC.
Pour chaque profil : login, collecte des liens de la sidebar,
visite de chaque page, capture erreurs JS + pages bloquées « Chargement ».
Usage : python scripts/e2e_smoke.py [email]
"""
import sys
import time
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8899'
PWD = 'mh@123'

PROFILES = {
    'admin@mhc.com': 'admin123',
    'sup.technique@mhc.demo': PWD,
    'agent.production@mhc.demo': PWD,
    'conformite.prod@mhc.demo': PWD,
    'agent.sinistre@mhc.demo': PWD,
    'conformite.sinistre@mhc.demo': PWD,
    'sup.medical@mhc.demo': PWD,
    'agent.medical@mhc.demo': PWD,
    'conformite.medical@mhc.demo': PWD,
    'sup.comptable@mhc.demo': PWD,
    'agent.comptable@mhc.demo': PWD,
    'conformite.compta@mhc.demo': PWD,
    # Partenaires / externes
    'assistant.souscr@mhc.demo': PWD,
    'prod.assureur@mhc.demo': PWD,
    'compta.assureur@mhc.demo': PWD,
    'medical.assureur@mhc.demo': PWD,
    'sinistre.assureur@mhc.demo': PWD,
    'prod.courtier@mhc.demo': PWD,
    'compta.courtier@mhc.demo': PWD,
    'sinistre.courtier@mhc.demo': PWD,
    'verif.reassureur@mhc.demo': PWD,
    'medecin.conseil@mhc.demo': PWD,
    'admin.hopital@mhc.demo': PWD,
    'compta.hopital@mhc.demo': PWD,
    'reception.hopital@mhc.demo': PWD,
    'medecin.hopital@mhc.demo': PWD,
}

STUCK_MARKERS = ['Chargement…', 'Chargement...', 'chargement en cours', 'Chargement en cours', 'Chargement des transactions']


def login(page, email, password):
    page.goto(f'{BASE}/login.html')
    page.wait_for_selector('#username', timeout=15000)
    page.fill('#username', email)
    page.fill('#password', password)
    page.click('#loginBtn')
    page.wait_for_timeout(2500)


def sidebar_links(page):
    links = page.eval_on_selector_all(
        '.bo-sidebar a[href]', 'els => els.map(e => e.getAttribute("href"))')
    out, seen = [], set()
    for h in links:
        if not h or h.startswith('#') or h.startswith('javascript'):
            continue
        h = h.split('#')[0]
        if h in seen or 'login.html' in h:
            continue
        seen.add(h)
        out.append(h)
    return out


def run_profile(pw, email):
    password = PROFILES[email]
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    js_errors, page_errors = [], []
    page.on('console', lambda m: js_errors.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: page_errors.append(str(e)))

    report = {'email': email, 'pages': [], 'js_errors': js_errors, 'page_errors': page_errors}
    try:
        login(page, email, password)
        try:
            page.wait_for_selector('.bo-sidebar a[href]', timeout=12000)
        except Exception:
            pass
        links = sidebar_links(page)
        report['nb_links'] = len(links)
        for href in links:
            url = href if href.startswith('http') else f'{BASE}/{href.lstrip("./")}'
            err0 = len(page_errors)
            try:
                page.goto(url, timeout=15000)
                page.wait_for_timeout(5500)
            except Exception as e:
                report['pages'].append({'url': href, 'status': 'NAV_FAIL', 'detail': str(e)[:120]})
                continue
            # Alertes JS (bloquantes)
            alert = page.evaluate(
                "document.body.innerText.includes('Accès restreint') || document.body.innerText.includes('Rôle non autorisé')")
            stuck = []
            body_text = page.inner_text('body')[:8000]
            for marker in STUCK_MARKERS:
                if marker.lower() in body_text.lower():
                    stuck.append(marker)
            new_errs = page_errors[err0:]
            status = 'OK'
            detail = ''
            if alert:
                status = 'ALERTE_ACCES'
            elif stuck:
                status = 'CHARGEMENT_STUCK'
                detail = ','.join(set(stuck))
            if new_errs:
                status = 'JS_ERROR' if status == 'OK' else status + '+JS_ERROR'
                detail += ' | ' + new_errs[0][:100]
            report['pages'].append({'url': href, 'status': status, 'detail': detail.strip(' |')})
    finally:
        browser.close()
    return report


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    with sync_playwright() as pw:
        for email in PROFILES:
            if only and email != only:
                continue
            try:
                r = run_profile(pw, email)
            except Exception as e:
                print(f'### {email} — LOGIN/RUN FAIL: {e}')
                continue
            print(f'\n### {email} — {r["nb_links"]} liens')
            bad = [p for p in r['pages'] if p['status'] != 'OK']
            if not bad:
                print('   toutes les pages OK')
            for p in r['pages']:
                mark = '' if p['status'] == 'OK' else '  <<< ' + p['status']
                print(f"   {p['status']:22} {p['url']} {p['detail']}{mark}")


if __name__ == '__main__':
    main()
