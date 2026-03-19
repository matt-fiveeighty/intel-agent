#!/usr/bin/env python3
"""
Brand Ad Intelligence PDF Builder
Called with: python3 build_report.py <json_data_file> <output_pdf_path>
"""
import sys
import json
import os
import io
import urllib.request
import urllib.error
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from io import BytesIO

# ── Brand palette ─────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#0F1E3C")
BLUE      = colors.HexColor("#2563EB")
LIGHTBLUE = colors.HexColor("#EFF6FF")
GRAY      = colors.HexColor("#6B7280")
LIGHTGRAY = colors.HexColor("#F3F4F6")
MIDGRAY   = colors.HexColor("#E5E7EB")
BLACK     = colors.HexColor("#111827")
WHITE     = colors.white
GREEN     = colors.HexColor("#16A34A")
GREENLT   = colors.HexColor("#F0FDF4")

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch
CONTENT_W = PAGE_W - 2 * MARGIN

# ── Styles ────────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "cover_brand": S("cover_brand",
            fontName="Helvetica-Bold", fontSize=32, textColor=WHITE,
            leading=36, spaceAfter=6),
        "cover_sub": S("cover_sub",
            fontName="Helvetica", fontSize=13, textColor=colors.HexColor("#93C5FD"),
            leading=18, spaceAfter=4),
        "cover_date": S("cover_date",
            fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#CBD5E1"),
            leading=14),
        "section_label": S("section_label",
            fontName="Helvetica-Bold", fontSize=8, textColor=BLUE,
            leading=10, spaceAfter=4, spaceBefore=18,
            letterSpacing=1.5),
        "h1": S("h1",
            fontName="Helvetica-Bold", fontSize=18, textColor=NAVY,
            leading=22, spaceAfter=6, spaceBefore=10),
        "h2": S("h2",
            fontName="Helvetica-Bold", fontSize=13, textColor=NAVY,
            leading=16, spaceAfter=4, spaceBefore=10),
        "body": S("body",
            fontName="Helvetica", fontSize=10, textColor=BLACK,
            leading=15, spaceAfter=4),
        "body_sm": S("body_sm",
            fontName="Helvetica", fontSize=9, textColor=GRAY,
            leading=13, spaceAfter=3),
        "headline_item": S("headline_item",
            fontName="Helvetica-Bold", fontSize=12, textColor=BLACK,
            leading=16, spaceAfter=0),
        "ultra_item": S("ultra_item",
            fontName="Helvetica-Bold", fontSize=16, textColor=WHITE,
            leading=20, spaceAfter=0),
        "tag": S("tag",
            fontName="Helvetica-Bold", fontSize=8, textColor=BLUE,
            leading=10),
        "copy_item": S("copy_item",
            fontName="Helvetica", fontSize=9, textColor=BLACK,
            leading=13, spaceAfter=1),
        "url_style": S("url_style",
            fontName="Helvetica", fontSize=8, textColor=BLUE,
            leading=11),
        "voice_summary": S("voice_summary",
            fontName="Helvetica", fontSize=11, textColor=colors.HexColor("#1E3A5F"),
            leading=17, spaceAfter=6),
    }


def try_fetch_image(url, max_w, max_h):
    """Fetch image from URL, return reportlab Image or None."""
    if not url or not url.startswith("http"):
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=6).read()
        img_io = BytesIO(data)
        img = Image(img_io)
        # Scale to fit
        iw, ih = img.drawWidth, img.drawHeight
        scale = min(max_w / iw, max_h / ih, 1.0)
        img.drawWidth  = iw * scale
        img.drawHeight = ih * scale
        return img
    except Exception:
        return None


class ColorRect(Flowable):
    """Filled rectangle behind text — used for cover and chips."""
    def __init__(self, w, h, fill_color, radius=4):
        Flowable.__init__(self)
        self.w, self.h = w, h
        self.fill_color = fill_color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        self.canv.roundRect(0, 0, self.w, self.h, self.radius, fill=1, stroke=0)


def page_header_footer(canvas, doc, brand_name):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 36, PAGE_W, 36, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, PAGE_H - 23, f"BRAND AD INTELLIGENCE  ·  {brand_name.upper()}")
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#93C5FD"))
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 23, "AGENCY FIVE EIGHTY")
    # Footer
    canvas.setFillColor(MIDGRAY)
    canvas.rect(0, 0, PAGE_W, 28, fill=1, stroke=0)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, 9, f"Generated {datetime.now().strftime('%B %d, %Y')}  ·  Confidential")
    canvas.drawRightString(PAGE_W - MARGIN, 9, f"Page {doc.page}")
    canvas.restoreState()


