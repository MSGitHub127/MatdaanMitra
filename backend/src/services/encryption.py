"""
encryption.py — Versioned Fernet encryption for EPIC numbers

AUDIT FIX: Key versioning to prevent data corruption on key rotation.

  THE PROBLEM (before this fix):
    When FERNET_KEY was rotated (e.g., for security policy reasons or after a
    suspected credential leak), ALL existing Firestore documents encrypted with
    the old key became permanently unreadable. Calling decrypt() on old tokens
    with a new key raises cryptography.fernet.InvalidToken — a silent data loss.

  THE SOLUTION — Version-prefixed tokens:
    Every encrypted token is stored as:
        v{N}:{base64_fernet_token}
    e.g.:
        v1:gAAAAABk...   ← encrypted with FERNET_KEY_V1
        v2:gAAAAABl...   ← encrypted with FERNET_KEY_V2 (new key)

    On decrypt, the prefix is parsed to select the correct key version.
    New encryptions always use the CURRENT (latest) version.

    This means:
      - Old documents remain decryptable with their original key.
      - New documents are encrypted with the rotated key.
      - Rotation is zero-downtime and zero-data-loss.
      - After all old documents have been re-encrypted (background migration),
        old key versions can be removed from config.

  CONFIGURATION in backend/.env:
    # Current (active) key — used for all new encryptions
    FERNET_KEY=<base64-url-safe-32-byte-key>

    # Previous key(s) — kept for decrypting old tokens only
    # Comma-separated list of "version:key" pairs
    FERNET_KEY_VERSIONS=v1:<old-key-1>,v2:<old-key-2>

    To generate a new key:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

  MIGRATION STRATEGY:
    To re-encrypt all existing Firestore documents to the current key version,
    run the migration script provided at the bottom of this file as a one-off
    Cloud Run job BEFORE removing old key versions from config.

  TOKEN FORMAT:
    PREFIX_SEPARATOR = ":"
    Version string:  "v1", "v2", ... "v99" (no upper limit)
    Fernet token:    standard base64url Fernet output (always starts with "gAAAAA")
    Combined:        "v1:gAAAAABk..."

    Tokens WITHOUT a version prefix (legacy — written before this fix) are
    treated as version "v0" and decrypted with FERNET_KEY (the current key),
    since those tokens were written with whatever key was set at the time.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from ..config.settings import settings

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX_RE = re.compile(r'^(v\d+):(.+)$', re.DOTALL)
_CURRENT_VERSION = "v1"  # Bump this when rotating to a new key


class VersionedEncryptionService:
    """
    Fernet encryption with version-prefixed tokens.

    Supports simultaneous decryption of tokens from multiple key versions,
    enabling zero-downtime, zero-data-loss key rotation.
    """

    def __init__(self) -> None:
        # Lazy init — keys are resolved on first use so startup never crashes
        # if environment variables are temporarily missing (e.g., in CI).
        self._keys: Optional[dict[str, Fernet]] = None
        self._current_version: Optional[str] = None

    def _resolve_keys(self) -> dict[str, Fernet]:
        """
        Builds the version→Fernet map from environment config.

        Map structure:
            {
              "v1": Fernet(<FERNET_KEY>),          # current key
              "v0": Fernet(<old-key>),              # optional legacy keys
              ...
            }

        Raises ValueError if FERNET_KEY is not set.
        """
        current_key = settings.fernet_key
        if not current_key:
            raise ValueError(
                "FERNET_KEY is not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )

        key_map: dict[str, Fernet] = {
            _CURRENT_VERSION: Fernet(current_key.encode()),
        }

        # Load additional historical key versions from FERNET_KEY_VERSIONS.
        # Format: "v0:<key0>,v2:<key2>" (comma-separated "version:key" pairs)
        legacy_versions_raw: str = getattr(settings, "fernet_key_versions", "") or ""
        if legacy_versions_raw.strip():
            for entry in legacy_versions_raw.split(","):
                entry = entry.strip()
                if not entry:
                    continue
                parts = entry.split(":", 1)
                if len(parts) != 2:
                    logger.warning(
                        "Skipping malformed FERNET_KEY_VERSIONS entry: %r", entry
                    )
                    continue
                version, key_value = parts[0].strip(), parts[1].strip()
                if version in key_map:
                    logger.warning(
                        "Duplicate key version %r in FERNET_KEY_VERSIONS — skipping", version
                    )
                    continue
                try:
                    key_map[version] = Fernet(key_value.encode())
                    logger.info("Loaded historical Fernet key version: %s", version)
                except Exception as exc:
                    logger.error(
                        "Invalid Fernet key for version %r: %s", version, exc
                    )

        logger.info(
            "VersionedEncryptionService ready — current=%s, all_versions=%s",
            _CURRENT_VERSION,
            sorted(key_map.keys()),
        )
        return key_map

    @property
    def _key_map(self) -> dict[str, Fernet]:
        if self._keys is None:
            self._keys = self._resolve_keys()
        return self._keys

    # ── Public API ────────────────────────────────────────────────────────────

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext with the current key version.

        Returns a version-prefixed token, e.g.:
            "v1:gAAAAABk..."

        Always uses _CURRENT_VERSION — call this for all new write operations.
        """
        try:
            fernet = self._key_map[_CURRENT_VERSION]
            raw_token = fernet.encrypt(plaintext.encode()).decode()
            return f"{_CURRENT_VERSION}:{raw_token}"
        except Exception as exc:
            logger.error("Encryption error: %s", exc)
            raise

    def decrypt(self, token: str) -> Optional[str]:
        """
        Decrypt a version-prefixed token.

        Handles three cases:
          1. Versioned token "v1:gAAAAA..."  → uses key for "v1"
          2. Legacy token "gAAAAA..."         → tries current key first,
                                                then all other versions
          3. Unknown version                  → logs warning, returns None

        Returns None on decryption failure (instead of raising) so that
        a single corrupted document doesn't crash the entire pipeline.
        """
        try:
            match = _PREFIX_RE.match(token)

            if match:
                version, raw_token = match.group(1), match.group(2)
                fernet = self._key_map.get(version)
                if fernet is None:
                    logger.warning(
                        "Unknown token version '%s' — no key configured. "
                        "Add it to FERNET_KEY_VERSIONS.",
                        version,
                    )
                    return None
                return fernet.decrypt(raw_token.encode()).decode()

            else:
                # Legacy unversioned token (written before this fix was deployed).
                # Try all known keys in version order — most likely to succeed with
                # the current key if the token was written recently.
                logger.debug("Decrypting legacy unversioned token — trying all key versions")
                raw_bytes = token.encode()
                for version in sorted(self._key_map.keys(), reverse=True):
                    try:
                        result = self._key_map[version].decrypt(raw_bytes).decode()
                        logger.info(
                            "Legacy token decrypted successfully with key version '%s'",
                            version,
                        )
                        return result
                    except InvalidToken:
                        continue
                logger.error(
                    "Legacy token could not be decrypted with any configured key version"
                )
                return None

        except Exception as exc:
            logger.error("Decryption error: %s", exc)
            return None

    def current_version(self) -> str:
        """Returns the version string used for new encryptions."""
        return _CURRENT_VERSION

    def known_versions(self) -> list[str]:
        """Returns all configured key versions (for migration tooling)."""
        return sorted(self._key_map.keys())


