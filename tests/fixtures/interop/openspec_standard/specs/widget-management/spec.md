# Spec Delta: Widget Management

## Purpose
Provides predictable widget creation and status inspection for client applications.

## ADDED Requirements

### Requirement: Create widget
The system SHALL create a widget when provided a valid alphanumeric name.

#### Scenario: Valid widget creation
- **WHEN** client submits a valid widget name
- **THEN** system creates widget and returns status code 201

#### Scenario: Invalid widget creation
- **WHEN** client submits an empty widget name
- **THEN** system rejects request with status code 400

### Requirement: Query widget status
The system SHALL return active status for an existing widget.

#### Scenario: Query existing widget
- **WHEN** client queries an existing widget ID
- **THEN** system returns status code 200 with active state

