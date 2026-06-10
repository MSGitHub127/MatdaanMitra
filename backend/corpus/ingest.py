"""
ingest.py — ECI Document Ingestion Pipeline

Downloads official ECI forms and guidelines, extracts text using PyMuPDF,
chunks by semantic boundaries, and stores metadata in Firestore.

Run from backend/ directory:
    python -m corpus.ingest

Requires:
    backend/.env configured with FIREBASE_SERVICE_ACCOUNT_PATH
    pip install PyMuPDF httpx firebase-admin python-dotenv
"""

import hashlib
import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz          # PyMuPDF
import httpx
from dotenv import load_dotenv

# ── Bootstrap path so we can import src.config ───────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── ECI document catalogue ────────────────────────────────────────────────────
# URLs sourced from eci.gov.in — verified April 2026.
# Each entry includes rich curated text as a fallback when the PDF
# cannot be downloaded (common for ECI's CDN).

ECI_DOCUMENTS: list[dict[str, Any]] = [
    # ── Registration forms ────────────────────────────────────────────────────
    {
        "id": "form6",
        "name": "Form 6",
        "url": "https://eci.gov.in/files/file/00000150.pdf",
        "description": "Application for inclusion of name in electoral roll",
        "applicable_to": ["new", "relocation"],
        "curated_sections": [
            {
                "section": "Eligibility",
                "text": (
                    "Form 6 — New Voter Registration. Any Indian citizen who has "
                    "attained the age of 18 years on the qualifying date, which is "
                    "1st January of the year of revision of the electoral roll, is "
                    "eligible to register. The applicant must be ordinarily resident "
                    "at the address mentioned in the application. NRIs must use Form 6A."
                ),
            },
            {
                "section": "Required Documents",
                "text": (
                    "Form 6 Required Documents: "
                    "Proof of Age — Aadhaar card, Birth Certificate, School Leaving "
                    "Certificate, PAN card, Passport, or Driving License. "
                    "Proof of Address — Aadhaar card, Passport, Bank or Post Office "
                    "Passbook, Utility bill (not older than 1 year), Rent agreement, "
                    "or any government-issued document showing address. "
                    "One recent passport-size photograph. "
                    "If applying offline, self-attested photocopies of all documents."
                ),
            },
            {
                "section": "Submission Process",
                "text": (
                    "Form 6 Submission: Applications can be submitted (1) Online at "
                    "voters.eci.gov.in or the Voter Helpline app, (2) At the local "
                    "ERO (Electoral Registration Officer) office, or (3) Via the BLO "
                    "(Booth Level Officer) who visits residences for verification. "
                    "Online applications require Aadhaar-linked mobile for OTP. "
                    "Processing time is typically 30 days. Status can be tracked on "
                    "the NVSP portal using the reference number."
                ),
            },
            {
                "section": "Deadlines",
                "text": (
                    "Form 6 Deadlines: For the annual revision cycle, the draft "
                    "electoral roll is published on 1st October each year. "
                    "Applications for inclusion must be submitted before the "
                    "final publication date on 5th January. "
                    "For elections, the last date for new registration is typically "
                    "30 days before the election notification date. "
                    "No registrations are accepted during the Model Code of Conduct period."
                ),
            },
        ],
    },
    {
        "id": "form6a",
        "name": "Form 6A",
        "url": "https://eci.gov.in/files/file/00000151.pdf",
        "description": "Application for inclusion of name of overseas elector",
        "applicable_to": ["nri"],
        "curated_sections": [
            {
                "section": "NRI Eligibility",
                "text": (
                    "Form 6A — NRI Voter Registration. Indian citizens residing abroad "
                    "who hold a valid Indian passport and have not acquired citizenship "
                    "of another country are eligible to register as overseas electors. "
                    "They can only register at their last address in India as mentioned "
                    "in their passport. NRIs can vote only in person at their "
                    "constituency — postal ballot is not available for overseas voters."
                ),
            },
            {
                "section": "Required Documents",
                "text": (
                    "Form 6A Required Documents: "
                    "Copy of valid Indian Passport. "
                    "Copy of relevant pages showing date of birth and last address in India. "
                    "One recent passport-size photograph. "
                    "A declaration that the applicant has not acquired citizenship of "
                    "any foreign country and is still an Indian citizen."
                ),
            },
        ],
    },
    {
        "id": "form7",
        "name": "Form 7",
        "url": "https://eci.gov.in/files/file/00000153.pdf",
        "description": "Application for deletion of name from electoral roll",
        "applicable_to": ["relocation", "correction"],
        "curated_sections": [
            {
                "section": "When to use Form 7",
                "text": (
                    "Form 7 — Objection to inclusion or deletion of name. "
                    "Use Form 7 to: (1) Delete a deceased person's name from the roll, "
                    "(2) Delete a name that appears twice (duplicate entry), "
                    "(3) Object to inclusion of a non-resident or ineligible person. "
                    "If you have moved to a different constituency, you must file Form 7 "
                    "at your old constituency to delete the old entry, and Form 6 at "
                    "the new constituency for fresh registration."
                ),
            },
            {
                "section": "Deletion Process",
                "text": (
                    "Form 7 Process: Provide the EPIC number and full name of the entry "
                    "to be deleted, along with the reason for deletion. "
                    "For deletion of deceased persons, a death certificate or statement "
                    "from a close relative is required. "
                    "The ERO will verify the claim before removing the entry. "
                    "Frivolous objections may result in penalties."
                ),
            },
        ],
    },
    {
        "id": "form8",
        "name": "Form 8",
        "url": "https://eci.gov.in/files/file/00000154.pdf",
        "description": "Application for correction of entries in electoral roll",
        "applicable_to": ["correction"],
        "curated_sections": [
            {
                "section": "Corrections Covered",
                "text": (
                    "Form 8 — Correction of Entries. Use Form 8 to correct: "
                    "Name spelling, date of birth, gender, relationship name (father/husband), "
                    "photograph update, or address within the same constituency. "
                    "For address change to a different constituency, use Form 6 (new) "
                    "and Form 7 (deletion at old address)."
                ),
            },
            {
                "section": "Required Documents",
                "text": (
                    "Form 8 Required Documents: "
                    "Proof supporting the correction — e.g., Aadhaar for name correction, "
                    "birth certificate for date of birth correction. "
                    "Original EPIC card for photograph correction. "
                    "The correction must be accompanied by documentary proof. "
                    "Unsubstantiated corrections will be rejected."
                ),
            },
        ],
    },
    {
        "id": "form8a",
        "name": "Form 8A",
        "url": "https://eci.gov.in/files/file/00000155.pdf",
        "description": "Application for transposition of entry in electoral roll",
        "applicable_to": ["relocation"],
        "curated_sections": [
            {
                "section": "Transposition Within Constituency",
                "text": (
                    "Form 8A — Transposition (address change within same constituency). "
                    "If you have moved to a new address but remain within the SAME "
                    "assembly constituency, use Form 8A to update your address. "
                    "You do NOT need to re-register with Form 6. "
                    "If you have moved to a DIFFERENT constituency, file Form 6 "
                    "at the new constituency and Form 7 at the old constituency."
                ),
            },
        ],
    },
    # ── Procedures and guidelines ─────────────────────────────────────────────
    {
        "id": "eci_guidelines",
        "name": "ECI Registration Guidelines",
        "url": "https://eci.gov.in/voter-registration/",
        "description": "General voter registration procedures and timelines",
        "applicable_to": ["new", "relocation", "correction", "nri"],
        "curated_sections": [
            {
                "section": "BLO Verification",
                "text": (
                    "Booth Level Officer (BLO) Verification: After submitting Form 6, "
                    "the BLO (Booth Level Officer) will visit your address to verify "
                    "that you actually reside there. This typically happens within "
                    "15–30 days of submission. Keep your original documents ready. "
                    "If you are not available at the address, the BLO may mark the "
                    "application for re-verification. Absence without notification "
                    "can lead to rejection."
                ),
            },
            {
                "section": "EPIC Card Delivery",
                "text": (
                    "Voter ID (EPIC) Card: After successful registration, the EPIC "
                    "(Electors Photo Identity Card) is issued. "
                    "For new registrations, the card is typically ready within 45–60 days. "
                    "You can track status at voters.eci.gov.in. "
                    "The card can be downloaded digitally as an e-EPIC (PDF) from the "
                    "same portal using your registered mobile number. "
                    "The e-EPIC is legally valid for voting."
                ),
            },
            {
                "section": "Grievance Filing",
                "text": (
                    "Voter Grievance Filing: If your name is missing, contains errors, "
                    "or you have any registration issue, you can: "
                    "(1) File online at nvsp.in under Grievances section, "
                    "(2) Call National Voter Helpline 1950 (toll-free, Mon–Sat 8AM–8PM), "
                    "(3) Email your state CEO office (listed at eci.gov.in/ceo), "
                    "(4) Submit written complaint to your ERO office with supporting documents. "
                    "Grievances are typically resolved within 30 days."
                ),
            },
            {
                "section": "Qualifying Date",
                "text": (
                    "Qualifying Date for Voter Registration: The qualifying date is "
                    "1st January of the year of revision of the electoral roll. "
                    "You must be 18 years old on 1st January to be eligible for that year's roll. "
                    "However, for by-elections and general elections, the qualifying date "
                    "may be the date of notification. Always check the specific election "
                    "schedule on the ECI website or call 1950 for confirmation."
                ),
            },
            {
                "section": "Online Registration Steps",
                "text": (
                    "Online Voter Registration Steps: "
                    "1. Visit voters.eci.gov.in or download the Voter Helpline app. "
                    "2. Click 'New Registration' for first-time voters. "
                    "3. Enter Aadhaar number (optional but recommended for faster processing). "
                    "4. Fill personal details — name exactly as on Aadhaar. "
                    "5. Upload a clear passport-size photo (JPG, max 2MB). "
                    "6. Upload proof of age and address (PDF or JPG, max 2MB each). "
                    "7. Submit and note the Application Reference Number. "
                    "8. Track status at nvsp.in using the reference number."
                ),
            },
            {
                "section": "Dual Enrollment",
                "text": (
                    "Dual Enrollment (multiple registrations): Being registered in "
                    "more than one constituency simultaneously is illegal under the "
                    "Representation of the People Act. If you have moved, you MUST "
                    "file Form 7 to delete your name from the old roll before or "
                    "simultaneously with filing Form 6 at the new address. "
                    "The ECI runs de-duplication drives to identify duplicate entries."
                ),
            },
        ],
    },
]


