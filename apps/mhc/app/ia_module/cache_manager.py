"""
Gestionnaire de cache pour stocker les résultats d'analyse
Évite de réanalyser les mêmes fichiers
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Gestionnaire de cache en mémoire avec TTL (Time To Live)
    Utilise LRU (Least Recently Used) pour limiter la taille
    """
    
    def __init__(self, ttl_hours: int = 24, max_size: int = 1000):
        """
        Initialise le gestionnaire de cache
        
        Args:
            ttl_hours: Durée de vie des entrées en heures (défaut: 24h)
            max_size: Taille maximale du cache (défaut: 1000)
        """
        self.ttl_hours = ttl_hours
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict] = OrderedDict()
        self.hits = 0
        self.misses = 0
        
        logger.info(f"✅ CacheManager initialisé (TTL: {ttl_hours}h, Max: {max_size})")
    
    def _is_expired(self, entry: Dict) -> bool:
        """Vérifie si une entrée du cache a expiré"""
        if "expires_at" not in entry:
            return True
        
        expires_at = entry["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        return datetime.now() > expires_at
    
    def _cleanup_expired(self):
        """Nettoie les entrées expirées"""
        to_remove = []
        for key, entry in self.cache.items():
            if self._is_expired(entry):
                to_remove.append(key)
        
        for key in to_remove:
            del self.cache[key]
            self.misses += 1  # Compter comme un miss car on ne peut pas l'utiliser
        
        if to_remove:
            logger.debug(f"🧹 {len(to_remove)} entrées expirées nettoyées")
    
    def _evict_lru(self):
        """Supprime l'entrée la moins récemment utilisée si le cache est plein"""
        if len(self.cache) >= self.max_size:
            # Supprimer la première entrée (la moins récemment utilisée)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"🗑️ Entrée LRU supprimée: {oldest_key[:20]}...")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Récupère une valeur du cache
        
        Args:
            key: Clé de l'entrée (généralement le chemin du fichier)
        
        Returns:
            La valeur mise en cache ou None si absente/expirée
        """
        # Nettoyer les entrées expirées
        self._cleanup_expired()
        
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        
        # Vérifier si expirée
        if self._is_expired(entry):
            del self.cache[key]
            self.misses += 1
            return None
        
        # Déplacer à la fin (LRU - most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        
        return entry["value"]
    
    def set(self, key: str, value: Any):
        """
        Stocke une valeur dans le cache
        
        Args:
            key: Clé de l'entrée
            value: Valeur à stocker
        """
        # Nettoyer les entrées expirées
        self._cleanup_expired()
        
        # Évincer si nécessaire
        self._evict_lru()
        
        # Calculer la date d'expiration
        expires_at = datetime.now() + timedelta(hours=self.ttl_hours)
        
        # Stocker l'entrée
        self.cache[key] = {
            "value": value,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        # Déplacer à la fin (LRU - most recently used)
        self.cache.move_to_end(key)
    
    def clear(self):
        """Vide complètement le cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("🗑️ Cache vidé")
    
    def get_stats(self) -> Dict:
        """
        Retourne les statistiques du cache
        
        Returns:
            Dictionnaire avec les statistiques
        """
        self._cleanup_expired()
        
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "ttl_hours": self.ttl_hours
        }
