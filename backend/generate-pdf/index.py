import json
import base64
import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader


# Размеры форматов фотокниг (ширина × высота в мм), разворот = 2 страницы рядом
FORMATS = {
    '20x20': (200, 200),
    '30x20': (300, 200),
    '21x29': (210, 297),
    '30x30': (300, 300),
}

# Поля для типографии (мм)
BLEED = 3      # вылет за обрез
SAFE  = 5      # безопасная зона от обреза
SPINE = 10     # корешок посередине разворота


def draw_page(c: canvas.Canvas, w: float, h: float, spread_num: int,
              heading: str, caption: str, text: str,
              is_right: bool = False) -> None:
    """Рисует одну страницу разворота."""
    bleed = BLEED * mm
    safe  = SAFE  * mm

    # Фон страницы
    c.setFillColor(colors.HexColor('#0c0a18'))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Декоративный градиент-полоса сверху
    c.setFillColor(colors.HexColor('#F4622A'))
    c.rect(0, h - 6 * mm, w, 6 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#6C5CE7'))
    c.rect(0, h - 12 * mm, w, 6 * mm, fill=1, stroke=0)

    # Рамка места под фото
    photo_x = safe + bleed
    photo_y = h * 0.35
    photo_w = w - 2 * (safe + bleed)
    photo_h = h * 0.45
    c.setFillColor(colors.HexColor('#1a1730'))
    c.roundRect(photo_x, photo_y, photo_w, photo_h, 8 * mm, fill=1, stroke=0)

    # Иконка «место для фото»
    c.setFillColor(colors.HexColor('#ffffff20'))
    cx = photo_x + photo_w / 2
    cy = photo_y + photo_h / 2
    c.setLineWidth(0.8 * mm)
    c.setStrokeColor(colors.HexColor('#ffffff30'))
    c.roundRect(cx - 18 * mm, cy - 12 * mm, 36 * mm, 24 * mm, 3 * mm, fill=0, stroke=1)

    # Метки обрезки (crop marks) — 4 угла
    mark = 5 * mm
    gap  = 2 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.25 * mm)
    for x, y in [(bleed, bleed), (w - bleed, bleed), (bleed, h - bleed), (w - bleed, h - bleed)]:
        sx = 1 if x == bleed else -1
        sy = 1 if y == bleed else -1
        c.line(x + sx * gap, y, x + sx * (gap + mark), y)
        c.line(x, y + sy * gap, x, y + sy * (gap + mark))

    # Номер разворота
    c.setFillColor(colors.HexColor('#ffffff40'))
    c.setFont('Helvetica', 7)
    side = 'R' if is_right else 'L'
    c.drawString(safe + bleed, safe + bleed, f'Разворот {spread_num} • {side}')

    # Заголовок
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 14)
    text_x = safe + bleed
    text_w = w - 2 * (safe + bleed)
    _draw_wrapped(c, heading, text_x, photo_y - 10 * mm, text_w, 14, 'Helvetica-Bold', colors.white, align='center', w=w)

    # Основной текст
    _draw_wrapped(c, text, text_x, photo_y - 28 * mm, text_w, 9, 'Helvetica', colors.HexColor('#ffffffcc'))

    # Подпись-капшн
    _draw_wrapped(c, caption, text_x, safe + bleed + 8 * mm, text_w, 8, 'Helvetica-Oblique', colors.HexColor('#F4E070'))

    # Линия вылета
    c.setStrokeColor(colors.HexColor('#ffffff15'))
    c.setLineWidth(0.3 * mm)
    c.rect(bleed, bleed, w - 2 * bleed, h - 2 * bleed, fill=0, stroke=1)


def _draw_wrapped(c, text, x, y, max_w, font_size, font, color, align='left', w=None):
    """Рисует текст с переносом строк."""
    c.setFont(font, font_size)
    c.setFillColor(color)
    words = text.split()
    line = ''
    line_h = font_size * 1.4
    cur_y = y
    lines = []
    for word in words:
        test = (line + ' ' + word).strip()
        if c.stringWidth(test, font, font_size) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    for l in lines:
        lw = c.stringWidth(l, font, font_size)
        if align == 'center' and w:
            draw_x = x + (max_w - lw) / 2
        else:
            draw_x = x
        c.drawString(draw_x, cur_y, l)
        cur_y -= line_h
        if cur_y < 0:
            break


