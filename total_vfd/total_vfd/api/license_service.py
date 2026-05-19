"""Deprecated: local PBKDF2/HMAC licensing. Use license_site API via license_store.py.

Deprecated. ERPNext uses the license validation server API (see SETUP.md).
"""

import warnings

warnings.warn(
    "total_vfd.api.license_service is deprecated; use license_site validation API",
    DeprecationWarning,
    stacklevel=2,
)

import base64
import hashlib
import hmac
import secrets

from total_vfd.api.license_constants import (
    LICENSE_WORDS,
    LICENSE_WORD_SUFFIX,
    PBKDF2_ALGORITHM,
    PBKDF2_ITERATIONS,
)

_INTEGRITY_PEPPER = b"total_vfd_module_license_v1"
_HASH_PREFIX = f"${PBKDF2_ALGORITHM}$"


class LicenseServiceError(Exception):
    pass


class LicenseService:
    @staticmethod
    def normalize_word(word):
        if not word:
            return ""
        return word.strip()

    @classmethod
    def normalize_base_word(cls, word):
        w = cls.normalize_word(word)
        if w.endswith(LICENSE_WORD_SUFFIX):
            return w[: -len(LICENSE_WORD_SUFFIX)]
        return w

    @classmethod
    def verification_word(cls, base_word):
        base = cls.normalize_base_word(base_word)
        return f"{base}{LICENSE_WORD_SUFFIX}"

    @classmethod
    def validate_base_word_in_list(cls, base_word):
        base = cls.normalize_base_word(base_word)
        if base not in LICENSE_WORDS:
            raise LicenseServiceError("License Word is not valid.")
        return base

    @classmethod
    def validate_verification_input(cls, entered_word, stored_base_word):
        if not stored_base_word:
            raise LicenseServiceError("No License Word is assigned on this system.")
        expected = cls.verification_word(stored_base_word)
        entered = cls.normalize_word(entered_word)
        if entered != expected:
            raise LicenseServiceError(
                f'License Word must be "{expected}" '
                f'(your word "{stored_base_word}" plus "{LICENSE_WORD_SUFFIX}").'
            )
        return cls.normalize_base_word(stored_base_word)

    @classmethod
    def verify_license_key(cls, license_key, stored_hash):
        if not stored_hash:
            raise LicenseServiceError("License verification data is missing.")
        stored = str(stored_hash).strip()
        if stored.startswith(_HASH_PREFIX):
            return cls._verify_pbkdf2_license_key(license_key, stored)
        if stored.startswith("$2b$") or stored.startswith("$2a$"):
            return cls._verify_bcrypt_license_key(license_key, stored)
        raise LicenseServiceError("License Key format is invalid.")

    @classmethod
    def _verify_bcrypt_license_key(cls, license_key, stored_hash):
        try:
            import bcrypt
        except ImportError as exc:
            raise LicenseServiceError(
                "Legacy license hash requires bcrypt or a new key from your vendor."
            ) from exc
        try:
            return bcrypt.checkpw(
                str(license_key).strip().encode("utf-8"),
                stored_hash.encode("utf-8"),
            )
        except (ValueError, TypeError) as exc:
            raise LicenseServiceError("License Key format is invalid.") from exc

    @classmethod
    def _verify_pbkdf2_license_key(cls, license_key, stored_hash):
        try:
            _prefix, algorithm, iterations, salt_b64, digest_b64 = stored_hash.split("$", 4)
            if algorithm != PBKDF2_ALGORITHM:
                return False
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(digest_b64.encode("ascii"))
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                str(license_key).strip().encode("utf-8"),
                salt,
                int(iterations),
            )
            return secrets.compare_digest(actual, expected)
        except (ValueError, TypeError) as exc:
            raise LicenseServiceError("License Key format is invalid.") from exc

    @classmethod
    def encode_verification_token(cls, license_key_hash):
        return base64.urlsafe_b64encode(license_key_hash.encode("utf-8")).decode("ascii")

    @classmethod
    def decode_verification_token(cls, token):
        if not token or not str(token).strip():
            raise LicenseServiceError(
                "Vendor Activation Code is required. "
                "Paste it on Total VFD License → Activate License."
            )
        try:
            decoded = base64.urlsafe_b64decode(str(token).strip().encode("ascii"))
            return decoded.decode("utf-8")
        except (ValueError, TypeError) as exc:
            raise LicenseServiceError("Vendor Activation Code is invalid or corrupted.") from exc

    @classmethod
    def pick_random_word(cls):
        return secrets.choice(LICENSE_WORDS)

    @classmethod
    def build_integrity_seal(cls, site_id, license_word, expiry_date, status, license_key_hash):
        expiry_str = expiry_date.isoformat() if expiry_date else str(expiry_date or "")
        message = "|".join(
            [
                str(site_id or ""),
                cls.normalize_base_word(license_word),
                expiry_str,
                str(status or ""),
                str(license_key_hash or ""),
            ]
        )
        digest = hmac.new(
            _INTEGRITY_PEPPER + str(site_id or "").encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        )
        return digest.hexdigest()

    @classmethod
    def verify_integrity_seal(cls, record):
        if not record.get("integrity_seal"):
            return False
        expected = cls.build_integrity_seal(
            record.get("site_id"),
            record.get("license_word"),
            record.get("expiry_date"),
            record.get("status"),
            record.get("license_key_hash"),
        )
        return hmac.compare_digest(record.get("integrity_seal") or "", expected)
