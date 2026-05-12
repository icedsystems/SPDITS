# ICED SPDITS
**Secure Partner Data Intake, SFTP Ingestion, Participant Tracing & Interview Management System**

Built for **The International Centre for Evaluation and Development (ICED)**.

- **Production URL:** https://ea.data.iced-eval.org
- **GitHub:** https://github.com/icedsystems/SPDITS

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Stack](#stack)
4. [User Roles](#user-roles)
5. [Participant Pipeline](#participant-pipeline)
6. [Pseudocoding & Encryption](#pseudocoding--encryption)
7. [File Upload Format](#file-upload-format)
8. [Environment Variables](#environment-variables)
9. [Production Deployment](#production-deployment)
10. [Local Development](#local-development)
11. [SFTP Ingestion](#sftp-ingestion)
12. [Email Configuration](#email-configuration)
13. [Azure AD / Microsoft OAuth](#azure-ad--microsoft-oauth)
14. [Security](#security)
15. [Demo Accounts](#demo-accounts)
16. [Related Documents](#related-documents)

---

## Overview

SPDITS enables ICED to:

- Receive participant data from implementing partners via **web upload** or **SFTP**
- **Pseudocode** every participant — separating quasi-identifiers from direct identifiers at ingest
- **Encrypt** all direct identifiers (name, ID, phone, address) before storing in the database
- Track the full field pipeline: Upload → Tracing → Traced → Assigned → Interviewed
- Assign traced participants to field enumerators via supervisor bulk assignment
- Let enumerators record interview outcomes directly from their assignments dashboard
- Provide **role-differentiated dashboards** for every user type
- Maintain a **fully immutable audit trail** of every action in the system
- Allow **secure re-identification** with mandatory reason logging (compliance/admin only)

---

## Architecture

```
Browser (Bootstrap 5 + HTMX)
        │
        ▼
    Django 4.2 (Gunicorn)
        │
        ├── PostgreSQL 16         — main data store (external, port 5440)
        ├── Redis 7               — cache + session storage
        └── Media (bind mount)    — uploaded files at ./media/
```

### Code structure

```
spdits/
├── config/             # Django settings (base / development / production / preview)
├── apps/
│   ├── accounts/       # CustomUser, Partner, Role, OAuth, session management
│   ├── uploads/        # File upload batches, web upload + SFTP
│   ├── processing/     # File parsing, validation, pseudocoding
│   ├── participants/   # Participant records, IdentityMap (Fernet), re-identification
│   ├── tracing/        # Tracing queue, status updates, TracingLog
│   ├── assignments/    # Bulk assignment of traced participants to enumerators
│   ├── interviews/     # Interview status lifecycle
│   ├── audit/          # Immutable AuditLog, middleware, user timeline
│   ├── notifications/  # In-app notifications + email alerts
│   ├── invitations/    # Token-based invitation system
│   ├── sftp_ingestion/ # SFTPConfig, SFTPIngestionLog, SFTP watcher
│   ├── dashboards/     # Role-based dashboards
│   └── compliance/     # Compliance officer dashboard
├── templates/          # Django HTML templates (Bootstrap 5 + HTMX)
├── static/             # CSS, JS, logo
├── docker/             # Dockerfiles
├── nginx/              # nginx.conf
├── scripts/            # entrypoint.sh, generate_sftp_keys.sh, verify_encryption_key.sh
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

### Data separation model

Every participant has **two records** created atomically on approval:

| Record | Table | Contains | Readable by |
|---|---|---|---|
| Participant | `participants_participant` | Pseudocode + quasi-identifiers (county, gender, age) | All roles |
| IdentityMap | `participants_identitymap` | Direct identifiers — **Fernet-encrypted** | System Admin + Compliance Officer only |

Direct identifiers are **never** stored alongside quasi-identifiers. Even a full database dump reveals only pseudocodes and non-identifying fields.

---

## Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12 + Django 4.2 |
| Database | PostgreSQL 16 |
| Cache / Sessions | Redis 7 |
| Frontend | Bootstrap 5 + HTMX + Bootstrap Icons |
| Authentication | Microsoft Azure Entra ID (OAuth2 via MSAL) |
| Encryption | `cryptography` — Fernet (AES-128-CBC) |
| Email | Microsoft Graph API (app-only / client credentials) |
| SFTP | atmoz/sftp (OpenSSH) |
| Containerisation | Docker + Docker Compose |

---

## User Roles

| Role | What they can do |
|---|---|
| **System Admin** | Full access — upload approval, user management, assignments, audit trail, re-identification |
| **Implementing Partner** | Upload CSV/XLSX files, view own batch statuses and outcomes |
| **Supervisor** | View tracing queue, bulk-assign traced participants to enumerators, monitor team |
| **Enumerator** | View only their own assigned participants, record interview outcomes |
| **Tracer** | Update tracing status for participants in the tracing queue |
| **Compliance Officer** | Re-identification access with mandatory reason logging, compliance dashboard |

---

## Participant Pipeline

```
UPLOADED ──► TRACING ──► TRACED ──► ASSIGNED ──► INTERVIEWED ──► CLOSED
```

| Stage | Triggered by | Description |
|---|---|---|
| **Uploaded** | Admin approves batch | Participant pseudocoded, identifiers encrypted |
| **Tracing** | Tracer picks up record | Field officer actively locating the participant |
| **Traced** | Tracer marks as found | Participant located and confirmed |
| **Assigned** | Supervisor bulk-assigns | Assigned to a specific enumerator |
| **Interviewed** | Enumerator records outcome | Completed / Refused / Unreachable / Callback |
| **Closed** | Admin / Supervisor closes | Case finalised |

---

## Pseudocoding & Encryption

### Pseudocode format

```
PSN-YYYY-NNNNNN
```

Example: `PSN-2026-000042` — year of upload + zero-padded sequential number.

### What happens on approval

1. Admin reviews the validation summary and approves the batch
2. For every valid row, the system atomically:
   - Generates a unique pseudocode
   - Strips all direct identifiers from the row
   - Stores only quasi-identifiers (county, gender, age, sub-county, ward) in `Participant.data`
   - Encrypts direct identifiers (name, ID, phone, email, address) using Fernet and writes to `IdentityMap`

### Re-identification

Only **System Admin** and **Compliance Officer** roles can re-identify. Every access:
- Requires a written reason
- Is logged with user, timestamp, IP address, session ID, and fields accessed
- Displays decrypted data on screen for **60 seconds only**, then auto-hidden by JavaScript
- The decrypted values are never written to logs or stored anywhere

### Generate a new encryption key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> **Key backup, recovery, and rotation:** See [KEY_BACKUP_PROCEDURE.md](KEY_BACKUP_PROCEDURE.md)

---

## File Upload Format

**Accepted formats:** CSV, XLS, XLSX — maximum **100 MB**

| Column | Required | Stored as |
|---|---|---|
| `name` | **Yes** | Encrypted (IdentityMap) |
| `gender` | **Yes** | Plain (Participant.data) |
| `county` | **Yes** | Plain (Participant.data) |
| `national_id` | No | Encrypted |
| `passport` | No | Encrypted |
| `phone` | No | Encrypted |
| `alt_phone` | No | Encrypted |
| `email` | No | Encrypted |
| `address` | No | Encrypted |
| `age` | No | Plain |
| `birth_year` | No | Plain |
| `sub_county` | No | Plain |
| `ward` | No | Plain |

Column names are case-insensitive and spaces are normalised to underscores automatically.

---

## Environment Variables

Set in `/home/ipo/spdits/.env` on the production server.

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | **Yes** | Long random string — Django secret key |
| `DATABASE_URL` | **Yes** | PostgreSQL connection string |
| `REDIS_URL` | **Yes** | Redis connection string |
| `FIELD_ENCRYPTION_KEY` | **Yes** | Fernet key for encrypting direct identifiers |
| `ALLOWED_HOSTS` | **Yes** | Comma-separated list of allowed hostnames |
| `APP_URL` | **Yes** | Public URL e.g. `https://ea.data.iced-eval.org` |
| `AZURE_AD_CLIENT_ID` | Yes (OAuth) | Azure app registration client ID |
| `AZURE_AD_CLIENT_SECRET` | Yes (OAuth) | Azure app registration client secret |
| `AZURE_AD_TENANT_ID` | Yes (OAuth) | Azure AD tenant ID |
| `GRAPH_MAIL_SENDER` | Yes (email) | Sender email address for Graph API |
| `DEFAULT_FROM_EMAIL` | No | Display name + email for outgoing mail |
| `ADMIN_EMAIL` | No | Fallback admin notification email |
| `INVITATION_EXPIRY_MINUTES` | No | Invitation link lifetime (default: 30) |
| `MAX_UPLOAD_SIZE_MB` | No | Max upload size in MB (default: 100) |
| `DEBUG` | No | Set `False` in production |
| `DJANGO_SUPERUSER_EMAIL` | No | Initial superuser email |
| `DJANGO_SUPERUSER_PASSWORD` | No | Initial superuser password |

---

## Production Deployment

**Server:** `root@kenya1` — files at `/home/ipo/spdits/`

### Containers running in production

| Container | Purpose |
|---|---|
| `web` | Django application (Gunicorn) |
| `redis` | Cache + session store |

> PostgreSQL runs externally on port 5440. There is no Nginx container in the current production setup.

### Deploy after pushing to GitHub

```bash
ssh root@kenya1
cd /home/ipo/spdits
docker compose up --build -d
```

The Dockerfile pulls the latest code from GitHub automatically during `docker compose up --build`. You do **not** need to run `git pull` manually.

### Run migrations after deploy

```bash
docker compose exec web python manage.py migrate --noinput
```

### Collect static files (if static assets changed)

```bash
docker compose exec web python manage.py collectstatic --noinput
```

### Check logs

```bash
docker compose logs -f web
docker compose logs -f redis
```

### Media files

Uploaded files persist across container rebuilds via a bind mount:

```
Host path:       /home/ipo/spdits/media/
Container path:  /app/media/
Partner uploads: /home/ipo/spdits/media/uploads/<PARTNER_CODE>/filename.csv
```

The partner folder is named after the partner's `code` field and created automatically on first upload.

---

## Local Development

```bash
git clone https://github.com/icedsystems/SPDITS.git
cd SPDITS
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set DJANGO_SECRET_KEY, DATABASE_URL, FIELD_ENCRYPTION_KEY

export DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py migrate
python manage.py seed_demo_data --participants 100
python manage.py runserver
```

> In development, upload processing and email notifications run synchronously (no Celery worker required).

---

## SFTP Ingestion

Partners can upload files via SFTP instead of the web interface.

- Generate host keys once before first start: `bash scripts/generate_sftp_keys.sh`
- Default port: **2222**
- Authentication: SSH public key (preferred) or password
- New files are detected and processed through the same pipeline as web uploads

Configure SFTP connections under **Admin → SFTP Config** in the web interface.

---

## Email Configuration

Email is sent via **Microsoft Graph API** — no SMTP server required.

Configure under **Admin → Email Settings** in the web interface, or set in `.env`:

```
AZURE_AD_TENANT_ID=...
AZURE_AD_CLIENT_ID=...
AZURE_AD_CLIENT_SECRET=...
GRAPH_MAIL_SENDER=info@iced-eval.org
```

| Trigger | Recipient |
|---|---|
| Partner uploads a file | All System Admins |
| Admin approves upload | Uploading partner |
| Admin rejects upload | Uploading partner |
| New user invitation | Invited user |

---

## Azure AD / Microsoft OAuth

1. In Azure Portal → **App Registrations** → New Registration
2. Set redirect URI: `https://ea.data.iced-eval.org/accounts/oauth/callback/`
3. Under **Certificates & Secrets** → create a client secret
4. Copy **Client ID**, **Tenant ID**, **Client Secret** to `.env`
5. Users must have a pre-existing SPDITS account with a matching Microsoft email address

---

## Security

| Control | Implementation |
|---|---|
| Data pseudonymisation | Direct identifiers separated from quasi-identifiers at ingest |
| Encryption at rest | Fernet AES-128-CBC for all direct identifiers |
| Re-identification access control | System Admin + Compliance Officer only |
| Re-identification audit | Every access logged with user, reason, IP, session, timestamp |
| Re-identification time limit | Decrypted data auto-hidden after 60 seconds |
| Session timeout | 30 minutes idle |
| Immutable audit trail | `AuditLog.save()` overridden — records can never be updated |
| CSRF / XSS / Clickjacking | Django defaults + security middleware |
| HTTPS | Enforced in production |
| File validation | Type whitelist, 100 MB size limit, MD5 checksum recorded |
| Role-based access | All views permission-checked; enumerators scoped to own assignments only |

---

## Demo Accounts

After running `python manage.py seed_demo_data`, all accounts use password: **`spdits@2024!`**

| Email | Role |
|---|---|
| admin@iced.org | System Admin |
| partner1@iced.org | Implementing Partner |
| supervisor@iced.org | Supervisor |
| enumerator1@iced.org | Enumerator |
| tracer@iced.org | Tracer |
| compliance@iced.org | Compliance Officer |

---

## Related Documents

| Document | Purpose |
|---|---|
| [KEY_BACKUP_PROCEDURE.md](KEY_BACKUP_PROCEDURE.md) | How to back up, verify, recover, and rotate the `FIELD_ENCRYPTION_KEY` |
| [scripts/verify_encryption_key.sh](scripts/verify_encryption_key.sh) | Run on server to verify the encryption key is working correctly |
| [.env.example](.env.example) | Template for all required environment variables |

---

*ICED SPDITS — Developed by ICED Systems*
*For support contact the system developer.*
