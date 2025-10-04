# apps/core/auth.py
#### DIKKAT NEJO
#######
#auth implementation stopped for a while come back here...!!!!!!!!!!!!!!
#######
###
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import requests
from cachetools import TTLCache
from django.conf import settings
from rest_framework import authentication, exceptions
from jose import jwt

log = logging.getLogger("docuchat.auth")

# Küçük bir runtime cache (issuer cfg ve JWKS)
_cfg_cache = TTLCache(maxsize=4, ttl=3600)    # 1 saat
_jwks_cache = TTLCache(maxsize=2, ttl=3600)   # 1 saat

def _getenv(name: str, default: str = "") -> str:
    return getattr(settings, name, "") or default

def _get_oidc_cfg(issuer: str) -> Dict[str, Any]:
    """Issuer için .well-known config’i indir (veya cache’ten al)."""
    if not issuer:
        raise exceptions.AuthenticationFailed("OIDC not configured (ISSUER missing)")
    try:
        return _cfg_cache[issuer]
    except KeyError:
        url = issuer.rstrip("/") + "/.well-known/openid-configuration"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        _cfg_cache[issuer] = data
        return data

def _get_jwks(jwks_url: str) -> Dict[str, Any]:
    if not jwks_url:
        raise exceptions.AuthenticationFailed("OIDC not configured (JWKS url missing)")
    try:
        return _jwks_cache[jwks_url]
    except KeyError:
        resp = requests.get(jwks_url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        _jwks_cache[jwks_url] = data
        return data

def _pick_key(jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, Any]]:
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            return k
    return None

def _aud_ok(claim_aud: Any, expected: str) -> bool:
    if not expected:
        return False
    if isinstance(claim_aud, str):
        return claim_aud == expected
    if isinstance(claim_aud, (list, tuple, set)):
        return expected in claim_aud
    return False

def _roles_ok(claims: Dict[str, Any], required_roles: list[str]) -> bool:
    if not required_roles:
        return True
    # Keycloak realm role path: realm_access.roles = [...]
    roles = claims.get("realm_access", {}).get("roles", []) or []
    return all(r in roles for r in required_roles)

class KeycloakAuthentication(authentication.BaseAuthentication):
    """
    - Authorization: Bearer <JWT>
    - Doğrulamalar:
        * issuer == OIDC_ISSUER
        * imza RS256 (JWKS'ten key ile)
        * exp/nbf/iAT (leeway ile)
        * audience veya azp (esnek)
        * (opsiyon) required roles
    - Hatalarda AuthenticationFailed (401) fırlatır; 500 vermez.
    """

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None  # Token yoksa DRF devam eder; IsAuthenticated ise 401'e kendisi düşer

        token = auth.split(" ", 1)[1].strip()
        issuer = _getenv("OIDC_ISSUER")
        audience = _getenv("OIDC_AUDIENCE")
        expected_client = _getenv("OIDC_CLIENT_ID") or "docuchat-frontend"
        required_roles_csv = _getenv("OIDC_REQUIRED_ROLES", "")  # "admin,editor" gibi
        required_roles = [r.strip() for r in required_roles_csv.split(",") if r.strip()]

        # .well-known’dan jwks_uri’yi al (yoksa OIDC_JWKS_URL fallback)
        cfg = _get_oidc_cfg(issuer)
        jwks_url = _getenv("OIDC_JWKS_URL") or cfg.get("jwks_uri", "")

        try:
            # Key seçimi
            unverified = jwt.get_unverified_header(token)
            kid = unverified.get("kid")
            if not kid:
                raise exceptions.AuthenticationFailed("Token header has no kid")

            jwks = _get_jwks(jwks_url)
            key = _pick_key(jwks, kid)
            if not key:
                raise exceptions.AuthenticationFailed("No matching JWKS key for kid")

            # JWT decode (audience'ı burada zorlamayacağız; kendimiz kontrol edeceğiz)
            leeway = int(_getenv("OIDC_LEEWAY", "30"))  # saniye (clock skew için)
            claims = jwt.decode(
                token,
                key,
                options={"verify_aud": False},  # aud'u manuel kontrol
                issuer=issuer,
                algorithms=[key.get("alg", "RS256")],
                leeway=leeway,
            )

            # Audience / azp esnek kontrol
            aud_ok = _aud_ok(claims.get("aud"), audience)
            azp_ok = (claims.get("azp") == (expected_client or audience) or
                      claims.get("azp") == expected_client)
            if not (aud_ok or azp_ok):
                raise exceptions.AuthenticationFailed("Invalid audience/azp")

            # Rol kontrolü (opsiyonel)
            if not _roles_ok(claims, required_roles):
                raise exceptions.AuthenticationFailed("Required role missing")

            # Basit user objesi (AnonymousUser'ı işaretleyip kullanıyoruz)
            from django.contrib.auth.models import AnonymousUser
            user = AnonymousUser()
            user.is_authenticated = True  # type: ignore[attr-defined]
            user.username = (claims.get("preferred_username")
                             or claims.get("email")
                             or claims.get("sub")
                             or "user")  # type: ignore[attr-defined]

            # log: kim geldi, hangi iss/model
            log.info("Auth OK user=%s aud=%s azp=%s iss=%s",
                     user.username, claims.get("aud"), claims.get("azp"), issuer)

            return (user, claims)

        except exceptions.AuthenticationFailed:
            raise
        except requests.RequestException as e:
            log.warning("OIDC metadata/JWKS fetch failed: %s", e)
            raise exceptions.AuthenticationFailed("OIDC metadata fetch failed")
        except Exception as e:
            # hiçbiri 500'e dönmesin; 401 olarak dönsün
            log.debug("JWT validation error: %s", e, exc_info=True)
            raise exceptions.AuthenticationFailed(f"Invalid token")
