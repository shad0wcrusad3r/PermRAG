# API Development Standards

This document defines coding standards for API development at Initech.

## REST API Design

### Endpoint Naming
- Use nouns, not verbs: `/users` not `/getUsers`
- Use plural forms: `/products` not `/product`
- Use kebab-case for multi-word resources: `/order-items`

### HTTP Methods
- GET: Retrieve resources
- POST: Create new resources
- PUT: Update entire resource
- PATCH: Partial update
- DELETE: Remove resource

## Authentication

All API endpoints must use JWT bearer tokens for authentication.

## Error Handling

Return appropriate HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad request
- 401: Unauthorized
- 404: Not found
- 500: Server error

Include error messages in JSON format with a consistent structure.

## Versioning

Include API version in the URL path: `/api/v1/users`

## Documentation

Use OpenAPI (Swagger) specification for all APIs. Keep documentation up to date with code changes.
