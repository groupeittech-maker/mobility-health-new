#!/usr/bin/env python3
"""
Serveur HTTP simple pour le développement frontend avec désactivation du cache.
Usage: python server.py [port]
"""

import http.server
import socketserver
import sys
from pathlib import Path

class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP qui désactive le cache pour tous les fichiers statiques."""
    
    def end_headers(self):
        # Ajouter des en-têtes pour désactiver le cache
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        # Permettre CORS pour le développement
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Gérer les requêtes OPTIONS pour CORS."""
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        """Personnaliser les messages de log."""
        print(f"[{self.log_date_time_string()}] {format % args}")

def main():
    # Port par défaut : 3000
    port = 3000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Erreur: Le port doit être un nombre. Utilisation du port par défaut {port}")
    
    # Vérifier que nous sommes dans le bon répertoire
    if not Path('index.html').exists():
        print("Erreur: index.html non trouvé. Assurez-vous d'exécuter ce script depuis le répertoire frontend-simple.")
        sys.exit(1)
    
    Handler = NoCacheHTTPRequestHandler
    
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print("=" * 60)
        print("Serveur HTTP Frontend - Mobility Health")
        print("=" * 60)
        print(f"Serveur démarré sur http://localhost:{port}")
        print(f"Répertoire: {Path.cwd()}")
        print("")
        print("Pages disponibles:")
        print(f"  - Accueil:      http://localhost:{port}/index.html")
        print(f"  - Connexion:    http://localhost:{port}/login.html")
        print(f"  - Admin:        http://localhost:{port}/admin-dashboard.html")
        print("")
        print("⚠️  Le cache du navigateur est DÉSACTIVÉ pour le développement")
        print("")
        print("Appuyez sur Ctrl+C pour arrêter le serveur")
        print("=" * 60)
        print("")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nArrêt du serveur...")
            httpd.shutdown()
            sys.exit(0)

if __name__ == "__main__":
    main()

