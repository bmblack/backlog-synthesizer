# ADR-003: API Standards and Versioning

**Status**: Accepted
**Date**: 2024-01-25
**Decision Makers**: API Architecture Team, Product Management
**Tags**: api, standards, versioning, rest

---

## Context

We need to establish consistent API design standards to ensure:
- Backward compatibility for clients
- Clear versioning strategy
- Consistent error handling
- Predictable URL structures
- Proper HTTP semantics

## Decision

### API Style: REST

We will use **RESTful API design** following OpenAPI 3.0 specification.

**Not using**: GraphQL, gRPC, SOAP

### Versioning Strategy: URL-based

**Format**: `https://api.example.com/v1/resource`

**Version in URL path** (not header, not query parameter)

### URL Structure

```
https://api.example.com/v{version}/{resource}
https://api.example.com/v1/users
https://api.example.com/v1/projects/123/tasks
```

**Pattern**:
- Plural nouns for resources: `/users`, `/projects`, not `/user`, `/project`
- Nested resources up to 2 levels: `/projects/123/tasks` ✓, `/projects/123/tasks/456/comments` ✗
- No verbs in URLs: `/users/create` ✗, use `POST /users` ✓

### HTTP Methods

| Method | Purpose | Example | Idempotent |
|--------|---------|---------|------------|
| GET | Retrieve resource(s) | `GET /users/123` | Yes ✓ |
| POST | Create new resource | `POST /users` | No ✗ |
| PUT | Replace entire resource | `PUT /users/123` | Yes ✓ |
| PATCH | Partial update | `PATCH /users/123` | No ✗ |
| DELETE | Remove resource | `DELETE /users/123` | Yes ✓ |

### Response Format

**Success Responses**:
```json
{
  "data": { /* resource */ },
  "meta": {
    "timestamp": "2024-01-25T10:30:00Z",
    "version": "v1"
  }
}
```

**Collection Responses**:
```json
{
  "data": [ /* resources */ ],
  "meta": {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  },
  "links": {
    "self": "/v1/users?page=1",
    "next": "/v1/users?page=2",
    "prev": null,
    "first": "/v1/users?page=1",
    "last": "/v1/users?page=8"
  }
}
```