# ── PDF extraction ────────────────────────────────────────────────────────────

def _download_pdf(url: str, timeout: int = 20) -> bytes | None:
    """Download a PDF from the given URL. Returns bytes or None on failure."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "MatdaanMitra/1.0"})
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/pdf"):
                return resp.content
            logger.warning("PDF download failed (%s): %s", resp.status_code, url)
    except Exception as exc:
        logger.warning("PDF download error for %s: %s", url, exc)
    return None


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using PyMuPDF."""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            return "\n\n".join(page.get_text("text") for page in doc).strip()
    except Exception as exc:
        logger.warning("PDF text extraction error: %s", exc)
        return ""


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """
    Split extracted PDF text into (section_name, section_text) pairs.
    Uses heading-like patterns common in ECI documents.
    """
    section_pattern = re.compile(
        r'^(?:Section|Part|Clause|Article|Rule|Schedule|Appendix|Instructions?|Note|Schedule)\s*[\d\.\-]+[:\s]+(.+)',
        re.IGNORECASE | re.MULTILINE,
    )

    lines = text.split("\n")
    sections: list[tuple[str, str]] = []
    current_section = "General"
    current_lines: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = section_pattern.match(line)
        if match and len(line) < 120:
            if current_lines:
                body = " ".join(current_lines).strip()
                if len(body) > 80:
                    sections.append((current_section, body))
            current_section = match.group(1)[:80]
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = " ".join(current_lines).strip()
        if len(body) > 80:
            sections.append((current_section, body))

    return sections or [("General", text[:2000])]