# Singleton — safe to import without FERNET_KEY set (init is lazy)
encryption_service = VersionedEncryptionService()


# =============================================================================
# MIGRATION SCRIPT
# Run this ONCE as a Cloud Run Job after deploying the new key version.
# It re-encrypts all existing Firestore EPIC tokens to the current key version
# so that old key versions can eventually be retired.
#
# Usage:
#   python -m backend.src.services.encryption --migrate --dry-run
#   python -m backend.src.services.encryption --migrate
# =============================================================================

async def _migrate_firestore_epics(dry_run: bool = True) -> None:  # pragma: no cover
    """
    Re-encrypt all Firestore voter profiles to the current key version.

    Set dry_run=True to audit without writing. Always run dry-run first.
    """
    import argparse
    import firebase_admin
    from firebase_admin import firestore as fs

    logger.info("Starting EPIC re-encryption migration — dry_run=%s", dry_run)

    if not firebase_admin._apps:
        from firebase_admin import credentials
        cred = credentials.Certificate(settings.firebase_service_account_path)
        firebase_admin.initialize_app(cred)

    db = fs.client()
    profiles_ref = db.collection("voter_profiles")
    docs = profiles_ref.stream()

    migrated = 0
    skipped = 0
    errors = 0

    for doc in docs:
        data = doc.to_dict()
        encrypted_epic = data.get("epic_number")

        if not encrypted_epic:
            skipped += 1
            continue

        # Already on the current version?
        if encrypted_epic.startswith(f"{_CURRENT_VERSION}:"):
            skipped += 1
            continue

        # Decrypt with the old key, re-encrypt with the new key
        plaintext = encryption_service.decrypt(encrypted_epic)
        if plaintext is None:
            logger.error("doc=%s — failed to decrypt, SKIPPING", doc.id)
            errors += 1
            continue

        new_token = encryption_service.encrypt(plaintext)

        if dry_run:
            logger.info(
                "[DRY RUN] doc=%s — would re-encrypt %s → %s",
                doc.id,
                encrypted_epic[:20] + "...",
                new_token[:20] + "...",
            )
        else:
            doc.reference.update({"epic_number": new_token})
            logger.info("doc=%s — re-encrypted to %s", doc.id, _CURRENT_VERSION)

        migrated += 1

    logger.info(
        "Migration complete — migrated=%d skipped=%d errors=%d dry_run=%s",
        migrated, skipped, errors, dry_run,
    )


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Migrate Fernet key versions in Firestore")
    parser.add_argument("--migrate", action="store_true", required=True)
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    asyncio.run(_migrate_firestore_epics(dry_run=args.dry_run))