"""
config.py — تحميل متغيرات البيئة والثوابت العامة لمشروع Neural Digest.

كل المفاتيح الحساسة تُقرأ من متغيرات البيئة فقط (أو من ملف .env محلياً عبر
python-dotenv). لا يوجد أي مفتاح مكتوب داخل الكود.
"""

import os
from zoneinfo import ZoneInfo

try:
    # تحميل ملف .env إن وُجد محلياً. على GitHub Actions لا يوجد .env
    # والمتغيرات تأتي من الـ secrets، لذا لا مشكلة إن لم يوجد الملف.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # python-dotenv غير مثبّت أو فشل التحميل — نكمل بالاعتماد على بيئة النظام.
    pass


# ---------------------------------------------------------------------------
# المفاتيح الحساسة (من البيئة فقط)
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@DailyNeural_AI")


# ---------------------------------------------------------------------------
# الثوابت العامة
# ---------------------------------------------------------------------------
# المنطقة الزمنية المحلية المستخدمة في وضع auto.
TIMEZONE = ZoneInfo("Asia/Damascus")

# اسم القناة المعروض (للهوية البصرية والهاشتاغات).
CHANNEL_HANDLE = "@DailyNeural_AI"
CHANNEL_URL = "t.me/DailyNeural_AI"

# موديل Groq المستخدم للترجمة/التبسيط والتوليد.
GROQ_MODEL = "llama-3.3-70b-versatile"

# مصادر arXiv: التصنيفات المطلوبة، الأحدث أولاً.
ARXIV_CATEGORIES = ["cs.AI", "cs.LG"]
ARXIV_API_URL = "http://export.arxiv.org/api/query"

# مصادر RSS للأخبار.
RSS_FEEDS = [
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {
        "name": "MIT Technology Review (AI)",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    },
    {
        "name": "The Batch (deeplearning.ai)",
        "url": "https://www.deeplearning.ai/the-batch/feed/",
    },
]

# حدود تلجرام.
TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_MESSAGE_LIMIT = 4096

# حد أقصى لعدد العناصر المحفوظة في كل قائمة dedup.
STORE_MAX_ITEMS = 250

# مسار ملف الحالة.
STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "store.json")

# مهلة الطلبات الشبكية (بالثواني).
HTTP_TIMEOUT = 20


def validate() -> list:
    """
    تتحقق من وجود المفاتيح الحساسة المطلوبة للنشر الفعلي.
    تُعيد قائمة بأسماء المتغيرات الناقصة (فارغة إذا كل شيء سليم).

    لا ترفع استثناءً — المنادي يقرر ماذا يفعل (في وضع dry-run نتجاهل النقص).
    """
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not TELEGRAM_CHANNEL_ID:
        missing.append("TELEGRAM_CHANNEL_ID")
    return missing
