# ICED SPDITS — Encryption Documentation

**Classification: Internal Technical Reference**
**System: ICED SPDITS**
**Last reviewed: May 2026**

---

## Overview

ICED SPDITS uses **Fernet symmetric encryption** from Python's `cryptography` library to protect all direct participant identifiers stored in the database.

Fernet guarantees that encrypted data cannot be read or tampered with without the correct key. It is an authenticated encryption scheme — meaning it detects any modification to the ciphertext and rejects it.

---

## Encryption standard

| Property | Value |
|---|---|
| Library | Python `cryptography` (Fernet) |
| Cipher | AES-128-CBC |
| Authentication | HMAC-SHA256 |
| Key format | 32-byte URL-safe base64-encoded string (44 characters) |
| Key storage | `.env` file on the production server as `FIELD_ENCRYPTION_KEY` |

---

## What is encrypted

All **direct identifiers** — fields that can identify a participant on their own — are encrypted before being written to the database:

| Field | Example |
|---|---|
| Full name | Jane Mwangi |
| National ID | 12345678 |
| Passport number | AK1234567 |
| Phone number | 0712 345 678 |
| Alternative phone | 0723 456 789 |
| Email address | jane@example.com |
| Physical address | Plot 12, Kilifi |

These fields are stored in the `IdentityMap` table as encrypted binary blobs. Even with full database access, the values are unreadable without the key.

---

## What is NOT encrypted

**Quasi-identifiers** — fields that are not identifying on their own — are stored in plain text in the `Participant` table:

| Field | Why it is not encrypted |
|---|---|
| County | Needed for filtering, tracing assignment, and reporting |
| Sub-county | Same as above |
| Ward | Same as above |
| Gender | Same as above |
| Age / Birth year | Same as above |
| Pseudocode (PSN-YYYY-NNNNNN) | Required for all pipeline operations |

---

## How it works

### At upload and approval

When an admin approves an upload batch:

```
Raw CSV row
    │
    ▼
Direct identifiers extracted (name, ID, phone, etc.)
    │
    ├──► Fernet.encrypt(value) ──► stored in IdentityMap table (encrypted)
    │
    └──► Quasi-identifiers only ──► stored in Participant.data (plain JSON)
```

The pseudocode is generated at this point and links the two records together.

### At re-identification

When a System Admin or Compliance Officer re-identifies a participant:

```
Request arrives with written reason
    │
    ▼
Permission check (System Admin or Compliance Officer only)
    │
    ▼
Fernet.decrypt(encrypted_value) ──► plain text returned to view
    │
    ▼
Plain text rendered in HTML response (visible for 60 seconds)
    │
    ▼
JavaScript auto-hides the values after 60 seconds
    │
    ▼
Access logged: user, reason, IP address, session ID, timestamp, fields accessed
```

The decrypted values are **never written to the database, logs, or cache**. They exist only for the duration of the HTTP response.

---

## The encryption key

### Format

```
dGhpcyBpcyBhIGZha2Uga2V5IGZvciBkb2N1bWVudGF0aW9u=
```

*(example only — not a real key)*

- Exactly **44 characters** long
- Ends with `=`
- URL-safe base64 encoding of 32 random bytes

### Generating a new key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Where it lives in production

```
/home/ipo/spdits/.env
    └── FIELD_ENCRYPTION_KEY=<your-key-here>
```

The key is injected into the Docker container as an environment variable at startup. It never touches the database, logs, or any frontend code.

### Critical warning

> **If the key is lost, all participant identity data is permanently unreadable.**
> There is no recovery without the key. Back it up immediately and store it in at least two secure locations.

See [KEY_BACKUP_PROCEDURE.md](KEY_BACKUP_PROCEDURE.md) for step-by-step backup and recovery instructions.

---

## Security properties

| Property | Detail |
|---|---|
| Confidentiality | AES-128-CBC ensures encrypted data is unreadable without the key |
| Integrity | HMAC-SHA256 detects any tampering with the ciphertext |
| Key separation | Key is never stored in the database or source code |
| Access control | Decryption only happens server-side, never in the browser |
| Audit trail | Every re-identification is logged immutably |
| Time-limited display | Decrypted data auto-hides after 60 seconds on screen |

---

## Current limitations

| Limitation | Description |
|---|---|
| Single key | All records share one key. If the key is compromised, all records are at risk. |
| Key on same server as data | If the server is fully compromised, both the key and the database are exposed. |
| No key rotation script | Rotating the key requires re-encrypting all IdentityMap records. A migration script must be written before attempting rotation. |

---

## Recommended upgrade path

For stronger security, the key should be moved out of the server into **Azure Key Vault** — since ICED already uses Microsoft Azure for authentication. This means:

- The key never leaves Azure's hardware
- Even if the server is breached, the attacker cannot extract the key
- Every encrypt/decrypt operation is logged in Azure with timestamp and identity
- Key rotation becomes a one-click operation in the Azure portal
- Cost is negligible at SPDITS data volumes

See the system developer for implementation details.

---

## Related documents

| Document | Purpose |
|---|---|
| [KEY_BACKUP_PROCEDURE.md](KEY_BACKUP_PROCEDURE.md) | How to back up, verify, recover, and rotate the encryption key |
| [scripts/verify_encryption_key.sh](scripts/verify_encryption_key.sh) | Script to verify the key is working correctly on the server |
| [README.md](README.md) | Full system documentation |

---

*ICED SPDITS — Developed by ICED Systems*
*For support contact the system developer.*
