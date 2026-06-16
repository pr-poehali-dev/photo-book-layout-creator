import json
import base64
import io
import os
import urllib.request
import tempfile
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FORMATS = {
    '20x20': (200, 200),
    '30x20': (300, 200),
    '21x29': (210, 297),
    '30x30': (300, 300),
}

BLEED = 3
SAFE  = 5

FONT_URLS = {
    'DejaVu':       'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf',
    'DejaVu-Bold':  'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf',
    'DejaVu-Oblique': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Oblique.ttf',
}

_fonts_loaded = False

def load_fonts():
    global _fonts_loaded
    if _fonts_loaded:
        return
    tmp = tempfile.gettempdir()
    for name, url in FONT_URLS.items():
        path = os.path.join(tmp, f'{name}.ttf')
        if not os.path.exists(path):
            urllib.request.urlretrieve(url, path)
        pdfmetrics.registerFont(TTFont(name, path))
    _fonts_loaded = True


def _draw_wrapped(c, text, x, y, max_w, font_size, font, color, align='left', page_w=None):
    c.setFont(font, font_size)
    c.setFillColor(color)
    words = str(text).split()
    line = ''
    line_h = font_size * 1.5
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
    for ln in lines:
        lw = c.stringWidth(ln, font, font_size)
        if align == 'center' and page_w:
            draw_x = x + (max_w - lw) / 2
        else:
            draw_x = x
        c.drawString(draw_x, cur_y, ln)
        cur_y -= line_h
        if cur_y < SAFE * mm:
            break


