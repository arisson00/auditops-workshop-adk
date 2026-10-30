"""Extrator e Gerador Nativo de Documentos Paginados (.PDF, .DOCX, .MD, .TXT) para o AuditOps 2.0.

Suporta:
1. Extração nativa de arquivos `.docx` (OpenXML `word/document.xml` via `zipfile` + `xml.etree.ElementTree`)
   com detecção de quebras de página (`w:br w:type="page"`), tabelas e cabeçalhos de cláusulas.
2. Extração nativa de arquivos `.pdf` página a página (`pypdf`/`pdfplumber` quando disponível + parser
   nativo de objetos `/Type /Page` e streams `FlateDecode` em Python puro, zero dependências externas).
3. Geração de arquivos `.pdf` multipágina reais (PDF 1.4 com objetos `/Page` independentes) a partir
   dos contratos da carteira corporativa.
"""

import io
import re
import zlib
import base64
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple


def _decode_pdf_literal_string(raw: str) -> str:
    """Decodifica strings literais de operadores PDF `( ... )` com escapes octais e especiais."""
    out = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch == "\\" and i + 1 < n:
            nxt = raw[i + 1]
            if nxt in "01234567":
                oct_digits = nxt
                j = i + 2
                while j < n and len(oct_digits) < 3 and raw[j] in "01234567":
                    oct_digits += raw[j]
                    j += 1
                out.append(int(oct_digits, 8) & 0xFF)
                i = j
                continue
            elif nxt == "n":
                out.append(10)
            elif nxt == "r":
                out.append(13)
            elif nxt == "t":
                out.append(9)
            elif nxt in ("(", ")", "\\"):
                out.append(ord(nxt))
            else:
                out.append(ord(nxt))
            i += 2
        else:
            out.append(ord(ch) & 0xFF)
            i += 1
    try:
        if out.startswith(b"\xfe\xff"):
            return out[2:].decode("utf-16-be", errors="replace")
        return out.decode("cp1252", errors="replace")
    except Exception:
        return out.decode("latin-1", errors="replace")


def _decode_pdf_hex_string(hex_str: str) -> str:
    """Decodifica strings hexadecimais `<...>` de streams PDF."""
    cleaned = re.sub(r"\s+", "", hex_str)
    if len(cleaned) % 2 == 1:
        cleaned += "0"
    try:
        raw_bytes = bytes.fromhex(cleaned)
        if raw_bytes.startswith(b"\xfe\xff"):
            return raw_bytes[2:].decode("utf-16-be", errors="replace")
        return raw_bytes.decode("cp1252", errors="replace")
    except Exception:
        return ""


