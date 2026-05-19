#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
External license key generator (outside the Odoo module).

    python3 license_vendor/generate_license.py Mauzo
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

from license_crypto import LicenseVendorError, issue_license_for_customer_word  # noqa: E402


def format_vendor_email(bundle):
    return textwrap.dedent(f"""
        TOTAL VFD — LICENSE PACKAGE
        ===========================

        Customer word (they see in Odoo):  {bundle['license_word']}
        Activation phrase (automatic):       {bundle['license_verification_word']}

        --- Send customer these two items ---

        1) VENDOR ACTIVATION CODE (paste in Odoo → Activate License):
        {bundle['verification_token']}

        2) LICENSE KEY:
        {bundle['license_key']}

        Customer steps:
        • Settings → Total VFD → Activate License
        • Paste activation code + license key (activation phrase is automatic)

        Keys are NOT generated inside Odoo.
    """).strip()


def main():
    parser = argparse.ArgumentParser(description='Issue license for customer word')
    parser.add_argument('license_word', help='Word customer told you (e.g. Mauzo)')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    try:
        bundle = issue_license_for_customer_word(args.license_word)
    except LicenseVendorError as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(bundle, indent=2))
        return

    print(format_vendor_email(bundle))


if __name__ == '__main__':
    main()
