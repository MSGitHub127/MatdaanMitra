"""
ECI Document Ingestion Pipeline

Downloads ECI PDFs, extracts text, chunks by semantic boundaries,
and prepares for embedding.
"""
import fitz  # PyMuPDF
from typing import List, Dict, Any
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class DocumentChunk:
    """Represents a chunk of ECI document text with metadata."""

    def __init__(
        self,
        chunk_id: str,
        text: str,
        source_url: str,
        form_type: str,
        section: str,
        applicable_to: List[str],
        language: str = "en",
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.source_url = source_url
        self.form_type = form_type
        self.section = section
        self.applicable_to = applicable_to
        self.language = language
        self.last_fetched = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_url": self.source_url,
            "form_type": self.form_type,
            "section": self.section,
            "applicable_to": self.applicable_to,
            "language": self.language,
            "last_fetched": self.last_fetched,
        }


class ECIIngestor:
    """Ingests ECI documents and prepares them for RAG."""

    ECI_FORMS = [
        {
            "id": "form6",
            "name": "Form 6",
            "url": "https://eci.gov.in/files/file/00000150.pdf",
            "description": "New voter registration",
            "applicable_to": ["first_time", "relocation"],
        },
        {
            "id": "form6a",
            "name": "Form 6A",
            "url": "https://eci.gov.in/files/file/00000151.pdf",
            "description": "NRI voter registration",
            "applicable_to": ["nri"],
        },
        {
            "id": "form8",
            "name": "Form 8",
            "url": "https://eci.gov.in/files/file/00000152.pdf",
            "description": "Address correction",
            "applicable_to": ["relocation", "correction"],
        },
    ]

    def __init__(self):
        self.chunks: List[DocumentChunk] = []

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyMuPDF."""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def chunk_by_semantic_boundaries(self, text: str, form_type: str) -> List[DocumentChunk]:
        """
        Chunk text by semantic boundaries (paragraphs, sections).
        Not by token count - preserves document structure.
        """
        chunks = []

        # Split by paragraphs
        paragraphs = re.split(r'\n\s*\n', text)

        current_section = "Introduction"
        chunk_counter = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Detect section headers
            section_match = re.match(r'^(Section|Part|Chapter)\s+\d+[:\s]*(.+)', para, re.IGNORECASE)
            if section_match:
                current_section = section_match.group(2).strip()

            # Create chunk
            chunk_id = f"{form_type}_{current_section.replace(' ', '_').lower()}_{chunk_counter}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                text=para,
                source_url="",  # Will be filled during ingestion
                form_type=form_type,
                section=current_section,
                applicable_to=[],  # Will be filled based on form metadata
            )
            chunks.append(chunk)
            chunk_counter += 1

        return chunks

    def ingest_form(self, form_metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Ingest a single ECI form."""
        logger.info(f"Ingesting {form_metadata['name']}")

        # In production, download PDF from URL
        # pdf_path = self.download_pdf(form_metadata['url'])
        # text = self.extract_text_from_pdf(pdf_path)

        # For now, use placeholder text
        text = f"""
        {form_metadata['name']} - {form_metadata['description']}

        Section 1: Eligibility
        Any Indian citizen who has attained the age of 18 years on the qualifying date
        (1st January of the year of revision of electoral roll) is eligible to be registered
        as a voter in the electoral roll.

        Section 2: Required Documents
        The following documents are required for registration:
        - Proof of age (Birth Certificate, Passport, School Certificate)
        - Proof of address (Aadhaar Card, Passport, Utility Bills)
        - Recent passport size photograph

        Section 3: Submission Process
        The application can be submitted online through NVSP portal or offline at the
        nearest ERO office or BLO.

        Section 4: Timeline
        The application is usually processed within 30 days of submission.
        """

        chunks = self.chunk_by_semantic_boundaries(text, form_metadata["id"])

        # Update chunk metadata
        for chunk in chunks:
            chunk.source_url = form_metadata["url"]
            chunk.applicable_to = form_metadata["applicable_to"]

        logger.info(f"Created {len(chunks)} chunks for {form_metadata['name']}")
        return chunks

    def ingest_all(self) -> List[DocumentChunk]:
        """Ingest all ECI forms."""
        all_chunks = []

        for form_metadata in self.ECI_FORMS:
            chunks = self.ingest_form(form_metadata)
            all_chunks.extend(chunks)

        self.chunks = all_chunks
        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks


if __name__ == "__main__":
    ingestor = ECIIngestor()
    chunks = ingestor.ingest_all()

    print(f"Created {len(chunks)} chunks")
    for chunk in chunks[:3]:
        print(f"\n{chunk.chunk_id}:")
        print(chunk.text[:100] + "...")