def build_pdf(story: dict, fmt: str) -> bytes:
    """Строит PDF-разворот для типографии и возвращает байты."""
    page_w_mm, page_h_mm = FORMATS.get(fmt, FORMATS['20x20'])
    bleed = BLEED
    # Размер страницы с вылетом
    pw = (page_w_mm + 2 * bleed) * mm
    ph = (page_h_mm + 2 * bleed) * mm

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(pw, ph))
    c.setTitle(story.get('title', 'Фотокнига'))
    c.setAuthor('Фотокнига')

    spreads = story.get('spreads', [])

    # Обложка
    c.setFillColor(colors.HexColor('#0c0a18'))
    c.rect(0, 0, pw, ph, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#F4622A'))
    c.rect(0, ph - 8 * mm, pw, 8 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#6C5CE7'))
    c.rect(0, ph - 16 * mm, pw, 8 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 22)
    title = story.get('title', 'Фотокнига')
    tw = c.stringWidth(title, 'Helvetica-Bold', 22)
    c.drawString((pw - tw) / 2, ph / 2 + 10 * mm, title)
    intro = story.get('intro', '')
    c.setFont('Helvetica', 10)
    c.setFillColor(colors.HexColor('#ffffffcc'))
    _draw_wrapped(c, intro, 15 * mm, ph / 2 - 8 * mm, pw - 30 * mm, 10, 'Helvetica', colors.HexColor('#ffffffcc'))
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#ffffff50'))
    c.drawString(15 * mm, 15 * mm, 'С полями 3мм для вылета и 5мм безопасная зона')
    c.showPage()

    # Развороты
    for i, spread in enumerate(spreads):
        heading = spread.get('heading', '')
        caption = spread.get('caption', '')
        text    = spread.get('text', '')

        # Левая страница
        draw_page(c, pw, ph, i + 1, heading, caption, text, is_right=False)
        c.showPage()

        # Правая страница
        draw_page(c, pw, ph, i + 1, caption, heading, text, is_right=True)
        c.showPage()

    # Задняя обложка
    c.setFillColor(colors.HexColor('#0c0a18'))
    c.rect(0, 0, pw, ph, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#6C5CE7'))
    c.rect(0, 0, pw, 8 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#F4622A'))
    c.rect(0, 8 * mm, pw, 8 * mm, fill=1, stroke=0)
    c.setFont('Helvetica', 9)
    c.setFillColor(colors.HexColor('#ffffff60'))
    tagline = 'Создано с любовью · фотокнига.рф'
    tw = c.stringWidth(tagline, 'Helvetica', 9)
    c.drawString((pw - tw) / 2, ph / 2, tagline)
    c.showPage()

    c.save()
    return buf.getvalue()


def handler(event: dict, context) -> dict:
    '''Собирает PDF-макет фотокниги с полями, обрезкой и разворотами для отправки в типографию.'''
    cors = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400',
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors, 'body': ''}

    if event.get('httpMethod') != 'POST':
        return {'statusCode': 405, 'headers': {**cors, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': 'Method not allowed'})}

    body = json.loads(event.get('body') or '{}')
    story = body.get('story')
    fmt   = body.get('format', '20x20')

    if not story or not story.get('spreads'):
        return {'statusCode': 400, 'headers': {**cors, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': 'Передайте объект story'})}

    pdf_bytes = build_pdf(story, fmt)
    pdf_b64   = base64.b64encode(pdf_bytes).decode('utf-8')

    return {
        'statusCode': 200,
        'headers': {
            **cors,
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="photobook_{fmt}.pdf"',
            'X-Base64': 'true',
        },
        'body': pdf_b64,
        'isBase64Encoded': True,
    }
