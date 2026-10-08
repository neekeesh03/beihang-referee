from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import csv
import io
import json
import re
import hashlib
import zipfile
import xml.etree.ElementTree as ET
from typing import Any

@dataclass(slots=True)
class LoadedDocument:
    document_id: str
    path: str
    kind: str
    text: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["text_preview"] = self.text[:800]
        d.pop("text")
        return d

class DocumentLoader:
    TEXT_EXTS = {".txt", ".md", ".rst", ".tex", ".bib", ".ris", ".html", ".htm"}

    def load(self, path: str | Path, document_id: str | None = None) -> LoadedDocument:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        ext = p.suffix.lower()
        doc_id = document_id or p.stem
        if ext in self.TEXT_EXTS:
            text = p.read_text(encoding="utf-8", errors="replace")
            kind = ext.lstrip(".")
        elif ext == ".docx":
            text = self._load_docx(p)
            kind = "docx"
        elif ext == ".pdf":
            text = self._load_pdf(p)
            kind = "pdf"
        elif ext == ".json":
            obj = json.loads(p.read_text(encoding="utf-8"))
            text = json.dumps(obj, indent=2, ensure_ascii=False)
            kind = "json"
        elif ext == ".ipynb":
            obj = json.loads(p.read_text(encoding="utf-8"))
            text = "\n\n".join("".join(c.get("source", [])) for c in obj.get("cells", []))
            kind = "ipynb"
        elif ext == ".xml":
            root = ET.parse(p).getroot()
            text = " ".join(t.strip() for t in root.itertext() if t and t.strip())
            kind = "xml"
        elif ext == ".csv":
            text = self._load_csv(p)
            kind = "csv"
        elif ext in {".xlsx", ".xlsm"}:
            text = self._load_xlsx(p)
            kind = "xlsx"
        else:
            raise ValueError(f"Unsupported document format: {ext}")
        payload = p.read_bytes()
        meta = {
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "characters": len(text),
            "estimated_words": len(re.findall(r"\S+", text)),
            "suffix": ext,
        }
        return LoadedDocument(doc_id, str(p), kind, text, meta)

    def _load_docx(self, p: Path) -> str:
        with zipfile.ZipFile(p) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = []
        for para in root.iter(ns + "p"):
            chunks = [node.text or "" for node in para.iter(ns + "t")]
            if chunks:
                paragraphs.append("".join(chunks))
        return "\n".join(paragraphs)

    def _load_pdf(self, p: Path) -> str:
        try:
            import fitz  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PDF loading requires PyMuPDF (`pip install .[pdf]`)") from exc
        doc = fitz.open(p)
        return "\n\n".join(page.get_text("text") for page in doc)

    def _load_csv(self, p: Path) -> str:
        rows = []
        with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
            for i, row in enumerate(csv.reader(f)):
                rows.append("\t".join(row))
                if i >= 5000:
                    rows.append("[truncated after 5001 rows]")
                    break
        return "\n".join(rows)

    def _load_xlsx(self, p: Path) -> str:
        try:
            import openpyxl  # type: ignore
        except ImportError as exc:
            raise RuntimeError("XLSX loading requires openpyxl (`pip install .[office]`)") from exc
        wb = openpyxl.load_workbook(p, read_only=True, data_only=False)
        chunks = []
        for ws in wb.worksheets:
            chunks.append(f"## Sheet: {ws.title}")
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                chunks.append("\t".join("" if v is None else str(v) for v in row))
                if i >= 2000:
                    chunks.append("[sheet truncated after 2001 rows]")
                    break
        return "\n".join(chunks)
