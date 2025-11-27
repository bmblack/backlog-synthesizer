# ADR-004: Security Requirements and Standards

**Status**: Accepted
**Date**: 2024-02-01
**Decision Makers**: Security Team, CTO, Compliance Officer
**Tags**: security, authentication, encryption, compliance

---

## Context

We need to establish baseline security requirements for all systems to ensure:
- Data protection (encryption at rest and in transit)
- Secure authentication and authorization
- Protection against common vulnerabilities (OWASP Top 10)
- Compliance with industry standards (SOC 2, GDPR)

## Decision

### Authentication & Authorization

**Standard**: OAuth 2.0 + OpenID Connect (OIDC)

**Requirements**:
- All APIs MUST use OAuth 2.0 with JWT Bearer tokens
- JWT tokens MUST expire within 1 hour
- Refresh tokens MUST expire within 7 days
- MUST support token revocation
- MUST implement Multi-Factor Authentication (MFA) for admin accounts
- MUST use PKCE (Proof Key for Code Exchange) for public clients

**Password Requirements**:
- Minimum 12 characters
- Must include: uppercase, lowercase, number, special character
- MUST use bcrypt (cost factor 12) or Argon2 for hashing
- MUST NOT store passwords in plain text or using MD5/SHA1
- MUST implement rate limiting on login attempts (5 attempts per 15 minutes)
- MUST implement account lockout after 10 failed attempts

### Data Encryption

**In Transit**:
- MUST use TLS 1.3 (TLS 1.2 minimum)
- MUST NOT allow TLS 1.0, TLS 1.1, or SSL
- MUST use HTTPS for all external endpoints (no HTTP)
- MUST use strong cipher suites (AES-256-GCM preferred)
- MUST implement HSTS (HTTP Strict Transport Security)

**At Rest**:
- MUST encrypt sensitive data in database (PII, credentials, financial data)
- MUST use AES-256 encryption
- MUST use separate encryption keys per data type
- MUST rotate encryption keys annually
- MUST store encryption keys in dedicated key management service (AWS KMS, HashiCorp Vault)

**What Must Be Encrypted**:
- User passwords (hashed with bcrypt/Argon2)
- API keys and secrets
- Personal Identifiable Information (PII): SSN, credit cards, addresses
- Financial data: payment info, transaction details
- Authentication tokens and session data

**What Should Be Encrypted**:
- Email addresses
- Phone numbers
- User preferences containing sensitive choices

**What Doesn't Need Encryption**:
- Public profile information (username, display name, avatar)
- Non-sensitive application logs
- Publicly available content

### Input Validation & Sanitization

**Requirements**:
- MUST validate all input data (API, forms, file uploads)
- MUST use parameterized queries for database access (no string concatenation)
- MUST sanitize HTML output to prevent XSS attacks
- MUST validate file types and scan for malware
- MUST limit file upload sizes (default: 10MB)
- MUST implement Content Security Policy (CSP) headers
- MUST validate JSON schema for API requests

**Prohibited Practices**:
- MUST NOT use `eval()` or `exec()` on user input
- MUST NOT trust client-side validation alone
- MUST NOT expose stack traces to users
- MUST NOT log sensitive data (passwords, tokens, PII)

### API Security

