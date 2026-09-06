/// Hôtes API MHC. Le sous-domaine `api.` a un certificat Let's Encrypt expiré
/// (05/09/2026) ; le domaine apex reste valide et reverse-proxy `/api/v1`.
const kLegacyApiHost = 'api.srv1324425.hstgr.cloud';
const kProductionApiHost = 'srv1324425.hstgr.cloud';
const kProductionApiBaseUrl = 'https://$kProductionApiHost/api/v1';
const kAppVersionLabel = '1.0.0+4';

/// Réécrit l'ancien hôte API vers le domaine au certificat valide.
String canonicalizeApiBaseUrl(String url) {
  return url.replaceAll(kLegacyApiHost, kProductionApiHost);
}
