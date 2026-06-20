"""
image_finder.py — توليد بطاقة (card) PNG بـ Pillow.

نص البطاقة بالإنجليزية عمداً لتفادي مشاكل تشكيل العربية واتجاهها مع خط
DejaVu. لا نضع إيموجي على البطاقة لأن DejaVu لا يدعمها (تظهر مربعات).

تُعيد دالة generate_card مسار ملف PNG مؤقت، أو None عند الفشل (يكمل البوت
بدون صورة).
"""

import os
import tempfile

import config

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover - Pillow قد لا يكون مثبّتاً وقت الاختبار
    Image = ImageDraw = ImageFont = None


# أبعاد البطاقة.
_WIDTH = 1200
_HEIGHT = 630

# ألوان الهوية البصرية.
_BG_TOP = (15, 23, 42)        # slate-900
_BG_BOTTOM = (49, 46, 129)    # indigo-900
_ACCENT = (129, 140, 248)     # indigo-400
_TEXT = (241, 245, 249)       # slate-100
_MUTED = (148, 163, 184)      # slate-400

# مسارات خطوط DejaVu المحتملة على لينكس.
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
_FONT_REGULAR_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]


def _load_font(size: int, bold: bool = True):
    """تحميل خط DejaVu بالحجم المطلوب، مع رجوع للخط الافتراضي عند الفشل."""
    candidates = _FONT_CANDIDATES if bold else _FONT_REGULAR_CANDIDATES
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _gradient_background():
    """إنشاء خلفية متدرّجة عمودية بين لونين."""
    base = Image.new("RGB", (_WIDTH, _HEIGHT), _BG_TOP)
    draw = ImageDraw.Draw(base)
    top, bottom = _BG_TOP, _BG_BOTTOM
    for y in range(_HEIGHT):
        ratio = y / _HEIGHT
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        draw.line([(0, y), (_WIDTH, y)], fill=(r, g, b))
    return base


def _wrap_text(draw, text: str, font, max_width: int) -> list:
    """لفّ النص على عدة أسطر بحيث لا يتجاوز كل سطر max_width بكسل."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_card(title: str, label: str = "AI Daily Digest"):
    """
    توليد بطاقة PNG.

    title: العنوان (إنجليزي) يُلفّ على عدة أسطر.
    label: شارة علوية صغيرة (مثل 'Paper of the Day').

    تُعيد مسار ملف PNG مؤقت، أو None عند الفشل.
    """
    if Image is None:
        print("[image] مكتبة Pillow غير متوفرة — تخطّي البطاقة.")
        return None

    try:
        img = _gradient_background()
        draw = ImageDraw.Draw(img)

        margin = 80
        max_text_width = _WIDTH - 2 * margin

        # شريط علوي ملوّن.
        draw.rectangle([(0, 0), (_WIDTH, 12)], fill=_ACCENT)

        # الشارة العلوية (label).
        label_font = _load_font(34, bold=True)
        draw.text((margin, 70), label.upper(), font=label_font, fill=_ACCENT)

        # العنوان الرئيسي.
        title = (title or "Neural Digest").strip()
        title_font = _load_font(58, bold=True)
        lines = _wrap_text(draw, title, title_font, max_text_width)
        # نحدّ عدد الأسطر بأربعة مع إضافة "..." إن زاد.
        if len(lines) > 4:
            lines = lines[:4]
            lines[-1] = lines[-1].rstrip(".") + "..."

        y = 170
        line_height = 78
        for line in lines:
            draw.text((margin, y), line, font=title_font, fill=_TEXT)
            y += line_height

        # خط فاصل سفلي.
        footer_y = _HEIGHT - 110
        draw.line(
            [(margin, footer_y), (_WIDTH - margin, footer_y)], fill=_MUTED, width=2
        )

        # تذييل: الهوية + رابط القناة (إنجليزي فقط).
        brand_font = _load_font(36, bold=True)
        url_font = _load_font(32, bold=False)
        draw.text(
            (margin, footer_y + 25), "Neural Digest", font=brand_font, fill=_TEXT
        )

        url_text = config.CHANNEL_URL
        bbox = draw.textbbox((0, 0), url_text, font=url_font)
        url_w = bbox[2] - bbox[0]
        draw.text(
            (_WIDTH - margin - url_w, footer_y + 28),
            url_text,
            font=url_font,
            fill=_MUTED,
        )

        # حفظ في ملف مؤقت.
        fd, path = tempfile.mkstemp(prefix="neural_card_", suffix=".png")
        os.close(fd)
        img.save(path, "PNG")
        return path
    except Exception as exc:
        print(f"[image] خطأ في توليد البطاقة: {exc}")
        return None
