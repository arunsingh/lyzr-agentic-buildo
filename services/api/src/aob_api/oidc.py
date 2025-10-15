from __future__ import annotations
import os, time, json
from typing import Dict, Any, Optional, List
import httpx
from jose import jwk, jwt
from jose.utils import base64url_decode


class OIDC:
    def __init__(self):
        self.issuer = os.getenv("OIDC_ISSUER_URL", "http://localhost:8089/realms/demo")
        self.audience = os.getenv("OIDC_AUDIENCE", "aob-api")
        self.required_scopes = set((os.getenv("OIDC_REQUIRED_SCOPES", "").split() or []))
        self._jwks: Optional[Dict[str, Any]] = None
        self._jwks_ts = 0.0

    async def _get_jwks(self) -> Dict[str, Any]:
        if self._jwks and (time.time() - self._jwks_ts) < 300:
            return self._jwks
        async with httpx.AsyncClient(timeout=5.0) as client:
            jwks_uri = f"{self.issuer}/protocol/openid-connect/certs"
            r = await client.get(jwks_uri)
            r.raise_for_status()
            self._jwks = r.json()
            self._jwks_ts = time.time()
            return self._jwks

    async def validate(self, token: str) -> Dict[str, Any]:
        # Decode headers to fetch key id
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        jwks = await self._get_jwks()
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise ValueError("JWK not found")
        public_key = jwk.construct(key)
        message, encoded_sig = str(token).rsplit('.', 1)
        decoded_sig = base64url_decode(encoded_sig.encode('utf-8'))
        if not public_key.verify(message.encode('utf-8'), decoded_sig):
            raise ValueError("Invalid signature")
        claims = jwt.get_unverified_claims(token)
        if claims.get("iss") != self.issuer:
            raise ValueError("Issuer mismatch")
        aud = claims.get("aud")
        if isinstance(aud, list):
            if self.audience not in aud and "account" not in aud:
                raise ValueError("Audience mismatch")
        elif aud != self.audience and aud != "account":
            raise ValueError("Audience mismatch")
        if claims.get("exp", 0) < time.time():
            raise ValueError("Token expired")
        scopes = set((claims.get("scope", "").split() or []))
        if self.required_scopes and not self.required_scopes.issubset(scopes):
            raise ValueError("Missing required scopes")
        return claims

    @staticmethod
    def tenant_from_claims(claims: Dict[str, Any]) -> str:
        return claims.get("tenant_id") or claims.get("realm_access", {}).get("realm") or claims.get("iss", "public").split("/realms/")[-1]

