"""Helpers d'en-têtes HTTP."""

import unicodedata
from urllib.parse import quote


def content_disposition(disposition: str, filename: str) -> str:
    """Valeur ``Content-Disposition`` sûre pour un nom de fichier arbitraire.

    Les navigateurs exigent des en-têtes latin-1 : un nom contenant des
    caractères hors latin-1 (ex. apostrophe typographique U+2019, accents
    étendus) lève ``UnicodeEncodeError`` côté Starlette → HTTP 500.
    On émet donc un ``filename`` ASCII de repli + ``filename*`` RFC 5987.
    """
    dispo = "inline" if disposition == "inline" else "attachment"
    raw = (filename or "document").strip() or "document"
    ascii_name = (
        unicodedata.normalize("NFKD", raw)
        .encode("ascii", "ignore")
        .decode()
        .replace('"', "'")
        .replace("\\", "-")
        .replace("/", "-")
        .strip()
    ) or "document"
    return f"{dispo}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(raw)}"
