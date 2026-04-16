import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional import fallback
    PdfReader = None


def _collapse_whitespace(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _read_text_with_fallbacks(file_path: Path) -> tuple[str, str]:
    raw_bytes = file_path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "utf-16", "utf-16-le"):
        try:
            return raw_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("latin-1", errors="ignore"), "latin-1"


def _extract_docx_text(file_path: Path) -> str:
    with zipfile.ZipFile(file_path) as archive:
        xml_content = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_content)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
        ]
        merged = "".join(texts).strip()
        if merged:
            paragraphs.append(merged)
    return "\n".join(paragraphs)


def _extract_doc_best_effort(file_path: Path) -> tuple[str, str]:
    raw_bytes = file_path.read_bytes()
    for encoding in ("utf-16-le", "utf-8", "gb18030", "latin-1"):
        try:
            decoded = raw_bytes.decode(encoding, errors="ignore")
        except UnicodeDecodeError:
            continue
        normalized = _collapse_whitespace(decoded)
        if len(normalized) >= 40:
            return normalized, f"best_effort_decode:{encoding}"

    binary_text = raw_bytes.decode("latin-1", errors="ignore")
    fragments = re.findall(r"[\u4e00-\u9fffA-Za-z0-9，。！？；：“”‘’、,.!?\-_\s]{6,}", binary_text)
    merged = _collapse_whitespace("\n".join(fragments))
    return merged, "best_effort_strings"


def _extract_pdf_text(file_path: Path) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed.")

    reader = PdfReader(str(file_path))
    page_texts: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        cleaned = extracted.strip()
        if cleaned:
            page_texts.append(cleaned)
    return "\n\n".join(page_texts)


class DocumentParseResult:
    def __init__(
        self,
        *,
        file_name: str,
        mime_type: str,
        parser: str,
        parse_status: str,
        extracted_text: str,
        used_text: str,
        was_truncated: bool,
        error: str | None = None,
    ) -> None:
        self.file_name = file_name
        self.mime_type = mime_type
        self.parser = parser
        self.parse_status = parse_status
        self.extracted_text = extracted_text
        self.used_text = used_text
        self.was_truncated = was_truncated
        self.error = error


class DocumentParserService:
    INLINE_CHAR_LIMIT = 4000

    def parse(self, *, file_path: str, file_name: str, mime_type: str) -> DocumentParseResult:
        path = Path(file_path)
        extension = path.suffix.lower()

        try:
            if extension in {".txt", ".md", ".rtf"}:
                extracted_text, parser = _read_text_with_fallbacks(path)
            elif extension == ".docx":
                extracted_text = _extract_docx_text(path)
                parser = "docx_xml"
            elif extension == ".doc":
                extracted_text, parser = _extract_doc_best_effort(path)
            elif extension == ".pdf":
                extracted_text = _extract_pdf_text(path)
                parser = "pypdf_text"
            else:
                return DocumentParseResult(
                    file_name=file_name,
                    mime_type=mime_type,
                    parser="unsupported",
                    parse_status="unsupported",
                    extracted_text="",
                    used_text="",
                    was_truncated=False,
                    error="Current parser supports txt/md/rtf/docx/doc/pdf.",
                )
        except FileNotFoundError:
            return DocumentParseResult(
                file_name=file_name,
                mime_type=mime_type,
                parser="missing_file",
                parse_status="failed",
                extracted_text="",
                used_text="",
                was_truncated=False,
                error="File not found on disk.",
            )
        except KeyError:
            return DocumentParseResult(
                file_name=file_name,
                mime_type=mime_type,
                parser="docx_xml",
                parse_status="failed",
                extracted_text="",
                used_text="",
                was_truncated=False,
                error="Invalid docx structure.",
            )
        except zipfile.BadZipFile:
            return DocumentParseResult(
                file_name=file_name,
                mime_type=mime_type,
                parser="docx_xml",
                parse_status="failed",
                extracted_text="",
                used_text="",
                was_truncated=False,
                error="Corrupted docx file.",
            )
        except Exception as exc:
            return DocumentParseResult(
                file_name=file_name,
                mime_type=mime_type,
                parser="unknown",
                parse_status="failed",
                extracted_text="",
                used_text="",
                was_truncated=False,
                error=str(exc),
            )

        normalized = _collapse_whitespace(extracted_text)
        if not normalized:
            return DocumentParseResult(
                file_name=file_name,
                mime_type=mime_type,
                parser=parser,
                parse_status="empty",
                extracted_text="",
                used_text="",
                was_truncated=False,
                error="No readable text extracted.",
            )

        used_text = normalized[: self.INLINE_CHAR_LIMIT].strip()
        was_truncated = len(normalized) > len(used_text)
        return DocumentParseResult(
            file_name=file_name,
            mime_type=mime_type,
            parser=parser,
            parse_status="ok",
            extracted_text=normalized,
            used_text=used_text,
            was_truncated=was_truncated,
        )
