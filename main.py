"""
main.py — نقطة الدخول لمشروع Neural Digest.

الأوضاع (modes):
  paper    📄 ورقة اليوم (أحدث ورقة arXiv مشروحة + بطاقة)
  news     🔥 خبر اليوم (أهم خبر RSS مشروح + بطاقة)
  concept  💡 مفهوم اليوم (مصطلح مستخرج من سياق ورقة/خبر + بطاقة)
  digest   منشور مجمّع (ورقة + خبر + مفهوم)
  weekly   📊 ملخص أسبوعي + استفتاء Quiz
  auto     يختار الوضع حسب الوقت المحلي (Asia/Damascus)
  test     يشغّل كل الأوضاع في وضع dry-run

الاستخدام:
  python main.py --mode auto
  python main.py --mode paper --dry-run
"""

import argparse
import asyncio
from datetime import datetime

import config
import store as store_module
from ai_processor import (
    explain_news,
    explain_paper,
    extract_concept,
    generate_quiz,
    generate_weekly_summary,
)
from fetcher import fetch_latest_paper, fetch_top_news
from image_finder import generate_card
from publisher import escape, publish_post, publish_quiz

# أسماء الأشهر العربية للتاريخ.
_AR_MONTHS = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

_HASHTAGS = "#AI #MachineLearning #ذكاء_اصطناعي #تعلم_آلي #DeepLearning"
_FOOTER = f"📢 {config.CHANNEL_HANDLE}"


def arabic_date(now: datetime = None) -> str:
    """تاريخ اليوم بصيغة عربية: 'يوم شهر سنة'."""
    now = now or datetime.now(config.TIMEZONE)
    return f"{now.day} {_AR_MONTHS[now.month - 1]} {now.year}"


def _header() -> str:
    return (
        f"🧠 <b>AI Daily Digest</b> | {arabic_date()}\n"
        "━━━━━━━━━━━━━━━━━━"
    )


def _footer_block() -> str:
    return f"\n{_HASHTAGS}\n{_FOOTER}"


# ---------------------------------------------------------------------------
# بناء المنشورات لكل وضع
# ---------------------------------------------------------------------------
def build_paper_post(store):
    """يبني منشور ورقة اليوم. يُعيد (text, image_path, paper) أو (None, None, None)."""
    paper = fetch_latest_paper(store)
    if not paper:
        return None, None, None

    explanation = explain_paper(paper)
    text = (
        f"{_header()}\n\n"
        f"📄 <b>ورقة اليوم:</b> {escape(paper['title'])}\n"
        f"↳ {escape(explanation)}\n\n"
        f"🔗 <a href=\"{escape(paper['link'])}\">اقرأ الورقة على arXiv</a>"
        f"{_footer_block()}"
    )
    image_path = generate_card(paper["title"], label="Paper of the Day")
    return text, image_path, paper


def build_news_post(store):
    """يبني منشور خبر اليوم. يُعيد (text, image_path, news) أو (None, None, None)."""
    news = fetch_top_news(store)
    if not news:
        return None, None, None

    explanation = explain_news(news)
    text = (
        f"{_header()}\n\n"
        f"🔥 <b>خبر اليوم:</b> {escape(news['title'])}\n"
        f"↳ {escape(explanation)}\n\n"
        f"📰 المصدر: {escape(news['source'])}\n"
        f"🔗 <a href=\"{escape(news['link'])}\">الرابط الأصلي</a>"
        f"{_footer_block()}"
    )
    image_path = generate_card(news["title"], label="News of the Day")
    return text, image_path, news


def build_concept_post(store):
    """
    يبني منشور مفهوم اليوم من سياق أحدث ورقة/خبر.
    يُعيد (text, image_path, concept) أو (None, None, None).
    """
    paper = fetch_latest_paper(store)
    news = fetch_top_news(store)
    context_parts = []
    if paper:
        context_parts.append(f"{paper['title']}. {paper['summary']}")
    if news:
        context_parts.append(f"{news['title']}. {news['summary']}")
    context = "\n".join(context_parts)

    concept = extract_concept(context)
    text = (
        f"{_header()}\n\n"
        f"💡 <b>مفهوم اليوم:</b> {escape(concept['term'])}\n"
        f"↳ {escape(concept['explanation'])}"
        f"{_footer_block()}"
    )
    image_path = generate_card(concept["term"], label="Concept of the Day")
    return text, image_path, concept


