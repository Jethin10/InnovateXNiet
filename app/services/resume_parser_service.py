from __future__ import annotations

from io import BytesIO

from fastapi import HTTPException, UploadFile, status


class ResumeParserService:
    async def parse_upload(self, file: UploadFile) -> dict:
        content = await file.read()
        filename = file.filename or "resume.txt"
        suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"

        if suffix == "pdf":
            text = self._parse_pdf(content)
        elif suffix == "docx":
            text = self._parse_docx(content)
        elif suffix in {"txt", "md"}:
            text = content.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Supported resume formats are PDF, DOCX, TXT, and MD",
            )

        cleaned = self._clean_text(text)
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract readable resume text",
            )
        return {
            "filename": filename,
            "text": cleaned,
            "character_count": len(cleaned),
            "parse_status": "parsed",
        }

    def _parse_pdf(self, content: bytes) -> str:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _parse_docx(self, content: bytes) -> str:
        import docx

        document = docx.Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    def _clean_text(self, text: str) -> str:
        lines = [" ".join(line.strip().split()) for line in text.splitlines()]
        return "\n".join(line for line in lines if line)
