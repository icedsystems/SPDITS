# ICED SPDITS
**Secure Partner Data Intake, SFTP Ingestion, Tracing & Interview Management System**

Built for The International Centre for Evaluation and Development (ICED).

---

## Overview

SPDITS is a full-stack Django web application that enables ICED to:

- Securely receive participant data from implementing partners (via web upload or SFTP)
- Pseudocode participant records — separating quasi-identifiers from direct identifiers
- Encrypt all direct identifiers (name, ID, phone, address) using Fernet symmetric encryption
- Track the tracing pipeline: Upload → Tracing → Traced → Assigned → Interviewed
- Manage assignments of traced participants to field enumerators
- Record interview outcomes and status history
- Provide role-differentiated dashboards for every user type
- Maintain a fully immutable audit trail of all system actions
- Allow secure re-identification with full audit logging (compliance-only)
- Monitor all activity via a dedicated compliance dashboard

---

## Quick Start (Docker)

### 1. Prerequisites

- Docker 24+
- Docker Compose v2

### 2. Clone and configure

```bash
git clone <repo-url>
cd spdits
cp .env.example .env
# Edit .env — set DJANGO_SECRET_KEY, DATABASE_URL, FIELD_ENCRYPTION_KEY, Azure OAuth creds
```

### 3. Generate SFTP host keys (first time only)

```bash
bash scripts/generate_sftp_keys.sh
```

### 4. Start the full stack

```bash
docker-compose up --build -d
```

### 5. Run initial setup

```bash
# Apply migrations
docker-compose exec app python manage.py migrate

# Create superuser (uses DJANGO_SUPERUSER_* env vars or defaults)
docker-compose exec app python manage.py ensure_superuser

# Collect static files (done automatically in entrypoint)
docker-compose exec app python manage.py collectstatic --noinput

# (Optional) Load demo data
docker-compose exec app python manage.py seed_demo_data --participants 100
```

### 6. Access the system

| Service      | URL                       |
|-------------|--------------------------|
| Web App     | http://localhost          |
| Django Admin| http://localhost/admin/   |
| Flower      | http://localhost:5555     |
| SFTP        | sftp://localhost:2222     |

---

## Stack

| Component    | Technology                                  |
|-------------|---------------------------------------------|
| Backend     | Python 3.12 + Django 4.2                    |
| Task Queue  | Celery 5 + Redis 7                          |
| Database    | PostgreSQL 16                               |
| Cache/Queue | Redis 7                                     |
| Frontend    | Bootstrap 5 + HTMX + Bootstrap Icons        |
| Auth        | Microsoft Azure Entra ID (OAuth2 via MSAL)  |
| Encryption  | Cryptography (Fernet) for direct identifiers|
| SFTP        | atmoz/sftp (OpenSSH)                        |
| Web Server  | nginx → gunicorn                            |
| Monitoring  | Flower (Celery), Sentry (optional)          |

---

## User Roles

| Role                | Access                                                          |
|--------------------|-----------------------------------------------------------------|
| System Admin        | Full access, upload approvals, user management, audit trail     |
| Implementing Partner| Upload files, view own batch statuses                           |
| Supervisor          | View tracing queue, assign participants, monitor enumerators    |
| Enumerator          | View own assignments, update interview status                   |
| Tracer              | Update tracing status for participants                          |
| Compliance Officer  | Re-identification access, compliance dashboard                  |

---

## Participant Pipeline

```
UPLOADED → TRACING → TRACED → ASSIGNED → INTERVIEWED → CLOSED
```

1. **UPLOADED** — Partner uploads CSV/XLSX. File is validated and pseudocoded.
2. **TRACING** — Tracer is working to locate the participant.
3. **TRACED** — Participant has been located. Ready for assignment.
4. **ASSIGNED** — Assigned to a field enumerator by supervisor.
5. **INTERVIEWED** — Interview completed (or refused/unreachable/callback).
6. **CLOSED** — Case closed.

---

## Encryption

All direct identifiers (name, national ID, passport, phone, address, email) are stored
encrypted using Fernet symmetric encryption. The encryption key is set via the
`FIELD_ENCRYPTION_KEY` environment variable.