def build_digest_post(store):
    """
    يبني منشوراً مجمّعاً (ورقة + خبر + مفهوم) في بوست واحد.
    يُعيد (text, image_path, refs) — refs قاموس بالعناصر المستخدمة للـ dedup.
    """
    paper = fetch_latest_paper(store)
    news = fetch_top_news(store)

    context_parts = []
    if paper:
        context_parts.append(f"{paper['title']}. {paper['summary']}")
    if news:
        context_parts.append(f"{news['title']}. {news['summary']}")
    concept = extract_concept("\n".join(context_parts)) if context_parts else None

    blocks = [_header()]

    if paper:
        blocks.append(
            f"📄 <b>ورقة اليوم:</b> {escape(paper['title'])}\n"
            f"↳ {escape(explain_paper(paper))}\n"
            f"🔗 <a href=\"{escape(paper['link'])}\">arXiv</a>"
        )
    if news:
        blocks.append(
            f"🔥 <b>خبر اليوم:</b> {escape(news['title'])}\n"
            f"↳ {escape(explain_news(news))}\n"
            f"📰 {escape(news['source'])} — "
            f"<a href=\"{escape(news['link'])}\">الرابط</a>"
        )
    if concept:
        blocks.append(
            f"💡 <b>مفهوم اليوم:</b> {escape(concept['term'])}\n"
            f"↳ {escape(concept['explanation'])}"
        )

    if not paper and not news:
        return None, None, None

    text = "\n\n".join(blocks) + _footer_block()
    card_title = paper["title"] if paper else (news["title"] if news else "Neural Digest")
    image_path = generate_card(card_title, label="AI Daily Digest")
    refs = {"paper": paper, "news": news, "concept": concept}
    return text, image_path, refs


# ---------------------------------------------------------------------------
# مشغّلات الأوضاع (async)
# ---------------------------------------------------------------------------
async def run_paper(store, dry_run):
    text, image, paper = build_paper_post(store)
    if not text:
        print("[main] لا توجد ورقة جديدة للنشر.")
        return False
    ok = await publish_post(text, image, dry_run=dry_run)
    if ok and not dry_run and paper:
        store_module.mark_seen(store, "papers", paper["id"])
        store_module.add_history(store, {"kind": "paper", "title": paper["title"]})
    return ok


async def run_news(store, dry_run):
    text, image, news = build_news_post(store)
    if not text:
        print("[main] لا يوجد خبر جديد للنشر.")
        return False
    ok = await publish_post(text, image, dry_run=dry_run)
    if ok and not dry_run and news:
        store_module.mark_seen(store, "news", news["link"])
        store_module.add_history(store, {"kind": "news", "title": news["title"]})
    return ok


async def run_concept(store, dry_run):
    text, image, concept = build_concept_post(store)
    if not text:
        print("[main] تعذّر بناء منشور المفهوم.")
        return False
    ok = await publish_post(text, image, dry_run=dry_run)
    if ok and not dry_run and concept:
        store_module.add_history(
            store, {"kind": "concept", "title": concept["term"]}
        )
    return ok


async def run_digest(store, dry_run):
    text, image, refs = build_digest_post(store)
    if not text:
        print("[main] لا يوجد محتوى كافٍ للمنشور المجمّع.")
        return False
    ok = await publish_post(text, image, dry_run=dry_run)
    if ok and not dry_run and refs:
        if refs.get("paper"):
            store_module.mark_seen(store, "papers", refs["paper"]["id"])
            store_module.add_history(
                store, {"kind": "paper", "title": refs["paper"]["title"]}
            )
        if refs.get("news"):
            store_module.mark_seen(store, "news", refs["news"]["link"])
            store_module.add_history(
                store, {"kind": "news", "title": refs["news"]["title"]}
            )
    return ok