def draw_page(c, pw, ph, spread_num, heading, caption, text, is_right=False):
    bleed = BLEED * mm
    safe  = SAFE  * mm
    text_x = safe + bleed
    text_w = pw - 2 * (safe + bleed)

    # Фон
    c.setFillColor(colors.HexColor('#0c0a18'))
    c.rect(0, 0, pw, ph, fill=1, stroke=0)

    # Декор-полосы сверху
    c.setFillColor(colors.HexColor('#F4622A'))
    c.rect(0, ph - 6 * mm, pw, 6 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#6C5CE7'))
    c.rect(0, ph - 12 * mm, pw, 6 * mm, fill=1, stroke=0)

    # Место под фото
    photo_x = text_x
    photo_y = ph * 0.35
    photo_w = text_w
    photo_h = ph * 0.43
    c.setFillColor(colors.HexColor('#1a1730'))
    c.roundRect(photo_x, photo_y, photo_w, photo_h, 8 * mm, fill=1, stroke=0)
    c.setLineWidth(0.6 * mm)
    c.setStrokeColor(colors.HexColor('#ffffff25'))
    cx = photo_x + photo_w / 2
    cy = photo_y + photo_h / 2
    c.roundRect(cx - 18 * mm, cy - 12 * mm, 36 * mm, 24 * mm, 3 * mm, fill=0, stroke=1)

    # Метки обрезки
    mark = 5 * mm
    gap  = 2 * mm
    c.setStrokeColor(colors.HexColor('#888888'))
    c.setLineWidth(0.2 * mm)
    for x, y in [(bleed, bleed), (pw - bleed, bleed), (bleed, ph - bleed), (pw - bleed, ph - bleed)]:
        sx = 1 if x == bleed else -1
        sy = 1 if y == bleed else -1
        c.line(x + sx * gap, y, x + sx * (gap + mark), y)
        c.line(x, y + sy * gap, x, y + sy * (gap + mark))

    # Линия безопасной зоны
    c.setStrokeColor(colors.HexColor('#ffffff10'))
    c.setLineWidth(0.2 * mm)
    c.rect(bleed, bleed, pw - 2 * bleed, ph - 2 * bleed, fill=0, stroke=1)

    # Номер разворота
    side = 'П' if is_right else 'Л'
    c.setFillColor(colors.HexColor('#ffffff35'))
    c.setFont('DejaVu', 6)
    c.drawString(text_x, safe + bleed, f'Разворот {spread_num} · {side}')

    # Заголовок
    _draw_wrapped(c, heading, text_x, photo_y - 8 * mm, text_w, 13, 'DejaVu-Bold',
                  colors.white, align='center', page_w=pw)

    # Основной текст
    _draw_wrapped(c, text, text_x, photo_y - 24 * mm, text_w, 8.5, 'DejaVu',
                  colors.HexColor('#ffffffbb'))

    # Подпись-капшн
    _draw_wrapped(c, caption, text_x, safe + bleed + 14 * mm, text_w, 8, 'DejaVu-Oblique',
                  colors.HexColor('#F4E070'))


def build_pdf(story: dict, fmt: str) -> bytes:
    load_fonts()

    page_w_mm, page_h_mm = FORMATS.get(fmt, FORMATS['20x20'])
    pw = (page_w_mm + 2 * BLEED) * mm
    ph = (page_h_mm + 2 * BLEED) * mm
    bleed = BLEED * mm
    safe  = SAFE  * mm
    text_x = safe + bleed
    text_w = pw - 2 * (safe + bleed)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(pw, ph))
    title = story.get('title', 'Фотокнига')
    c.setTitle(title)

    spreads = story.get('spreads', [])

    # Обложка
    c.setFillColor(colors.HexColor('#0c0a18'))
    c.rect(0, 0, pw, ph, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#F4622A'))
    c.rect(0, ph - 8 * mm, pw, 8 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#6C5CE7'))
    c.rect(0, ph - 16 * mm, pw, 8 * mm, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont('DejaVu-Bold', 20)
    tw = c.stringWidth(title, 'DejaVu-Bold', 20)
    c.drawString((pw - tw) / 2, ph / 2 + 12 * mm, title)

    intro = story.get('intro', '')
    _draw_wrapped(c, intro, text_x, ph / 2 - 4 * mm, text_w, 9, 'DejaVu',
                  colors.HexColor('#ffffffcc'))

    c.setFont('DejaVu', 7)
    c.setFillColor(colors.HexColor('#ffffff40'))
    note = f'Формат {fmt.replace("x", "×")} см · Вылет {BLEED}мм · Безопасная зона {SAFE}мм'
    c.drawString(text_x, safe + bleed, note)
    c.showPage()

    # Развороты
    for i, spread in enumerate(spreads):
        heading = spread.get('heading', '')
        caption = spread.get('caption', '')
        body    = spread.get('text', '')

        draw_page(c, pw, ph, i + 1, heading, caption, body, is_right=False)
        c.showPage()
        draw_page(c, pw, ph, i + 1, heading, caption, body, is_right=True)
        c.showPage()

    # Задняя обложка
    c.setFillColor(colors.HexColor('#0c0a18'))
    c.rect(0, 0, pw, ph, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#6C5CE7'))
    c.rect(0, 0, pw, 8 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#F4622A'))
    c.rect(0, 8 * mm, pw, 8 * mm, fill=1, stroke=0)
    c.setFont('DejaVu', 9)
    c.setFillColor(colors.HexColor('#ffffff50'))
    tagline = 'Создано с любовью'
    tw = c.stringWidth(tagline, 'DejaVu', 9)
    c.drawString((pw - tw) / 2, ph / 2, tagline)
    c.showPage()

    c.save()
    return buf.getvalue()


def handler(event: dict, context) -> dict:
    '''Собирает PDF-макет фотокниги с кириллицей, полями, обрезкой и разворотами для типографии.'''
    cors = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400',
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors, 'body': ''}

    if event.get('httpMethod') != 'POST':
        return {'statusCode': 405, 'headers': {**cors, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})}

    try:
        body  = json.loads(event.get('body') or '{}')
        story = body.get('story')
        fmt   = body.get('format', '20x20')

        if not story or not story.get('spreads'):
            return {'statusCode': 400, 'headers': {**cors, 'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Передайте объект story'})}

        pdf_bytes = build_pdf(story, fmt)
        pdf_b64   = base64.b64encode(pdf_bytes).decode('utf-8')

        return {
            'statusCode': 200,
            'headers': {
                **cors,
                'Content-Type': 'application/pdf',
                'Content-Disposition': f'attachment; filename="photobook_{fmt}.pdf"',
            },
            'body': pdf_b64,
            'isBase64Encoded': True,
        }
    except Exception as e:
        import traceback
        print(f'[ERROR] {e}\n{traceback.format_exc()}')
        return {'statusCode': 500, 'headers': {**cors, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': str(e)})}