**Generate a key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Re-identification requires explicit reason entry, is restricted to System Admins and
Compliance Officers, is fully logged, and data is auto-hidden after 60 seconds on screen.

---

## SFTP Configuration

Partners can upload files directly via SFTP instead of the web interface.

- **Host:** your-server-ip
- **Port:** 2222
- **Authentication:** SSH public key (preferred) or password
- The SFTP Celery beat task polls every 60 seconds for new files
- Detected files are automatically processed through the same pipeline as web uploads

---

## Environment Variables

| Variable                    | Description                                        |
|-----------------------------|----------------------------------------------------|
| `DJANGO_SECRET_KEY`         | Django secret key (generate a long random string)  |
| `DATABASE_URL`              | PostgreSQL connection string                       |
| `REDIS_URL`                 | Redis connection string                            |
| `FIELD_ENCRYPTION_KEY`      | Fernet key for encrypting direct identifiers       |
| `AZURE_AD_CLIENT_ID`        | Azure app registration client ID                   |
| `AZURE_AD_CLIENT_SECRET`    | Azure app registration client secret               |
| `AZURE_AD_TENANT_ID`        | Azure AD tenant ID                                 |
| `APP_URL`                   | Public URL of the app (for invitation links)       |
| `INVITATION_EXPIRY_HOURS`   | How long invitation links are valid (default: 1)   |
| `EMAIL_HOST`                | SMTP server hostname                               |
| `EMAIL_HOST_USER`           | SMTP username                                      |
| `EMAIL_HOST_PASSWORD`       | SMTP password                                      |
| `SENTRY_DSN`                | Sentry error tracking DSN (optional)               |
| `DJANGO_SUPERUSER_EMAIL`    | Initial superuser email (default: admin@iced.org)  |
| `DJANGO_SUPERUSER_PASSWORD` | Initial superuser password                         |

---

## Development

```bash
# Run locally (requires postgres + redis running)
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver

# Run celery worker
celery -A config.celery worker --loglevel=info

# Run celery beat
celery -A config.celery beat --loglevel=info
```

### Demo accounts (after seed_demo_data)

All use password: `spdits@2024!`

| Email                   | Role                 |
|------------------------|----------------------|
| admin@iced.org          | System Admin         |
| partner1@iced.org       | Implementing Partner |
| supervisor@iced.org     | Supervisor           |
| enumerator1@iced.org    | Enumerator           |
| tracer@iced.org         | Tracer               |
| compliance@iced.org     | Compliance Officer   |

---

## Azure AD / Microsoft OAuth Setup

1. In Azure Portal → App Registrations → New Registration
2. Set redirect URI: `https://your-domain.com/accounts/oauth/callback/`
3. Under Certificates & Secrets → create a client secret
4. Copy **Client ID**, **Tenant ID**, **Client Secret** to `.env`
5. Users must have a pre-existing SPDITS account matching their Microsoft email

---

## Security Considerations

- All direct identifiers are encrypted at rest (Fernet AES-128-CBC)
- Session timeout after 30 minutes of inactivity
- Full immutable audit trail — AuditLog records cannot be modified via ORM
- Re-identification is rate-limited, reason-required, IP-logged, and time-limited (60s display)
- SFTP uses SSH key authentication
- File uploads are validated: type, size (100MB max), MD5 checksum
- CSRF, XSS, clickjacking, HSTS protections enabled in production
- HTTPS enforced in production via nginx

---

## File Upload Format

**Accepted formats:** CSV, XLS, XLSX (max 100 MB)

| Column        | Required | Notes                            |
|--------------|----------|----------------------------------|
| name          | Yes      | Full name (stored encrypted)     |
| gender        | Yes      | Quasi-identifier                 |
| county        | Yes      | Quasi-identifier                 |
| national_id   | No       | Stored encrypted                 |
| passport      | No       | Stored encrypted                 |
| phone         | No       | Stored encrypted                 |
| alt_phone     | No       | Stored encrypted                 |
| email         | No       | Stored encrypted                 |
| address       | No       | Stored encrypted                 |
| age           | No       | Quasi-identifier                 |
| birth_year    | No       | Quasi-identifier                 |
| sub_county    | No       | Quasi-identifier                 |
| ward          | No       | Quasi-identifier                 |