async def run_weekly(store, dry_run):
    summary = generate_weekly_summary(store.get("history", []))
    text = (
        f"📊 <b>الملخص الأسبوعي</b> | {arabic_date()}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{escape(summary)}"
        f"{_footer_block()}"
    )
    ok_post = await publish_post(text, None, dry_run=dry_run)

    # استفتاء Quiz من سياق آخر العناوين.
    context = " ".join(h.get("title", "") for h in store.get("history", [])[-10:])
    quiz = generate_quiz(context)
    ok_quiz = await publish_quiz(quiz, dry_run=dry_run)
    return ok_post and ok_quiz


async def run_test(store):
    """تشغيل كل الأوضاع في وضع dry-run (طباعة فقط)."""
    print("\n########## وضع الاختبار: تشغيل كل الأوضاع (dry-run) ##########\n")
    for label, fn in (
        ("paper", run_paper),
        ("news", run_news),
        ("concept", run_concept),
        ("digest", run_digest),
    ):
        print(f"\n----- اختبار وضع: {label} -----")
        try:
            await fn(store, dry_run=True)
        except Exception as exc:
            print(f"[test] فشل وضع {label}: {exc}")

    print("\n----- اختبار وضع: weekly -----")
    try:
        await run_weekly(store, dry_run=True)
    except Exception as exc:
        print(f"[test] فشل وضع weekly: {exc}")
    print("\n########## انتهى الاختبار ##########\n")


def resolve_auto_mode(now: datetime = None) -> str:
    """
    اختيار الوضع حسب الوقت المحلي (Asia/Damascus):
      - الجمعة مساءً (بعد 6م) → weekly
      - قبل 12 ظهراً        → paper
      - 12 حتى 6 مساءً      → news
      - بعد 6 مساءً         → concept
    weekday(): الاثنين=0 ... الجمعة=4 ... الأحد=6
    """
    now = now or datetime.now(config.TIMEZONE)
    hour = now.hour
    is_friday = now.weekday() == 4

    if is_friday and hour >= 18:
        return "weekly"
    if hour < 12:
        return "paper"
    if hour < 18:
        return "news"
    return "concept"


# ---------------------------------------------------------------------------
# التشغيل الرئيسي
# ---------------------------------------------------------------------------
async def dispatch(mode: str, dry_run: bool):
    store = store_module.load()

    if mode == "test":
        await run_test(store)
        # وضع الاختبار لا يحفظ حالة (كله dry-run).
        return

    if mode == "auto":
        mode = resolve_auto_mode()
        print(f"[main] وضع auto اختار: {mode}")

    handlers = {
        "paper": run_paper,
        "news": run_news,
        "concept": run_concept,
        "digest": run_digest,
        "weekly": run_weekly,
    }
    handler = handlers.get(mode)
    if handler is None:
        print(f"[main] وضع غير معروف: {mode}")
        return

    try:
        await handler(store, dry_run=dry_run)
    except Exception as exc:
        print(f"[main] خطأ أثناء تنفيذ الوضع {mode}: {exc}")

    # حفظ الحالة بعد التشغيل الفعلي فقط.
    if not dry_run:
        store_module.save(store)


def main():
    parser = argparse.ArgumentParser(description="Neural Digest — بوت تلجرام لمحتوى AI يومي")
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["paper", "news", "concept", "digest", "weekly", "auto", "test"],
        help="الوضع المطلوب تشغيله (افتراضي: auto)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="طباعة المنشور على الكونسول بدل النشر الفعلي",
    )
    args = parser.parse_args()

    # تحقق من المفاتيح — في dry-run/test نكمل رغم النقص (مع تنبيه).
    missing = config.validate()
    if missing and not (args.dry_run or args.mode == "test"):
        print(f"[main] تحذير: متغيرات بيئة ناقصة: {', '.join(missing)}")
        print("[main] سيحاول البوت المتابعة، لكن النشر الفعلي سيفشل غالباً.")
    elif missing:
        print(f"[main] (dry-run) متغيرات ناقصة (طبيعي محلياً): {', '.join(missing)}")

    asyncio.run(dispatch(args.mode, args.dry_run))


if __name__ == "__main__":
    main()