# ── Chunk builder ─────────────────────────────────────────────────────────────

class DocumentChunk:
    def __init__(
        self,
        chunk_id: str,
        text: str,
        source_url: str,
        form_type: str,
        section: str,
        applicable_to: list[str],
    ):
        self.chunk_id   = chunk_id
        self.text       = text
        self.source_url = source_url
        self.form_type  = form_type
        self.section    = section
        self.applicable_to = applicable_to
        self.ingested_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id":      self.chunk_id,
            "text":          self.text,
            "source_url":    self.source_url,
            "form_type":     self.form_type,
            "section":       self.section,
            "applicable_to": self.applicable_to,
            "ingested_at":   self.ingested_at,
        }


def _make_chunk_id(form_id: str, section: str, index: int) -> str:
    slug = re.sub(r'\W+', '_', section.lower())[:40]
    return f"{form_id}_{slug}_{index:03d}"


# ── Main ingestor ─────────────────────────────────────────────────────────────

class ECIIngestor:

    def __init__(self):
        self.chunks: list[DocumentChunk] = []

    def ingest_document(self, doc_meta: dict[str, Any]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        form_id = doc_meta["id"]
        form_name = doc_meta["name"]
        url = doc_meta["url"]
        applicable_to = doc_meta["applicable_to"]

        logger.info("Processing %s …", form_name)

        # ── Try real PDF download first ───────────────────────────────────────
        pdf_bytes = _download_pdf(url)
        if pdf_bytes:
            text = _extract_text_from_pdf(pdf_bytes)
            if len(text) > 200:
                sections = _split_into_sections(text)
                for i, (section, body) in enumerate(sections):
                    # Deduplicate identical text
                    chunk_id = _make_chunk_id(form_id, section, i)
                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        text=f"**{form_name} — {section}**: {body}",
                        source_url=url,
                        form_type=form_name,
                        section=section,
                        applicable_to=applicable_to,
                    ))
                logger.info("  → %d chunks from PDF", len(chunks))
                return chunks

        # ── Fallback: use curated sections ────────────────────────────────────
        logger.info("  → PDF unavailable, using curated content")
        for i, s in enumerate(doc_meta.get("curated_sections", [])):
            chunk_id = _make_chunk_id(form_id, s["section"], i)
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                text=s["text"],
                source_url=url,
                form_type=form_name,
                section=s["section"],
                applicable_to=applicable_to,
            ))

        logger.info("  → %d curated chunks", len(chunks))
        return chunks

    def ingest_all(self) -> list[DocumentChunk]:
        all_chunks: list[DocumentChunk] = []
        for doc_meta in ECI_DOCUMENTS:
            all_chunks.extend(self.ingest_document(doc_meta))

        # Deduplicate by chunk_id
        seen: set[str] = set()
        unique: list[DocumentChunk] = []
        for c in all_chunks:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                unique.append(c)

        self.chunks = unique
        logger.info("Total unique chunks: %d", len(self.chunks))
        return self.chunks

    def save_to_firestore(self, chunks: list[DocumentChunk]) -> int:
        """
        Persist chunk metadata to Firestore collection `corpus_chunks`.
        This is what rag_retrieval.py reads for text + metadata lookups.
        """
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore as admin_fs

            sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-admin.json")
            if not firebase_admin._apps:
                cred = credentials.Certificate(sa_path)
                firebase_admin.initialize_app(cred)

            db = admin_fs.client()
            batch = db.batch()
            count = 0

            for i, chunk in enumerate(chunks):
                ref = db.collection("corpus_chunks").document(chunk.chunk_id)
                batch.set(ref, chunk.to_dict())
                count += 1

                # Firestore batches are limited to 500 ops
                if count % 499 == 0:
                    batch.commit()
                    batch = db.batch()
                    logger.info("  Committed batch at chunk %d", count)

            batch.commit()
            logger.info("Saved %d chunks to Firestore corpus_chunks", count)
            return count

        except Exception as exc:
            logger.error("Firestore save failed: %s", exc)
            raise

    def save_to_jsonl(self, chunks: list[DocumentChunk], output_path: str) -> None:
        """
        Save chunks (without embeddings) to a JSONL file for inspection
        and for use by embed.py.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
        logger.info("Saved chunk JSONL to %s", output_path)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ingestor = ECIIngestor()

    logger.info("Starting ECI corpus ingestion…")
    chunks = ingestor.ingest_all()

    # Save JSONL for embed.py
    jsonl_path = Path(__file__).parent / "data" / "chunks.jsonl"
    ingestor.save_to_jsonl(chunks, str(jsonl_path))

    # Save metadata to Firestore
    saved = ingestor.save_to_firestore(chunks)

    logger.info("Ingestion complete. %d chunks ready for embedding.", saved)
    logger.info("Next step: run  python -m corpus.embed")