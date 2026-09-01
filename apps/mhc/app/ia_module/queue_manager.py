"""
Gestionnaire de queue pour traiter les demandes d'analyse de manière asynchrone
Permet de gérer plusieurs demandes simultanément sans bloquer le serveur
"""
import asyncio
import logging
from enum import Enum
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

class StatutDemande(Enum):
    """Statuts possibles d'une demande"""
    EN_ATTENTE = "en_attente"
    EN_TRAITEMENT = "en_traitement"
    TERMINE = "termine"
    ERREUR = "erreur"

class QueueManager:
    """
    Gestionnaire de queue pour traiter les demandes d'analyse
    
    Utilise un pool de workers pour traiter plusieurs demandes en parallèle
    """
    
    def __init__(self, max_workers: int = 3):
        """
        Initialise le gestionnaire de queue
        
        Args:
            max_workers: Nombre maximum de workers pour traiter les demandes
        """
        self.max_workers = max_workers
        self.demandes: Dict[str, Dict] = {}  # {demande_id: {status, created_at, result, error}}
        self.queue: asyncio.Queue = None
        self.workers: list = []
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
        self._loop = None
        self._running = False
        
        logger.info(f"✅ QueueManager initialisé avec {max_workers} workers")
    
    def _get_loop(self):
        """Récupère ou crée la boucle d'événements"""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    async def _worker(self):
        """Worker qui traite les demandes de la queue"""
        while self._running:
            try:
                # Récupérer une demande de la queue (timeout de 1 seconde)
                item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                demande_id, fonction, *args = item
                
                # Mettre à jour le statut
                with self.lock:
                    if demande_id in self.demandes:
                        self.demandes[demande_id]["status"] = StatutDemande.EN_TRAITEMENT.value
                
                logger.info(f"🔄 Worker traite la demande {demande_id}")
                
                try:
                    # Exécuter la fonction de traitement
                    if asyncio.iscoroutinefunction(fonction):
                        result = await fonction(*args)
                    else:
                        # Si c'est une fonction synchrone, l'exécuter dans le thread pool
                        loop = self._get_loop()
                        result = await loop.run_in_executor(self.executor, fonction, *args)
                    
                    # Mettre à jour avec le résultat
                    with self.lock:
                        if demande_id in self.demandes:
                            self.demandes[demande_id]["status"] = StatutDemande.TERMINE.value
                            self.demandes[demande_id]["result"] = result
                            self.demandes[demande_id]["completed_at"] = datetime.now().isoformat()
                    
                    logger.info(f"✅ Demande {demande_id} traitée avec succès")
                    
                except Exception as e:
                    # Mettre à jour avec l'erreur
                    error_msg = str(e)
                    logger.error(f"❌ Erreur lors du traitement de {demande_id}: {error_msg}")
                    
                    with self.lock:
                        if demande_id in self.demandes:
                            self.demandes[demande_id]["status"] = StatutDemande.ERREUR.value
                            self.demandes[demande_id]["error"] = error_msg
                
                finally:
                    self.queue.task_done()
                    
            except asyncio.TimeoutError:
                # Timeout normal, continuer la boucle
                continue
            except Exception as e:
                logger.error(f"❌ Erreur dans le worker: {e}")
                await asyncio.sleep(1)  # Attendre avant de réessayer
    
    async def _start_workers(self):
        """Démarre les workers"""
        if self._running:
            return
        
        self._running = True
        self.queue = asyncio.Queue()
        
        # Créer les workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker())
            self.workers.append(worker)
            logger.info(f"✅ Worker {i+1}/{self.max_workers} démarré")
    
    async def ajouter_demande(
        self,
        demande_id: str,
        fonction: Callable,
        *args
    ):
        """
        Ajoute une demande à la queue pour traitement asynchrone
        
        Args:
            demande_id: ID unique de la demande
            fonction: Fonction à exécuter (peut être async ou sync)
            *args: Arguments à passer à la fonction
        """
        # Démarrer les workers si ce n'est pas déjà fait
        if not self._running:
            await self._start_workers()
        
        # Enregistrer la demande
        with self.lock:
            self.demandes[demande_id] = {
                "status": StatutDemande.EN_ATTENTE.value,
                "created_at": datetime.now().isoformat(),
                "result": None,
                "error": None
            }
        
        # Ajouter à la queue
        await self.queue.put((demande_id, fonction, *args))
        
        logger.info(f"📥 Demande {demande_id} ajoutée à la queue")
    
    def get_status(self, demande_id: str) -> Optional[Dict]:
        """
        Récupère le statut d'une demande
        
        Args:
            demande_id: ID de la demande
        
        Returns:
            Dictionnaire avec le statut ou None si la demande n'existe pas
        """
        with self.lock:
            return self.demandes.get(demande_id)
    
    def get_stats(self) -> Dict:
        """
        Retourne les statistiques de la queue
        
        Returns:
            Dictionnaire avec les statistiques
        """
        with self.lock:
            total = len(self.demandes)
            en_attente = sum(1 for d in self.demandes.values() 
                          if d["status"] == StatutDemande.EN_ATTENTE.value)
            en_traitement = sum(1 for d in self.demandes.values() 
                              if d["status"] == StatutDemande.EN_TRAITEMENT.value)
            terminees = sum(1 for d in self.demandes.values() 
                          if d["status"] == StatutDemande.TERMINE.value)
            erreurs = sum(1 for d in self.demandes.values() 
                         if d["status"] == StatutDemande.ERREUR.value)
            
            return {
                "total": total,
                "en_attente": en_attente,
                "en_traitement": en_traitement,
                "terminees": terminees,
                "erreurs": erreurs,
                "workers": self.max_workers
            }
    
    async def stop(self):
        """Arrête les workers et nettoie les ressources"""
        self._running = False
        
        # Attendre que tous les workers se terminent
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Arrêter l'executor
        self.executor.shutdown(wait=True)
        
        logger.info("🛑 QueueManager arrêté")
