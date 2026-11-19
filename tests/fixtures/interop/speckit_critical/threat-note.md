# Threat Note: Payment Gateway Integration

## Boundaries and Assets
- Payment card tokens and transaction nonces.
- Third-party payment gateway connection.

## Threats and Mitigations
- Replay attacks: Enforce idempotent transaction keys with Redis expiry.
- Man-in-the-middle: Enforce certificate pinning on payment gateway endpoint.

