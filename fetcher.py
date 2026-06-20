"""
fetcher.py — جلب أحدث ورقة من arXiv وأهم خبر من خلاصات RSS.

كل دالة تعالج أعطالها بنفسها: عند فشل الشبكة أو التحليل تطبع خطأً واضحاً
وتُعيد None بدل أن تتسبب بانهيار البوت.
"""

import re
import xml.etree.ElementTree as ET

import requests

import config

try:
    import feedparser
except Exception:  # pragma: no cover - feedparser قد لا يكون مثبّتاً وقت الاختبار
    feedparser = None


# مساحات الأسماء في استجابة arXiv (Atom).
_ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

_USER_AGENT = "NeuralDigestBot/1.0 (+https://t.me/DailyNeural_AI)"


def _clean_text(text: str) -> str:
    """تنظيف المسافات الزائدة وفواصل الأسطر من نصوص arXiv."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _normalize_arxiv_id(raw_id: str) -> str:
    """
    استخراج معرّف arXiv بدون رقم النسخة.
    مثال: 'http://arxiv.org/abs/2401.12345v2' -> '2401.12345'
    """
    if not raw_id:
        return ""
    tail = raw_id.rstrip("/").split("/")[-1]
    # إزالة لاحقة النسخة vN
    return re.sub(r"v\d+$", "", tail)


def fetch_latest_paper(store):
    """
    جلب أحدث ورقة من arXiv ضمن التصنيفات المطلوبة، مع تخطّي ما نُشر سابقاً.

    تُعيد dict فيه: id, title, summary, authors, link  أو None عند الفشل/عدم وجود جديد.
    """
    cat_query = "+OR+".join(f"cat:{c}" for c in config.ARXIV_CATEGORIES)
    params = (
        f"search_query={cat_query}"
        "&sortBy=submittedDate&sortOrder=descending"
        "&start=0&max_results=25"
    )
    url = f"{config.ARXIV_API_URL}?{params}"

    try:
        resp = requests.get(
            url, timeout=config.HTTP_TIMEOUT, headers={"User-Agent": _USER_AGENT}
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[fetcher] خطأ في جلب arXiv: {exc}")
        return None

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        print(f"[fetcher] خطأ في تحليل استجابة arXiv: {exc}")
        return None

    entries = root.findall("atom:entry", _ATOM_NS)
    if not entries:
        print("[fetcher] لم تُرجع arXiv أي نتائج.")
        return None

    for entry in entries:
        raw_id = entry.findtext("atom:id", default="", namespaces=_ATOM_NS)
        arxiv_id = _normalize_arxiv_id(raw_id)
        if not arxiv_id:
            continue
        from store import is_seen

        if is_seen(store, "papers", arxiv_id):
            continue

        title = _clean_text(entry.findtext("atom:title", default="", namespaces=_ATOM_NS))
        summary = _clean_text(
            entry.findtext("atom:summary", default="", namespaces=_ATOM_NS)
        )

        authors = [
            _clean_text(a.findtext("atom:name", default="", namespaces=_ATOM_NS))
            for a in entry.findall("atom:author", _ATOM_NS)
        ]
        authors = [a for a in authors if a]

        # رابط الصفحة (نوع text/html إن وُجد، وإلا abs link).
        link = f"https://arxiv.org/abs/{arxiv_id}"
        for link_el in entry.findall("atom:link", _ATOM_NS):
            if link_el.get("rel") == "alternate" and link_el.get("href"):
                link = link_el.get("href")
                break

        return {
            "id": arxiv_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "link": link,
        }

    print("[fetcher] كل أوراق arXiv الأحدث منشورة سابقاً — لا جديد.")
    return None


def fetch_top_news(store):
    """
    جلب أهم خبر (الأحدث) من خلاصات RSS المعرّفة، مع تخطّي الروابط المنشورة سابقاً.

    تُعيد dict فيه: title, summary, link, source  أو None عند الفشل/عدم وجود جديد.
    """
    if feedparser is None:
        print("[fetcher] مكتبة feedparser غير متوفرة — تخطّي الأخبار.")
        return None

    from store import is_seen

    candidates = []
    for feed in config.RSS_FEEDS:
        try:
            parsed = feedparser.parse(
                feed["url"], request_headers={"User-Agent": _USER_AGENT}
            )
        except Exception as exc:  # feedparser نادراً ما يرفع، لكن للأمان
            print(f"[fetcher] خطأ في جلب RSS من {feed['name']}: {exc}")
            continue

        if getattr(parsed, "bozo", 0) and not parsed.entries:
            print(f"[fetcher] تحذير: خلاصة {feed['name']} غير صالحة أو فارغة.")
            continue

        for item in parsed.entries[:10]:
            link = getattr(item, "link", "")
            if not link or is_seen(store, "news", link):
                continue

            summary = getattr(item, "summary", "") or getattr(item, "description", "")
            summary = _clean_text(re.sub(r"<[^>]+>", " ", summary))

            published = getattr(item, "published_parsed", None) or getattr(
                item, "updated_parsed", None
            )

            candidates.append(
                {
                    "title": _clean_text(getattr(item, "title", "")),
                    "summary": summary,
                    "link": link,
                    "source": feed["name"],
                    "_sort": published,
                }
            )
            # نأخذ أول خبر جديد من كل خلاصة فقط (الأحدث).
            break

    if not candidates:
        print("[fetcher] لا يوجد خبر RSS جديد (الكل منشور سابقاً أو فشل الجلب).")
        return None

    # ترتيب حسب تاريخ النشر تنازلياً؛ العناصر بلا تاريخ تذهب للأخير.
    candidates.sort(key=lambda c: c["_sort"] or (0,), reverse=True)
    top = candidates[0]
    top.pop("_sort", None)
    return top