def _extract_text_from_pdf_stream(stream_text: str) -> str:
    """Extrai linhas de texto legível de um content stream PDF (`BT ... ET`, `Tj`, `TJ`)."""
    lines: List[str] = []
    current_line: List[str] = []

    token_pattern = re.compile(
        r"(\((?:\\.|[^\\()])*\)\s*Tj)"
        r"|(\[(?:\\.|[^\[\]])*\]\s*TJ)"
        r"|(<[0-9A-Fa-f\s]+>\s*Tj)"
        r"|(T\*|Td|TD|\'\s)",
        re.DOTALL,
    )

    for match in token_pattern.finditer(stream_text):
        tok = match.group(0)
        if tok.endswith("Tj"):
            inner = tok[:-2].strip()
            if inner.startswith("(") and inner.endswith(")"):
                current_line.append(_decode_pdf_literal_string(inner[1:-1]))
            elif inner.startswith("<") and inner.endswith(">"):
                current_line.append(_decode_pdf_hex_string(inner[1:-1]))
        elif tok.endswith("TJ"):
            inner = tok[:-2].strip()
            for part in re.finditer(r"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>", inner):
                p = part.group(0)
                if p.startswith("("):
                    current_line.append(_decode_pdf_literal_string(p[1:-1]))
                elif p.startswith("<"):
                    current_line.append(_decode_pdf_hex_string(p[1:-1]))
        else:
            if current_line:
                lines.append("".join(current_line).strip())
                current_line = []

    if current_line:
        lines.append("".join(current_line).strip())

    return "\n".join(l for l in lines if l)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Tuple[str, int]:
    """Extrai texto paginado (`--- [Página X] ---`) de um arquivo PDF binário."""
    # 1. Tenta pypdf / PyPDF2 caso instalado no ambiente
    for mod_name in ("pypdf", "PyPDF2"):
        try:
            mod = __import__(mod_name)
            reader = mod.PdfReader(io.BytesIO(pdf_bytes))
            pages_out: List[str] = []
            for idx, page in enumerate(reader.pages, start=1):
                txt = (page.extract_text() or "").strip()
                if txt:
                    if f"[Página {idx}]" not in txt:
                        pages_out.append(f"--- [Página {idx}] ---\n\n{txt}")
                    else:
                        pages_out.append(txt)
            if pages_out:
                return "\n\n".join(pages_out), len(pages_out)
        except Exception:
            pass

    # 2. Parser nativo em Python puro (suporta streams diretos e FlateDecode por página)
    pages_extracted: List[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.DOTALL):
        raw_stream = match.group(1)
        decoded_stream = None
        try:
            decoded_stream = zlib.decompress(raw_stream).decode("latin-1", errors="replace")
        except Exception:
            try:
                decoded_stream = raw_stream.decode("latin-1", errors="replace")
            except Exception:
                decoded_stream = None

        if decoded_stream and ("BT" in decoded_stream or "Tj" in decoded_stream or "TJ" in decoded_stream):
            page_txt = _extract_text_from_pdf_stream(decoded_stream).strip()
            if page_txt and len(page_txt) > 10:
                pages_extracted.append(page_txt)

    if pages_extracted:
        formatted_pages: List[str] = []
        for idx, p_txt in enumerate(pages_extracted, start=1):
            if re.search(r"---\s*\[P.+?gina\s*\d+\]\s*---", p_txt, re.IGNORECASE):
                formatted_pages.append(p_txt)
            else:
                formatted_pages.append(f"--- [Página {idx}] ---\n\n{p_txt}")
        return "\n\n".join(formatted_pages), len(formatted_pages)

    # 3. Fallback caso o PDF contenha texto plano embutido
    fallback_txt = pdf_bytes.decode("utf-8", errors="ignore")
    return auto_paginate_text(fallback_txt)


def extract_text_from_docx_bytes(docx_bytes: bytes) -> Tuple[str, int]:
    """Extrai texto paginado (`--- [Página X] ---`) de um arquivo Word `.docx` (OpenXML)."""
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        xml_bytes = zf.read("word/document.xml")

    root = ET.fromstring(xml_bytes)
    ns_w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    pages: List[List[str]] = [[]]
    current_page_idx = 0

    body = root.find(f"{ns_w}body")
    elements = list(body) if body is not None else list(root)

    for elem in elements:
        if elem.tag == f"{ns_w}p":
            # Verifica se há quebra de página explícita no parágrafo
            has_page_break = False
            for br in elem.iter(f"{ns_w}br"):
                if br.attrib.get(f"{ns_w}type") == "page":
                    has_page_break = True
            if has_page_break and pages[current_page_idx]:
                pages.append([])
                current_page_idx += 1

            texts = [t.text for t in elem.iter(f"{ns_w}t") if t.text]
            para_str = "".join(texts).strip()
            if not para_str:
                continue

            # Verifica marcador explícito de página no texto
            page_marker = re.search(r"---\s*\[P.+?gina\s*(\d+)\]\s*---", para_str, re.IGNORECASE)
            if page_marker:
                p_num = int(page_marker.group(1))
                while len(pages) < p_num:
                    pages.append([])
                current_page_idx = p_num - 1
                continue

            # Formata títulos de cláusulas como markdown headers para o indexador RAG
            if re.match(r"^(CLÁUSULA|CLAUSULA|IDENTIFICAÇÃO| CAPÍTULO|SEÇÃO|\[\w+-\w+-\d+\])", para_str, re.IGNORECASE):
                if not para_str.startswith("#"):
                    para_str = f"### {para_str}"
            pages[current_page_idx].append(para_str)

        elif elem.tag == f"{ns_w}tbl":
            for row in elem.iter(f"{ns_w}tr"):
                cells = []
                for cell in row.iter(f"{ns_w}tc"):
                    c_txt = " ".join(t.text.strip() for t in cell.iter(f"{ns_w}t") if t.text and t.text.strip())
                    if c_txt:
                        cells.append(c_txt)
                if cells:
                    pages[current_page_idx].append(" | ".join(cells))

    non_empty_pages = [p for p in pages if p]
    if not non_empty_pages:
        return "", 1

    # Se o DOCX inteiro veio em 1 única página longa (> 1600 caracteres), pagina automaticamente por blocos/cláusulas
    if len(non_empty_pages) == 1:
        full_joined = "\n\n".join(non_empty_pages[0])
        if len(full_joined) > 1500:
            return auto_paginate_text(full_joined)

    out_blocks = []
    for idx, p_lines in enumerate(non_empty_pages, start=1):
        out_blocks.append(f"--- [Página {idx}] ---\n\n" + "\n\n".join(p_lines))
    return "\n\n".join(out_blocks), len(out_blocks)


