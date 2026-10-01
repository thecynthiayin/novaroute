import secrets
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pdfplumber
from fastapi import HTTPException

from app.core.config import settings
from app.schemas import Extraction
from app.services.openrouter import redact_contacts, structured
from app.services.skills import infer, normalize


def extract_pdf(data: bytes):
    import logging

    logger = logging.getLogger(__name__)
    config = settings()

    if len(data) > config.upload_max_bytes:
        raise HTTPException(413, "PDF exceeds the upload size limit (default 5 MB)")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(422, "Upload a valid PDF file")

    try:
        logger.info(f"Opening PDF with pdfplumber, size: {len(data)} bytes")
        with pdfplumber.open(BytesIO(data)) as pdf:
            logger.info(f"PDF has {len(pdf.pages)} pages")
            if len(pdf.pages) > config.upload_max_pages:
                raise HTTPException(422, f"PDF must have at most {config.upload_max_pages} pages")

            text_parts = []
            for i, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    logger.debug(f"Extracted page {i}: {len(page_text or '')} chars")
                except Exception as e:
                    logger.warning(f"Failed to extract page {i}: {e}")
                    text_parts.append("")

            text = "\n".join(text_parts)
            logger.info(f"Total extracted text: {len(text)} characters")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}", exc_info=True)
        raise HTTPException(
            422, "PDF could not be read. Remove password protection and export a searchable PDF."
        ) from None

    if len(text.strip()) < 30:
        raise HTTPException(
            422, "This PDF has insufficient searchable text. Image-only scans require OCR outside this MVP."
        )
    if len(text) > config.upload_max_text:
        raise HTTPException(422, "PDF contains too much text. Upload a shorter resume.")

    return text


def parse(text):
    if settings().ai_mode == "demo":
        return Extraction(skills=infer(text), coursework=[], projects=[], education=[])
    result = structured(
        Extraction,
        "Extract skills, coursework, projects (title, short supported description, technologies), and education. Do not infer credentials or invent facts. Java and JavaScript are distinct.",
        {"resume_text": redact_contacts(text)},
    )
    result.skills = normalize(result.skills)
    return result


def store_pdf(data):
    root = settings().upload_private_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    name = secrets.token_hex(24) + ".pdf"
    (root / name).write_bytes(data)
    return name, sha256(data).hexdigest()


def private_path(ref):
    root = settings().upload_private_dir.resolve()
    path = (root / ref).resolve()
    if path.parent != root:
        raise HTTPException(404, "Resume file not found")
    return path


def remove_file(ref):
    private_path(ref).unlink(missing_ok=True)


def display_filename(name):
    return Path((name or "resume.pdf").replace("\\", "/")).name[:200].replace("\r", "").replace("\n", "")
