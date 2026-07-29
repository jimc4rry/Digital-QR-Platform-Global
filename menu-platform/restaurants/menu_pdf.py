"""Generates a printable, branded PDF of a restaurant's full menu (all active
categories and available products) for the owner to download and print."""
import os
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils.translation import gettext as _
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PRIMARY_COLOR = colors.HexColor('#6366f1')
TEXT_COLOR = colors.HexColor('#1f2937')
MUTED_COLOR = colors.HexColor('#6b7280')
RULE_COLOR = colors.HexColor('#e5e7eb')
OLD_PRICE_COLOR = colors.HexColor('#9ca3af')

def _diet_labels():
    """Built at call time (not import time) so gettext() picks up the
    current request's language, not whatever was active at server startup."""
    return {
        'is_vegan': _('Vegan'),
        'is_vegetarian': _('Vegetarian'),
        'is_gluten_free': _('Gluten-Free'),
        'is_spicy': _('Spicy'),
    }

# ReportLab's built-in base-14 fonts (Helvetica etc.) only cover Latin-1, which
# drops accented Greek vowels (a restaurant's own name/menu is very often
# Greek). DejaVu Sans has full Greek/Cyrillic/Latin coverage and ships under a
# license that permits redistribution, so it's bundled here instead.
FONT_REGULAR = 'DejaVuSans'
FONT_BOLD = 'DejaVuSans-Bold'
FONT_ITALIC = 'DejaVuSans-Oblique'
_FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')


def _register_fonts():
    if FONT_REGULAR in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, os.path.join(_FONTS_DIR, 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(_FONTS_DIR, 'DejaVuSans-Bold.ttf')))
    pdfmetrics.registerFont(TTFont(FONT_ITALIC, os.path.join(_FONTS_DIR, 'DejaVuSans-Oblique.ttf')))
    pdfmetrics.registerFontFamily(
        FONT_REGULAR, normal=FONT_REGULAR, bold=FONT_BOLD, italic=FONT_ITALIC, boldItalic=FONT_BOLD,
    )


def _styles():
    _register_fonts()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'MenuRestaurantName', fontName=FONT_BOLD, fontSize=24, leading=28,
        textColor=TEXT_COLOR, alignment=TA_CENTER, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        'MenuTagline', fontName=FONT_ITALIC, fontSize=10, leading=13,
        textColor=MUTED_COLOR, alignment=TA_CENTER, spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        'MenuCategoryHeader', fontName=FONT_BOLD, fontSize=15, leading=18,
        textColor=PRIMARY_COLOR, spaceBefore=16, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'MenuProductName', fontName=FONT_BOLD, fontSize=11, leading=14, textColor=TEXT_COLOR,
    ))
    styles.add(ParagraphStyle(
        'MenuProductDesc', fontName=FONT_REGULAR, fontSize=9, leading=12,
        textColor=MUTED_COLOR, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        'MenuProductPrice', fontName=FONT_BOLD, fontSize=11, leading=14,
        textColor=PRIMARY_COLOR, alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        'MenuEmpty', fontName=FONT_ITALIC, fontSize=11, leading=14,
        textColor=MUTED_COLOR, alignment=TA_CENTER, spaceBefore=40,
    ))
    return styles


def _footer(canvas_obj, doc, restaurant_name):
    canvas_obj.saveState()
    canvas_obj.setFont(FONT_REGULAR, 8)
    canvas_obj.setFillColor(MUTED_COLOR)
    footer_text = _('%(restaurant)s — Powered by GetMenuHub — Page %(page)s') % {
        'restaurant': restaurant_name, 'page': doc.page,
    }
    canvas_obj.drawCentredString(doc.pagesize[0] / 2, 1.1 * cm, footer_text)
    canvas_obj.restoreState()


def _logo_flowable(restaurant):
    if not restaurant.logo or not hasattr(restaurant.logo, 'path'):
        return None
    try:
        with PILImage.open(restaurant.logo.path) as im:
            width_px, height_px = im.size
    except (OSError, ValueError):
        return None

    max_h, max_w = 2.2 * cm, 4 * cm
    scale = min(max_h / height_px, max_w / width_px)
    img = Image(restaurant.logo.path, width=width_px * scale, height=height_px * scale)
    img.hAlign = 'CENTER'
    return img


def _product_rows(products, styles):
    diet_labels = _diet_labels()
    rows = []
    for product in products:
        name_text = escape(product.get_display_name())
        tags = [diet_labels[field] for field in diet_labels if getattr(product, field, False)]
        if tags:
            name_text += f' <font size="7" color="#6b7280">({escape(", ".join(tags))})</font>'

        if product.old_price:
            price_text = (
                f'<font size="8" color="#9ca3af"><strike>${product.old_price:.2f}</strike></font><br/>'
                f'${product.price:.2f}'
            )
        else:
            price_text = f'${product.price:.2f}'

        rows.append([
            Paragraph(name_text, styles['MenuProductName']),
            Paragraph(price_text, styles['MenuProductPrice']),
        ])
        if product.description:
            rows.append([Paragraph(escape(product.description), styles['MenuProductDesc']), ''])
    return rows


def build_menu_pdf(restaurant, categories):
    """categories: an iterable of Category instances, each with a prefetched
    `products` relation. Returns a BytesIO positioned at the start of the PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        title=f'{restaurant.name} - Menu',
    )
    styles = _styles()
    elements = []

    logo = _logo_flowable(restaurant)
    if logo:
        elements.append(logo)
        elements.append(Spacer(1, 0.3 * cm))

    elements.append(Paragraph(escape(restaurant.name), styles['MenuRestaurantName']))
    if restaurant.description:
        elements.append(Paragraph(escape(restaurant.description), styles['MenuTagline']))

    elements.append(HRFlowable(width='100%', thickness=1, color=PRIMARY_COLOR, spaceAfter=6))

    has_any_products = False
    for category in categories:
        products = [p for p in category.products.all() if p.is_available]
        if not products:
            continue
        has_any_products = True

        elements.append(Paragraph(escape(category.name), styles['MenuCategoryHeader']))
        elements.append(HRFlowable(width='100%', thickness=0.5, color=RULE_COLOR, spaceAfter=6))

        table = Table(_product_rows(products, styles), colWidths=[13.5 * cm, 3 * cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.4 * cm))

    if not has_any_products:
        elements.append(Paragraph(escape(_('No products available yet.')), styles['MenuEmpty']))

    restaurant_name = restaurant.name
    doc.build(
        elements,
        onFirstPage=lambda c, d: _footer(c, d, restaurant_name),
        onLaterPages=lambda c, d: _footer(c, d, restaurant_name),
    )
    buffer.seek(0)
    return buffer
