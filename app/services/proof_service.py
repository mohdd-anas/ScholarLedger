"""Generate a downloadable PDF verification proof for a publication record."""

import hashlib
import json
import textwrap
from datetime import UTC, datetime

from unidecode import unidecode

from app.models.publication import Publication

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 50
LABEL_X = 50
VALUE_X = 185
RIGHT_X = PAGE_WIDTH - MARGIN_X


def _to_winansi_bytes(text: str) -> bytes:
    """Convert arbitrary Unicode text into WinAnsi (cp1252) bytes safely."""
    chars: list[str] = []
    for ch in text:
        try:
            ch.encode("cp1252")
            chars.append(ch)
        except UnicodeEncodeError:
            chars.append(unidecode(ch))
    return "".join(chars).encode("cp1252", errors="replace")


def _pdf_literal(text: str) -> bytes:
    """Escape a string as a PDF literal string in WinAnsi encoding."""
    raw = _to_winansi_bytes(text)
    escaped = raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    return b"(" + escaped + b")"


def compute_proof_digest(pub: Publication) -> str:
    """Compute a deterministic SHA-256 digest over canonical publication fields."""
    payload = {
        "id": pub.id,
        "title": pub.title,
        "authors": pub.authors,
        "venue": pub.venue or "",
        "year": pub.year,
        "doi": pub.doi or "",
        "pub_type": pub.pub_type.value,
        "department": pub.department or "",
        "status": pub.status.value,
        "source": pub.source.value,
        "owner_faculty_id": pub.owner_faculty_id,
        "coauthor_ids": sorted(pub.coauthor_ids),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """Wrap text into lines bounded by max_chars, preserving empty fallback."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ["—"]
    return textwrap.wrap(cleaned, width=max_chars, break_long_words=True) or ["—"]


def build_publication_proof_pdf(pub: Publication) -> bytes:
    """Render a clean A4 PDF proof document for a publication record."""
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    digest = compute_proof_digest(pub)

    owner_str = (
        f"{pub.owner.name} ({pub.owner.email})"
        if pub.owner
        else f"Faculty #{pub.owner_faculty_id}"
    )
    if pub.coauthors:
        coauthors_str = "; ".join(
            f"{c.name} ({c.department}, {c.email})" for c in pub.coauthors
        )
    else:
        coauthors_str = "None linked"

    rows: list[tuple[str, str]] = [
        ("Record ID", f"#{pub.id}"),
        ("Status", pub.status.value.upper()),
        ("Source", pub.source.value),
        ("Title", pub.title),
        ("Authors", pub.authors),
        ("Venue / Journal", pub.venue or "—"),
        ("Year", str(pub.year) if pub.year else "—"),
        ("DOI", f"https://doi.org/{pub.doi}" if pub.doi else "—"),
        ("Type", pub.pub_type.value),
        ("Department", pub.department or "—"),
        ("Owner", owner_str),
        ("University Co-Authors", coauthors_str),
        (
            "Match Confidence",
            f"{pub.match_confidence * 100:.1f}%"
            if pub.match_confidence is not None
            else "—",
        ),
        (
            "Recorded At",
            pub.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if pub.created_at
            else "—",
        ),
        (
            "Last Updated",
            pub.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if pub.updated_at
            else "—",
        ),
        ("Proof Generated", generated_at),
        ("SHA-256 Digest", digest),
    ]

    pages: list[list[bytes]] = [[]]

    def add_cmd(cmd: bytes) -> None:
        pages[-1].append(cmd)

    def draw_header() -> int:
        # Top accent bar
        add_cmd(b"0.145 0.388 0.922 rg")
        add_cmd(f"{MARGIN_X} {PAGE_HEIGHT - 54} {RIGHT_X - MARGIN_X} 4 re f".encode("ascii"))
        add_cmd(b"0.118 0.161 0.231 rg")
        add_cmd(b"BT /F2 18 Tf " + f"{MARGIN_X} {PAGE_HEIGHT - 80} Td ".encode("ascii")
                + _pdf_literal("ScholarLedger — Publication Proof") + b" Tj ET")
        add_cmd(b"0.392 0.455 0.545 rg")
        add_cmd(b"BT /F1 10 Tf " + f"{MARGIN_X} {PAGE_HEIGHT - 98} Td ".encode("ascii")
                + _pdf_literal(
                    "Official export of recorded university publication metadata & attribution"
                )
                + b" Tj ET")
        add_cmd(b"0.886 0.910 0.941 RG 0.8 w")
        add_cmd(
            f"{MARGIN_X} {PAGE_HEIGHT - 110} m {RIGHT_X} {PAGE_HEIGHT - 110} l S".encode("ascii")
        )
        return PAGE_HEIGHT - 132

    y = draw_header()
    line_height = 15

    for label, value in rows:
        max_chars = 60 if label != "SHA-256 Digest" else 64
        wrapped = _wrap_text(value, max_chars=max_chars)
        block_height = len(wrapped) * line_height + 10

        if y - block_height < 65:
            pages.append([])
            y = draw_header()

        # Field label
        add_cmd(b"0.392 0.455 0.545 rg")
        add_cmd(
            b"BT /F2 9 Tf "
            + f"{LABEL_X} {y} Td ".encode("ascii")
            + _pdf_literal(label.upper())
            + b" Tj ET"
        )

        # Field value lines
        add_cmd(b"0.118 0.161 0.231 rg")
        cur_y = y
        font_key = b"/F2" if label == "Title" else b"/F1"
        for line in wrapped:
            add_cmd(
                b"BT "
                + font_key
                + b" 10 Tf "
                + f"{VALUE_X} {cur_y} Td ".encode("ascii")
                + _pdf_literal(line)
                + b" Tj ET"
            )
            cur_y -= line_height

        # Row divider
        divider_y = cur_y + 4
        add_cmd(b"0.886 0.910 0.941 RG 0.5 w")
        add_cmd(f"{MARGIN_X} {divider_y} m {RIGHT_X} {divider_y} l S".encode("ascii"))
        y = divider_y - 16

    # Footer on every page
    total_pages = len(pages)
    for idx, cmds in enumerate(pages, start=1):
        footer = (
            f"ScholarLedger Publication Proof  |  Record #{pub.id}  "
            f"|  Page {idx} of {total_pages}"
        )
        cmds.append(b"0.392 0.455 0.545 rg")
        cmds.append(
            b"BT /F1 8 Tf "
            + f"{MARGIN_X} 36 Td ".encode("ascii")
            + _pdf_literal(footer)
            + b" Tj ET"
        )

    # Assemble PDF objects: Catalog, Pages, Fonts, and Page/Content pairs
    objects: list[bytes] = []
    page_obj_nums: list[int] = []

    objects.append(b"")  # placeholder 1: Catalog
    objects.append(b"")  # placeholder 2: Pages
    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"
    )

    for page_cmds in pages:
        stream = b"\n".join(page_cmds)
        content_obj_num = len(objects) + 1
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream"
        )
        page_obj_num = len(objects) + 1
        page_obj_nums.append(page_obj_num)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_obj_num} 0 R >>".encode("ascii")
        )

    kids = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_nums)} >>".encode("ascii")

    # Serialize with exact byte offsets
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = [0]
    for idx, obj_body in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode("ascii"))
        out.extend(obj_body)
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)
