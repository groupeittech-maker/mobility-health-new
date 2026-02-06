# Résolution des erreurs Celery sur Windows

## Problème

Sur Windows, Celery utilise par défaut le pool `prefork` qui n'est pas compatible avec Windows et cause des erreurs :
- `PermissionError: [WinError 5] Accès refusé`
- `OSError: [WinError 6] Descripteur non valide`

## Solution

Utiliser le pool `solo` qui est compatible avec Windows. Le script `start_celery_worker.ps1` a été modifié pour utiliser `--pool=solo` au lieu de `--concurrency=4` (qui utilise prefork).

## Redémarrer les workers

1. Arrêtez tous les workers Celery en cours (fermez les fenêtres PowerShell)
2. Redémarrez les workers avec :
   ```powershell
   .\scripts\start_all_workers.ps1
   ```

## Note

Le pool `solo` fonctionne en mode séquentiel (un seul thread), ce qui est suffisant pour le développement. Pour la production sur Linux, vous pouvez utiliser `prefork` ou `gevent`.

