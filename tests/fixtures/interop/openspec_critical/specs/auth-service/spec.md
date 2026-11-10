# Spec Delta: Secure Authentication Service

## Purpose
Provides secure authentication and verifiable cryptographic token exchange.

## ADDED Requirements

### Requirement: Issue token
The system SHALL issue a signed HMAC-SHA256 token upon valid credentials.

#### Scenario: Valid login credential
- **WHEN** client posts valid user credentials
- **THEN** system returns 200 with signed auth token

#### Scenario: Invalid login credential
- **WHEN** client posts invalid user credentials
- **THEN** system returns 401 with unauthorized error

