# Design: Secure Authentication Service

## Context
See proposal.md - Why. Replaces legacy plaintext credentials with signed token flow.

## Goals / Non-Goals
**Goals:** Secure stateless JWT verification.
**Non-Goals:** OAuth2 third-party federated logins.

## Decisions
- Use HS256 with 256-bit rotating secrets.

## Risks / Trade-offs
[Key compromise] -> Immediate revocation and key rotation list.

