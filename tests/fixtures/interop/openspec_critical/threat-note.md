# Threat Note: Secure Authentication Service

## Boundaries and Assets
- Authenticated session tokens and password hashes.
- External untrusted network boundaries.

## Threats and Mitigations
- Credential stuffing: Rate limit login attempts to 5 per minute per IP.
- Token leakage: Tokens are signed HMAC-SHA256 with 15-minute expiry.