**Error Responses**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email address is invalid",
    "details": [
      {
        "field": "email",
        "issue": "Must be a valid email format"
      }
    ],
    "request_id": "req_abc123"
  },
  "meta": {
    "timestamp": "2024-01-25T10:30:00Z",
    "version": "v1"
  }
}
```

### HTTP Status Codes

**Success (2xx)**:
- `200 OK` - Successful GET, PUT, PATCH, DELETE
- `201 Created` - Successful POST (new resource)
- `202 Accepted` - Async operation queued
- `204 No Content` - Successful DELETE (no response body)

**Client Errors (4xx)**:
- `400 Bad Request` - Invalid request format
- `401 Unauthorized` - Missing/invalid authentication
- `403 Forbidden` - Valid auth but insufficient permissions
- `404 Not Found` - Resource doesn't exist
- `409 Conflict` - Resource conflict (duplicate, version mismatch)
- `422 Unprocessable Entity` - Validation errors
- `429 Too Many Requests` - Rate limit exceeded

**Server Errors (5xx)**:
- `500 Internal Server Error` - Unexpected error
- `502 Bad Gateway` - Upstream service failure
- `503 Service Unavailable` - Temporary unavailability
- `504 Gateway Timeout` - Upstream timeout

### Authentication

**Standard**: OAuth 2.0 with JWT Bearer tokens

```http
Authorization: Bearer <jwt_token>
```

**NOT using**: Basic Auth, API keys in query params, custom auth schemes

### Pagination

**Query Parameters**:
- `page` - Page number (1-based)
- `page_size` - Items per page (default: 20, max: 100)

```http
GET /v1/users?page=2&page_size=50
```

### Filtering, Sorting, Searching

**Filtering**:
```http
GET /v1/users?status=active&role=admin
```

**Sorting**:
```http
GET /v1/users?sort=created_at:desc,name:asc
```

**Searching**:
```http
GET /v1/users?search=john
```

### Versioning Policy

**When to increment version**:

**Major version (v1 → v2)**: Breaking changes
- Remove endpoint
- Remove required field
- Change field type
- Change response structure
- Change authentication method

**Backward-compatible changes (no version change)**:
- Add new endpoint
- Add optional field
- Add new response field
- Add new HTTP method to existing endpoint

**Version Support**:
- Support **N-1 versions** (current + previous)
- **6 months deprecation notice** before removing version
- **12 months minimum support** for each major version

## Constraints

### MUST Follow:

**API Design**:
- All APIs MUST use REST (no GraphQL, gRPC)
- Version MUST be in URL path: `/v1/resource`
- Resources MUST use plural nouns: `/users`, not `/user`
- URLs MUST NOT contain verbs: Use HTTP methods instead
- Response format MUST match standard structure (data/meta/links)

**Authentication**:
- All APIs MUST use OAuth 2.0 with JWT
- Tokens MUST be in `Authorization` header (not query params)
- MUST use HTTPS in production (no HTTP)

**Error Handling**:
- Error responses MUST use standard format (error/code/message/details)
- HTTP status codes MUST be semantically correct
- MUST include `request_id` in all error responses

**Pagination**:
- Collection endpoints MUST support pagination
- Default page size: 20 items
- Maximum page size: 100 items
- MUST include HATEOAS links (next, prev, first, last)

### MUST NOT:

**Prohibited Practices**:
- MUST NOT use version in headers or query params
- MUST NOT use verbs in URL paths
- MUST NOT nest resources more than 2 levels deep
- MUST NOT return different structures for same endpoint
- MUST NOT use HTTP 200 for errors (use proper error codes)
- MUST NOT expose internal IDs (use UUIDs or opaque tokens)
- MUST NOT return sensitive data in GET URLs (use POST for sensitive filters)

### SHOULD Consider:

**Recommended Practices**:
- Use `snake_case` for field names (not camelCase)
- Include `created_at`, `updated_at` timestamps
- Use ISO 8601 for dates: `2024-01-25T10:30:00Z`
- Return `Location` header with `201 Created`
- Support `If-Modified-Since` for caching
- Implement rate limiting (429 status)
- Log all requests with `request_id`

## Rationale

### Why REST over GraphQL:
1. **Simplicity**: Easier for external developers to consume
2. **Tooling**: Better support in API gateways, monitoring tools
3. **Caching**: HTTP caching works out-of-box
4. **Team Expertise**: 90% of team familiar with REST
5. **Overfetching Not a Problem**: Our use cases don't have complex nested queries

### Why URL Versioning:
1. **Visibility**: Version is immediately clear in URL
2. **Caching**: Different versions can be cached separately
3. **Simplicity**: No custom header parsing needed
4. **Documentation**: OpenAPI tools work seamlessly

### Why OAuth 2.0:
1. **Industry Standard**: Supported by all major platforms
2. **Security**: Token-based, no password transmission
3. **Flexibility**: Supports multiple grant types
4. **Revocation**: Tokens can be revoked without password change

## Compliance

**Stories must be rejected if they**:
- Propose creating a GraphQL or gRPC endpoint
- Place version in headers or query parameters
- Use verbs in URL paths (e.g., `/users/create`)
- Create nested resources beyond 2 levels
- Use non-standard authentication methods
- Return success responses with HTTP 500 status

**Stories should be flagged for review if they**:
- Need to break backward compatibility (requires major version)
- Propose rate limiting changes
- Add new authentication scopes
- Change error response format
- Introduce new HTTP status codes

## Examples

### Good API Design:

```http
POST /v1/users
Content-Type: application/json
Authorization: Bearer eyJhbGc...

{
  "email": "user@example.com",
  "name": "John Doe",
  "role": "admin"
}

Response: 201 Created
Location: /v1/users/usr_abc123
{
  "data": {
    "id": "usr_abc123",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "admin",
    "created_at": "2024-01-25T10:30:00Z",
    "updated_at": "2024-01-25T10:30:00Z"
  },
  "meta": {
    "timestamp": "2024-01-25T10:30:00Z",
    "version": "v1"
  }
}
```

### Bad API Design (Don't Do This):

```http
❌ POST /v1/createUser (verb in URL)
❌ GET /v1/user/123 (singular noun)
❌ GET /v1/users?version=2 (version in query)
❌ GET /v1/projects/1/tasks/2/comments/3/replies (too nested)
```

## Review Date

**Next Review**: 2024-07-25 (6 months) or when adopting GraphQL/gRPC.

## References

- OpenAPI 3.0 Specification
- Roy Fielding's REST Dissertation
- RFC 6749 (OAuth 2.0)
- RFC 7807 (Problem Details for HTTP APIs)
- Internal: API Design Guidelines v1.2

---

**Last Updated**: 2024-01-25
**Version**: 1.0
**Owner**: API Architecture Team