def divider(styles):
    return HRFlowable(width="100%", thickness=1, color=MIDGRAY, spaceAfter=10, spaceBefore=6)


def section_header(label, title, styles):
    return [
        Paragraph(label.upper(), styles["section_label"]),
        Paragraph(title, styles["h1"]),
        divider(styles),
    ]


def tone_chip_table(words, styles):
    """Render tone words as colored chips in a table row."""
    cells = []
    for w in words[:6]:
        p = Paragraph(w.upper(), styles["tag"])
        cells.append(p)
    if not cells:
        return []
    col_w = CONTENT_W / max(len(cells), 1)
    t = Table([cells], colWidths=[col_w] * len(cells))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHTBLUE),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return [t, Spacer(1, 10)]


def headline_table(headlines, styles):
    """Two-column table of numbered headlines."""
    rows = []
    half = (len(headlines) + 1) // 2
    for i in range(half):
        left_num = f"{i+1:02d}"
        left_txt = headlines[i] if i < len(headlines) else ""
        right_num = f"{i+half+1:02d}"
        right_txt = headlines[i + half] if i + half < len(headlines) else ""

        left_cell = [
            Paragraph(f'<font color="#2563EB"><b>{left_num}</b></font>', styles["body_sm"]),
            Paragraph(left_txt, styles["headline_item"]),
        ]
        right_cell = [
            Paragraph(f'<font color="#2563EB"><b>{right_num}</b></font>', styles["body_sm"]),
            Paragraph(right_txt, styles["headline_item"]),
        ] if right_txt else [Paragraph("", styles["body_sm"])]

        rows.append([left_cell, right_cell])

    col_w = (CONTENT_W - 12) / 2
    t = Table(rows, colWidths=[col_w, col_w], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHTGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, MIDGRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def ultra_short_table(items, styles):
    """Big dark cards for ultra-short copy."""
    cells = [[Paragraph(item, styles["ultra_item"]) for item in items[:5]]]
    col_w = CONTENT_W / max(len(items[:5]), 1)
    t = Table(cells, colWidths=[col_w] * len(items[:5]))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, colors.HexColor("#1E3A5F")),
    ]))
    return t


def raw_copy_table(copy_list, styles, max_items=60):
    """Three-column table of raw collected copy."""
    items = copy_list[:max_items]
    # Pad to multiple of 3
    while len(items) % 3 != 0:
        items.append("")
    rows = []
    for i in range(0, len(items), 3):
        row = [Paragraph(f'"{items[i]}"' if items[i] else "", styles["copy_item"]),
               Paragraph(f'"{items[i+1]}"' if items[i+1] else "", styles["copy_item"]),
               Paragraph(f'"{items[i+2]}"' if items[i+2] else "", styles["copy_item"])]
        rows.append(row)
    col_w = CONTENT_W / 3
    t = Table(rows, colWidths=[col_w, col_w, col_w])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, MIDGRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHTGRAY]),
    ]))
    return t


def image_grid(image_data_list, styles, max_images=6):
    """Fetch and lay out images in a 3-col grid with source labels."""
    imgs = []
    for item in image_data_list[:max_images]:
        url = item.get("url", "")
        label = item.get("label", "")
        img = try_fetch_image(url, 1.8 * inch, 1.4 * inch)
        if img:
            imgs.append((img, label))

    if not imgs:
        return [Paragraph("No visual assets could be retrieved from public sources.", styles["body_sm"]),
                Spacer(1, 8)]

    # Pad to multiple of 3
    while len(imgs) % 3 != 0:
        imgs.append(None)

    rows = []
    for i in range(0, len(imgs), 3):
        row_cells = []
        for j in range(3):
            item = imgs[i + j]
            if item:
                img, lbl = item
                cell = [img, Spacer(1, 3), Paragraph(lbl[:50], styles["body_sm"])]
            else:
                cell = [Spacer(1, 1.4 * inch)]
            row_cells.append(cell)
        rows.append(row_cells)

    col_w = CONTENT_W / 3
    t = Table(rows, colWidths=[col_w, col_w, col_w])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, MIDGRAY),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHTGRAY),
    ]))
    return [t, Spacer(1, 8)]


