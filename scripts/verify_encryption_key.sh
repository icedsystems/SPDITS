#!/bin/bash
# =============================================================================
# ICED SPDITS — Encryption Key Verification Script
# Run this BEFORE and AFTER any backup, migration, or key rotation.
# =============================================================================

set -e

echo "========================================"
echo " ICED SPDITS — Encryption Key Verifier"
echo "========================================"
echo ""

# Check .env exists
ENV_FILE="$(dirname "$0")/../.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env file not found at $ENV_FILE"
  echo "Run this script from inside /home/ipo/spdits/ or adjust the path."
  exit 1
fi

# Check key is set
KEY=$(grep "^FIELD_ENCRYPTION_KEY=" "$ENV_FILE" | cut -d= -f2)
if [ -z "$KEY" ]; then
  echo "ERROR: FIELD_ENCRYPTION_KEY is not set in .env"
  exit 1
fi

KEY_LENGTH=${#KEY}
echo "Key found in .env"
echo "Key length: $KEY_LENGTH characters (expected: 44)"

if [ "$KEY_LENGTH" -ne 44 ]; then
  echo "WARNING: Key length is not 44 characters — may be invalid."
fi

# Print fingerprint (SHA-256 of key — safe to log, does not reveal key)
FINGERPRINT=$(echo -n "$KEY" | sha256sum | awk '{print $1}')
echo "Key fingerprint (SHA-256): $FINGERPRINT"
echo ""
echo "Record this fingerprint to verify backup copies match."
echo ""

# Test encryption/decryption via Django shell inside Docker
echo "Testing encryption/decryption inside container..."
docker compose exec web python manage.py shell -c "
from apps.participants.models import get_fernet, IdentityMap
f = get_fernet()
test_value = b'iced-spdits-key-verification-test'
encrypted = f.encrypt(test_value)
decrypted = f.decrypt(encrypted)
if decrypted == test_value:
    print('ENCRYPTION TEST: PASSED')
else:
    print('ENCRYPTION TEST: FAILED')
    exit(1)

count = IdentityMap.objects.count()
print(f'IdentityMap records in database: {count}')

if count > 0:
    sample = IdentityMap.objects.first()
    try:
        ids = sample.get_identifiers()
        readable = sum(1 for v in ids.values() if v)
        print(f'Sample record decryption: OK ({readable} fields readable)')
    except Exception as e:
        print(f'Sample record decryption: FAILED — {e}')
        print('WARNING: Existing records may not be readable with this key.')
        exit(1)
else:
    print('No IdentityMap records yet (new installation).')

print('')
print('KEY VERIFICATION: SUCCESS')
"

echo ""
echo "========================================"
echo " Verification complete."
echo " Fingerprint: $FINGERPRINT"
echo " Back this up alongside the key itself."
echo "========================================"