def auto_paginate_text(raw_text: str, chars_per_page: int = 1200) -> Tuple[str, int]:
    """Garante que qualquer texto ou documento tenha marcadores `--- [Página X] ---`."""
    text = (raw_text or "").strip()
    if not text:
        return "", 1

    existing_markers = re.findall(r"---\s*\[P.+?gina\s*(\d+)\]\s*---", text, re.IGNORECASE)
    if existing_markers:
        return text, max(int(m) for m in existing_markers)

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pages: List[List[str]] = [[]]
    current_len = 0

    for para in paragraphs:
        is_major_clause = bool(re.match(r"^(#{1,3}\s+)?(CLÁUSULA|CLAUSULA)\s+\d+", para, re.IGNORECASE))
        if current_len > 0 and (current_len + len(para) > chars_per_page or (is_major_clause and current_len > 650)):
            pages.append([para])
            current_len = len(para)
        else:
            pages[-1].append(para)
            current_len += len(para)

    out_blocks = []
    for idx, p_lines in enumerate(pages, start=1):
        out_blocks.append(f"--- [Página {idx}] ---\n\n" + "\n\n".join(p_lines))
    return "\n\n".join(out_blocks), len(out_blocks)


def parse_uploaded_document(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """Extrai texto paginado e metadados de qualquer arquivo `.pdf`, `.docx`, `.md` ou `.txt`."""
    fname = (filename or "documento.pdf").strip()
    ext = fname.lower().rsplit(".", 1)[-1] if "." in fname else "txt"

    if ext == "pdf":
        text, num_pages = extract_text_from_pdf_bytes(file_bytes)
        doc_format = "PDF (Adobe Portable Document Format)"
    elif ext in ("docx", "doc"):
        text, num_pages = extract_text_from_docx_bytes(file_bytes)
        doc_format = "DOCX (Microsoft Word OpenXML)"
    else:
        raw_str = file_bytes.decode("utf-8", errors="replace")
        text, num_pages = auto_paginate_text(raw_str)
        doc_format = f"{ext.upper()} (Texto Estruturado)"

    return {
        "filename": fname,
        "extension": ext,
        "format": ext.upper(),
        "file_format": ext.upper(),
        "document_format": doc_format,
        "total_pages": num_pages,
        "char_count": len(text),
        "extracted_text": text,
    }


def _pdf_escape_cp1252(text: str) -> str:
    """Converte string UTF-8 para bytes CP1252 escapados para literal PDF `( ... )`."""
    raw = text.encode("cp1252", errors="replace")
    out = []
    for b in raw:
        if b == ord("\\"):
            out.append("\\\\")
        elif b == ord("("):
            out.append("\\(")
        elif b == ord(")"):
            out.append("\\)")
        elif 32 <= b <= 126:
            out.append(chr(b))
        else:
            out.append(f"\\{b:03o}")
    return "".join(out)


def generate_pdf_bytes_from_markdown(md_text: str, title: str = "Contrato Corporativo") -> bytes:
    """Gera um arquivo PDF 1.4 multipágina real (1 objeto `/Page` por `--- [Página X] ---`)."""
    paginated_text, _ = auto_paginate_text(md_text)
    parts = re.split(r"(---\s*\[P.+?gina\s*\d+\]\s*---)", paginated_text, flags=re.IGNORECASE)
    pages_content: List[str] = []
    preamble = ""
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        if re.match(r"---\s*\[P.+?gina\s*\d+\]\s*---", chunk, flags=re.IGNORECASE):
            body = parts[i + 1].strip() if (i + 1) < len(parts) else ""
            if preamble:
                body = f"{preamble}\n\n{body}".strip()
                preamble = ""
            if body:
                pages_content.append(body)
            i += 2
        else:
            if chunk:
                preamble = f"{preamble}\n{chunk}".strip()
            i += 1
    if not pages_content:
        pages_content = [md_text.strip()]

    # Estrutura de objetos PDF:
    # 1: Catalog, 2: Pages, 3: Font Helvetica, 4: Font Helvetica-Bold
    # Depois pares (PageObj, ContentStreamObj) para cada página
    objects: List[bytes] = []

    def add_obj(content: bytes) -> int:
        objects.append(content)
        return len(objects)

    add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")  # Obj 1
    add_obj(b"")  # Obj 2 placeholder (/Pages)
    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")  # Obj 3
    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")  # Obj 4

    page_obj_ids: List[int] = []
    total_pages = len(pages_content)

    for page_idx, p_text in enumerate(pages_content, start=1):
        stream_lines = [
            "BT",
            "/F2 10 Tf",
            "50 790 Td",
            f"({_pdf_escape_cp1252(f'AUDITOPS EXECUTIVE - INSTRUMENTO CONTRATUAL  |  --- [Página {page_idx}] ---')}) Tj",
            "0 -18 Td",
            "/F2 12 Tf",
            f"({_pdf_escape_cp1252(title[:85])}) Tj",
            "0 -20 Td",
            "/F1 9.5 Tf",
        ]

        y_pos = 752
        for raw_line in p_text.splitlines():
            clean = raw_line.strip()
            if not clean:
                stream_lines.append("0 -10 Td")
                y_pos -= 10
                continue

            is_header = clean.startswith("#")
            clean_txt = re.sub(r"^#{1,4}\s*", "", clean)
            clean_txt = clean_txt.replace("**", "")

            # Quebra linhas longas em 88 caracteres para caber na página A4
            wrapped: List[str] = []
            while len(clean_txt) > 88:
                split_at = clean_txt.rfind(" ", 0, 88)
                if split_at <= 0:
                    split_at = 88
                wrapped.append(clean_txt[:split_at])
                clean_txt = clean_txt[split_at:].strip()
            if clean_txt:
                wrapped.append(clean_txt)

            for w_idx, w_line in enumerate(wrapped):
                if y_pos < 55:
                    break
                if is_header and w_idx == 0:
                    stream_lines.append("/F2 10.5 Tf")
                    stream_lines.append("0 -15 Td")
                    stream_lines.append(f"({_pdf_escape_cp1252(w_line)}) Tj")
                    stream_lines.append("/F1 9.5 Tf")
                    y_pos -= 15
                else:
                    stream_lines.append("0 -13 Td")
                    stream_lines.append(f"({_pdf_escape_cp1252(w_line)}) Tj")
                    y_pos -= 13

        stream_lines.append("ET")
        stream_data = "\n".join(stream_lines).encode("latin-1", errors="replace")
        compressed = zlib.compress(stream_data)

        content_obj_id = add_obj(
            f"<< /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode("ascii")
            + compressed
            + b"\nendstream"
        )
        page_obj_id = add_obj(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_obj_id} 0 R >>".encode("ascii")
        )
        page_obj_ids.append(page_obj_id)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {total_pages} >>".encode("ascii")

    # Monta o arquivo PDF com tabela xref exata
    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: List[int] = [0]
    for idx, obj_bytes in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf.extend(f"{idx} 0 obj\n".encode("ascii"))
        buf.extend(obj_bytes)
        buf.extend(b"\nendobj\n")

    xref_pos = len(buf)
    buf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    buf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(buf)
