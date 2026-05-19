# -*- coding: utf-8 -*-
"""
External license key generation (NOT part of the Odoo module).

Run from project root:
    python3 license_vendor/generate_license.py Mauzo
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import string

PBKDF2_ALGORITHM = 'pbkdf2-sha256'
PBKDF2_ITERATIONS = 100000
HASH_PREFIX = f'${PBKDF2_ALGORITHM}$'
WORD_SUFFIX = 'Tanzania'

LICENSE_WORDS = [
    'Biashara', 'Faida', 'Hasara', 'Mauzo', 'Manunuzi', 'Mteja', 'Wateja', 'Kampuni',
    'Uwekezaji', 'Mtaji', 'Mapato', 'Matumizi', 'Duka', 'Huduma', 'Bidhaa', 'Bei',
    'Punguzo', 'Stoo', 'Hesabu', 'Risiti', 'Ankara', 'Malipo', 'Mkopo', 'Deni', 'Benki',
    'Fedha', 'Ushuru', 'Kodi', 'Mkataba', 'Soko', 'Masoko', 'Uuzaji', 'Usafirishaji',
    'Ugavi', 'Wakala', 'Usimamizi', 'Uongozi', 'Mfanyakazi', 'Mwajiri', 'Mishahara',
    'Uzalishaji', 'Teknolojia', 'Mfumo', 'Mawasiliano', 'Uaminifu', 'Ubora', 'Ushindani',
    'Mafanikio', 'Leseni', 'Taarifa',
]


class LicenseVendorError(Exception):
    pass


def normalize_base_word(word):
    if not word:
        return ''
    w = word.strip()
    if w.endswith(WORD_SUFFIX):
        return w[:-len(WORD_SUFFIX)]
    return w


def verification_word(base_word):
    """Mauzo → MauzoTanzania"""
    return f'{normalize_base_word(base_word)}{WORD_SUFFIX}'


def validate_base_word(base_word):
    base = normalize_base_word(base_word)
    if base not in LICENSE_WORDS:
        raise LicenseVendorError(
            f'"{base}" is not a valid License Word. Customer must give you their word from Odoo Settings.'
        )
    return base


def generate_license_key(length=24):
    alphabet = string.ascii_uppercase + string.digits
    raw = ''.join(secrets.choice(alphabet) for _ in range(length))
    return '-'.join(raw[i:i + 6] for i in range(0, len(raw), 6))


def hash_license_key(license_key):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256',
        str(license_key).strip().encode('utf-8'),
        salt,
        PBKDF2_ITERATIONS,
    )
    salt_b64 = base64.b64encode(salt).decode('ascii')
    digest_b64 = base64.b64encode(digest).decode('ascii')
    return f'{HASH_PREFIX}{PBKDF2_ITERATIONS}${salt_b64}${digest_b64}'


def encode_verification_token(license_key_hash):
    return base64.urlsafe_b64encode(license_key_hash.encode('utf-8')).decode('ascii')


def issue_license_for_customer_word(customer_base_word):
    """
    Vendor: customer said their word is e.g. Mauzo (from their Odoo screen).
    """
    base = validate_base_word(customer_base_word)
    verify_word = verification_word(base)
    key = generate_license_key()
    key_hash = hash_license_key(key)
    token = encode_verification_token(key_hash)
    return {
        'license_word': base,
        'license_verification_word': verify_word,
        'license_key': key,
        'license_key_hash': key_hash,
        'verification_token': token,
    }