**Requirements**:
- MUST implement rate limiting (default: 100 req/min per user, 1000 req/min per IP)
- MUST log all authentication attempts (success and failure)
- MUST implement request signing for webhooks
- MUST use CORS policies (whitelist allowed origins)
- MUST validate JWT signatures and expiration
- MUST include security headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security: max-age=31536000`

### Secrets Management

**Requirements**:
- MUST NOT commit secrets to version control (use .env, .gitignore)
- MUST use environment variables or secrets manager for credentials
- MUST rotate API keys and tokens quarterly
- MUST use separate credentials for dev/staging/production
- MUST implement secret scanning in CI/CD pipeline
- MUST use dedicated secrets management tool (AWS Secrets Manager, HashiCorp Vault, 1Password)

**Prohibited Practices**:
- MUST NOT hardcode API keys, passwords, or tokens in code
- MUST NOT store secrets in plain text files
- MUST NOT share credentials via email, Slack, or public channels
- MUST NOT reuse production credentials in development

### Vulnerability Protection (OWASP Top 10)

**1. Injection Attacks**:
- Use parameterized queries (SQLAlchemy ORM)
- Validate and sanitize all inputs
- Use prepared statements

**2. Broken Authentication**:
- Implement OAuth 2.0 + OIDC
- Use secure session management
- Implement MFA for sensitive operations

**3. Sensitive Data Exposure**:
- Encrypt data at rest and in transit
- Use HTTPS everywhere
- Don't log sensitive data

**4. XML External Entities (XXE)**:
- Disable XML external entity processing
- Use JSON instead of XML where possible

**5. Broken Access Control**:
- Implement role-based access control (RBAC)
- Validate permissions on every request
- Use principle of least privilege

**6. Security Misconfiguration**:
- Use security headers
- Disable directory listing
- Remove default credentials

**7. Cross-Site Scripting (XSS)**:
- Sanitize HTML output
- Use Content Security Policy
- Escape user-generated content

**8. Insecure Deserialization**:
- Validate serialized objects
- Use JSON instead of pickle
- Implement integrity checks

**9. Using Components with Known Vulnerabilities**:
- Run dependency scanning (Snyk, Dependabot)
- Keep dependencies updated
- Monitor security advisories

**10. Insufficient Logging & Monitoring**:
- Log all security events
- Implement alerting for anomalies
- Retain logs for 90 days minimum

### Compliance Requirements

**GDPR (if applicable)**:
- Implement data deletion on request (right to be forgotten)
- Provide data export functionality (right to data portability)
- Obtain explicit consent for data collection
- Report breaches within 72 hours

**SOC 2 (if applicable)**:
- Implement audit logging
- Annual security assessments
- Incident response procedures
- Access control reviews

### Security Testing

**Requirements**:
- MUST run static analysis (SAST) on every commit (Bandit for Python)
- MUST run dependency scanning on every PR (Snyk, OWASP Dependency-Check)
- MUST perform penetration testing annually
- MUST conduct security code reviews for sensitive features
- SHOULD run dynamic analysis (DAST) on staging environments

## Constraints

### MUST Implement:

**Authentication**:
- OAuth 2.0 + JWT for all APIs
- MFA for admin accounts
- Password complexity requirements (12+ chars, mixed case, numbers, symbols)
- bcrypt or Argon2 for password hashing (NO MD5, SHA1, or plain text)
- Rate limiting on authentication endpoints

**Encryption**:
- HTTPS/TLS 1.3 for all external communication (no HTTP in production)
- AES-256 encryption for sensitive data at rest
- Encrypted database fields for PII, credentials, financial data

**Input Validation**:
- Parameterized queries for all database operations (no SQL concatenation)
- Input validation on all API endpoints
- File upload validation and malware scanning
- XSS protection with output sanitization

**Secrets**:
- No secrets in version control (use .env + .gitignore)
- Secrets management tool (AWS Secrets Manager, Vault, etc.)
- Separate credentials per environment (dev/staging/prod)

**Headers**:
- Security headers on all responses (HSTS, CSP, X-Frame-Options, etc.)
- CORS policies with whitelisted origins

**Logging**:
- Log all authentication attempts
- Log all authorization failures
- Log all API errors
- NO logging of passwords, tokens, or PII

### MUST NOT:

**Prohibited Practices**:
- NO hardcoded secrets in code
- NO plain text password storage
- NO MD5 or SHA1 for passwords
- NO HTTP in production (HTTPS only)
- NO `eval()` or `exec()` on user input
- NO SQL string concatenation (use parameterized queries)
- NO sensitive data in logs (passwords, tokens, credit cards)
- NO exposed stack traces to users
- NO default credentials in production
- NO disabled security features (CORS, CSP, rate limiting)

### SHOULD Consider:

**Recommended Practices**:
- Security code reviews for authentication/authorization features
- Penetration testing before major releases
- Bug bounty program for production systems
- Regular security training for developers
- Automated security scanning in CI/CD
- Incident response playbook
- Security champions in each team

## Rationale

### Why OAuth 2.0 + JWT:
1. **Industry Standard**: Widely adopted, well-documented
2. **Stateless**: No server-side session storage needed
3. **Scalable**: Works across microservices
4. **Flexible**: Supports multiple grant types
5. **Secure**: Token-based, short-lived, revocable

### Why TLS 1.3:
1. **Performance**: Faster handshake (1-RTT vs 2-RTT)
2. **Security**: Removed insecure cipher suites
3. **Privacy**: Encrypted handshake metadata
4. **Future-Proof**: Modern standard

### Why bcrypt/Argon2:
1. **Adaptive**: Can increase cost factor as hardware improves
2. **Salted**: Built-in random salt per password
3. **Slow**: Intentionally slow to resist brute force
4. **Battle-Tested**: Industry standard for password hashing

### Why Parameterized Queries:
1. **SQL Injection Prevention**: 100% protection against SQLi
2. **Automatic Escaping**: Database driver handles escaping
3. **Best Practice**: Recommended by OWASP
4. **Maintainability**: Cleaner code than manual escaping

## Compliance

**Stories must be rejected if they**:
- Propose storing passwords in plain text or with weak hashing (MD5, SHA1)
- Suggest using HTTP in production environments
- Create SQL queries with string concatenation
- Store secrets in version control
- Disable security features (CORS, rate limiting, etc.)
- Expose sensitive data in logs or error messages
- Allow file uploads without validation
- Use `eval()` or `exec()` on user input

**Stories should be flagged for review if they**:
- Handle PII, financial data, or authentication
- Implement new API endpoints (security review needed)
- Modify authentication or authorization logic
- Change encryption keys or algorithms
- Access external APIs or services
- Upload/download files
- Implement webhooks or callbacks

## Security Checklist

Before deploying to production:

- [ ] All secrets removed from code (no hardcoded credentials)
- [ ] .env file added to .gitignore
- [ ] HTTPS enabled with TLS 1.3
- [ ] Security headers configured (HSTS, CSP, X-Frame-Options)
- [ ] OAuth 2.0 + JWT authentication implemented
- [ ] Password hashing uses bcrypt (cost 12) or Argon2
- [ ] Rate limiting enabled on all API endpoints
- [ ] Input validation on all user inputs
- [ ] SQL queries use parameterized queries
- [ ] File uploads validated and scanned
- [ ] Sensitive data encrypted at rest (PII, credentials)
- [ ] Logging enabled for authentication/authorization events
- [ ] No sensitive data logged (passwords, tokens, PII)
- [ ] Dependency scanning passing (no critical vulnerabilities)
- [ ] CORS policies configured (whitelisted origins)
- [ ] MFA enabled for admin accounts
- [ ] Incident response plan documented

## Review Date

**Next Review**: 2024-08-01 (6 months) or after security incident/audit.

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
- OAuth 2.0 RFC 6749: https://datatracker.ietf.org/doc/html/rfc6749
- NIST Password Guidelines: https://pages.nist.gov/800-63-3/
- PCI DSS 3.2.1 (for payment card data)
- Internal: Security Policy v2.1
- Internal: Incident Response Playbook

---

**Last Updated**: 2024-02-01
**Version**: 1.0
**Owner**: Security Team