def pdp_table(pdp_list, styles):
    """Table showing PDP pages with URL and key copy found."""
    rows = [[
        Paragraph("SOURCE", styles["section_label"]),
        Paragraph("URL", styles["section_label"]),
        Paragraph("KEY COPY FOUND", styles["section_label"]),
    ]]
    for p in pdp_list:
        name = p.get("name", "")
        url  = p.get("url",  "")
        copy = p.get("copy", [])
        copy_txt = "\n".join([f"• {c}" for c in copy[:4]])
        rows.append([
            Paragraph(name, styles["body"]),
            Paragraph(url[:55], styles["url_style"]),
            Paragraph(copy_txt, styles["copy_item"]),
        ])

    col_ws = [1.4 * inch, 2.4 * inch, CONTENT_W - 3.8 * inch]
    t = Table(rows, colWidths=col_ws)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHTGRAY]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, MIDGRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, MIDGRAY),
    ]))
    return t


def build_pdf(data: dict, output_path: str):
    brand       = data.get("brand", "Brand")
    voice       = data.get("voice", {})
    copy        = data.get("copy", {})
    raw_copy    = data.get("rawCopy", [])
    pdp_pages   = data.get("pdpPages", [])
    images      = data.get("images", [])   # [{url, label, channel}]
    channel_map = data.get("channelCopy", {})  # {channel: [copy strings]}

    styles = make_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 30, bottomMargin=MARGIN + 10,
        title=f"{brand} Ad Intelligence Report",
        author="Agency Five Eighty",
    )

    def on_page(canvas, doc):
        if doc.page > 1:
            page_header_footer(canvas, doc, brand)

    story = []

    # ── COVER PAGE ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.2 * inch))
    # Big navy block
    cover_data = [[
        Paragraph("BRAND AD INTELLIGENCE", ParagraphStyle("cl",
            fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#93C5FD"),
            leading=12, letterSpacing=2.5)),
        Paragraph(brand.upper(), ParagraphStyle("cb",
            fontName="Helvetica-Bold", fontSize=36, textColor=WHITE, leading=40)),
        Spacer(1, 6),
        Paragraph("PDP Copy Intelligence Report", ParagraphStyle("cs",
            fontName="Helvetica", fontSize=14, textColor=colors.HexColor("#CBD5E1"), leading=18)),
        Spacer(1, 4),
        Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y')}  ·  Agency Five Eighty",
            ParagraphStyle("cd", fontName="Helvetica", fontSize=9,
            textColor=colors.HexColor("#64748B"), leading=13)),
    ]]
    cover_t = Table(cover_data, colWidths=[CONTENT_W])
    cover_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 40),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 40),
        ("LEFTPADDING", (0, 0), (-1, -1), 40),
        ("RIGHTPADDING", (0, 0), (-1, -1), 40),
    ]))
    story.append(cover_t)
    story.append(Spacer(1, 0.4 * inch))

    # Summary stats row
    n_copy   = len(raw_copy)
    n_chan   = len([v for v in channel_map.values() if v])
    n_heads  = len(copy.get("headlines", []))
    n_pdp    = len(pdp_pages)
    stat_rows = [[
        Paragraph(f"<b>{n_copy}</b>\nCopy Samples", ParagraphStyle("sc",
            fontName="Helvetica", fontSize=11, textColor=NAVY, leading=16, alignment=TA_CENTER)),
        Paragraph(f"<b>{n_chan}</b>\nChannels Scanned", ParagraphStyle("sc2",
            fontName="Helvetica", fontSize=11, textColor=NAVY, leading=16, alignment=TA_CENTER)),
        Paragraph(f"<b>{n_pdp}</b>\nPDP Pages Scraped", ParagraphStyle("sc3",
            fontName="Helvetica", fontSize=11, textColor=NAVY, leading=16, alignment=TA_CENTER)),
        Paragraph(f"<b>{n_heads}</b>\nHeadlines Generated", ParagraphStyle("sc4",
            fontName="Helvetica", fontSize=11, textColor=NAVY, leading=16, alignment=TA_CENTER)),
    ]]
    col_w4 = CONTENT_W / 4
    stat_t = Table(stat_rows, colWidths=[col_w4]*4)
    stat_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHTBLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, MIDGRAY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(stat_t)
    story.append(PageBreak())

    # ── SECTION 1: BRAND VOICE ANALYSIS ──────────────────────────────────────
    story += section_header("01 · Brand Intelligence", "Brand Voice Analysis", styles)
    story.append(Paragraph(voice.get("summary", ""), styles["voice_summary"]))
    story.append(Spacer(1, 8))

    story += tone_chip_table(voice.get("toneWords", []), styles)

    # Themes + Patterns side by side
    themes_txt  = "\n".join([f"• {t}" for t in voice.get("themes", [])])
    patterns_txt = "\n".join([f"• {p}" for p in voice.get("patterns", [])])
    avoid_txt   = "\n".join([f"• {a}" for a in voice.get("avoid", [])])

    analysis_rows = [[
        [Paragraph("RECURRING THEMES", styles["section_label"]),
         Paragraph(themes_txt, styles["body"])],
        [Paragraph("COPY PATTERNS", styles["section_label"]),
         Paragraph(patterns_txt, styles["body"])],
        [Paragraph("BRAND AVOIDS", styles["section_label"]),
         Paragraph(avoid_txt, styles["body"])],
    ]]
    col_w3 = CONTENT_W / 3
    analysis_t = Table(analysis_rows, colWidths=[col_w3]*3)
    analysis_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHTGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, MIDGRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(analysis_t)
    story.append(PageBreak())

    # ── SECTION 2: PDP PRESENCE ───────────────────────────────────────────────
    story += section_header("02 · PDP Presence", "Product Page Scrape", styles)
    story.append(Paragraph(
        f"Agent auto-identified and scraped the top {len(pdp_pages)} PDP pages "
        f"across Amazon, brand site, and major retailers.",
        styles["body"]))
    story.append(Spacer(1, 10))
    if pdp_pages:
        story.append(pdp_table(pdp_pages, styles))
    else:
        story.append(Paragraph("No PDP data collected.", styles["body_sm"]))
    story.append(PageBreak())

    # ── SECTION 3: VISUAL EVIDENCE ────────────────────────────────────────────
    story += section_header("03 · Visual Evidence", "Ad Visuals Collected", styles)
    story.append(Paragraph(
        "Images retrieved from Meta Ad Library, brand social, digital campaigns, and ecom pages. "
        "Availability varies by brand and platform.",
        styles["body"]))
    story.append(Spacer(1, 10))

    # Group by channel
    channels = {}
    for img in images:
        ch = img.get("channel", "Other")
        channels.setdefault(ch, []).append(img)

    if channels:
        for ch, ch_imgs in channels.items():
            story.append(Paragraph(ch.upper(), styles["section_label"]))
            story += image_grid(ch_imgs, styles, max_images=6)
    else:
        story += image_grid(images, styles, max_images=9)

    story.append(PageBreak())

    # ── SECTION 4: GENERATED COPY ─────────────────────────────────────────────
    story += section_header("04 · Generated Copy", "PDP Headlines & Short Copy", styles)
    story.append(Paragraph(
        "Generated in the brand's established voice. All headlines are 8 words or fewer. "
        "Ultra-short hooks are 3 words or fewer — for badges, callouts, and hero overlays.",
        styles["body"]))
    story.append(Spacer(1, 12))

    headlines = copy.get("headlines", [])
    if headlines:
        story.append(headline_table(headlines, styles))

    story.append(Spacer(1, 20))
    story.append(Paragraph("ULTRA-SHORT COPY", styles["section_label"]))
    ultra = copy.get("ultraShort", [])
    if ultra:
        story.append(ultra_short_table(ultra, styles))

    story.append(PageBreak())

    # ── SECTION 5: RAW COPY INTELLIGENCE ─────────────────────────────────────
    story += section_header("05 · Source Intelligence", "Raw Copy Collected", styles)
    story.append(Paragraph(
        f"{len(raw_copy)} unique copy strings collected across Meta Ad Library, "
        f"social, ecom, and digital channels.",
        styles["body"]))
    story.append(Spacer(1, 10))

    # Per-channel breakdown
    for ch, ch_copy in channel_map.items():
        if not ch_copy:
            continue
        story.append(Paragraph(ch.upper(), styles["section_label"]))
        col_w2 = CONTENT_W / 2
        items = ch_copy[:20]
        while len(items) % 2 != 0:
            items.append("")
        rows = []
        for i in range(0, len(items), 2):
            rows.append([
                Paragraph(f'"{items[i]}"' if items[i] else "", styles["copy_item"]),
                Paragraph(f'"{items[i+1]}"' if items[i+1] else "", styles["copy_item"]),
            ])
        if rows:
            t = Table(rows, colWidths=[col_w2, col_w2])
            t.setStyle(TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, MIDGRAY),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHTGRAY]),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=on_page)
    print(f"PDF written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: build_report.py <data.json> <output.pdf>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    build_pdf(data, sys.argv[2])
