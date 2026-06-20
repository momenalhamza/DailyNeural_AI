"""
publisher.py — النشر على تلجرام بـ parse_mode=HTML واستفتاء Quiz.

نعالج حدود تلجرام:
- caption الصورة ≤ 1024 حرف.
- الرسالة النصية ≤ 4096 حرف.
- لو النص أطول من حد الـ caption: نرسل الصورة (بـ caption قصير) ثم النص كرسالة منفصلة.

كل الدوال async لأن python-telegram-bot (>=21) واجهته async.
في وضع dry-run يطبع المنشور على الكونسول بدل النشر الفعلي.
"""

import html

import config

try:
    from telegram import Bot
    from telegram.constants import ParseMode, PollType
    from telegram.error import TelegramError
except Exception:  # pragma: no cover - python-telegram-bot قد لا يكون مثبّتاً
    Bot = None
    ParseMode = None
    PollType = None
    TelegramError = Exception


def escape(text: str) -> str:
    """تهريب أحرف HTML الخاصة (أأمن من MarkdownV2)."""
    return html.escape(text or "")


def _bot():
    """إنشاء كائن Bot. يُعيد None إن لم تتوفر المكتبة أو التوكن."""
    if Bot is None:
        print("[publisher] مكتبة python-telegram-bot غير متوفرة.")
        return None
    if not config.TELEGRAM_BOT_TOKEN:
        print("[publisher] TELEGRAM_BOT_TOKEN غير موجود.")
        return None
    try:
        return Bot(token=config.TELEGRAM_BOT_TOKEN)
    except Exception as exc:
        print(f"[publisher] تعذّر إنشاء Bot: {exc}")
        return None


async def publish_post(text: str, image_path: str = None, dry_run: bool = False) -> bool:
    """
    نشر منشور نصي (HTML) مع صورة بطاقة اختيارية.

    منطق الحدود:
    - لا توجد صورة: أرسل رسالة نصية (مقصوصة عند 4096).
    - توجد صورة والنص ≤ 1024: أرسل صورة بـ caption.
    - توجد صورة والنص > 1024: أرسل الصورة بـ caption قصير ثم النص كرسالة منفصلة.

    تُعيد True عند النجاح (أو في dry-run)، False عند الفشل.
    """
    if dry_run:
        print("\n" + "=" * 60)
        print(f"[DRY-RUN] القناة: {config.TELEGRAM_CHANNEL_ID}")
        if image_path:
            print(f"[DRY-RUN] صورة بطاقة: {image_path}")
        print("-" * 60)
        # نطبع النص بدون وسوم HTML لسهولة القراءة في الكونسول.
        import re

        print(re.sub(r"<[^>]+>", "", text))
        print("=" * 60 + "\n")
        return True

    bot = _bot()
    if bot is None:
        return False

    chat_id = config.TELEGRAM_CHANNEL_ID
    try:
        if image_path and len(text) <= config.TELEGRAM_CAPTION_LIMIT:
            with open(image_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                )
        elif image_path:
            # النص أطول من حد الـ caption: صورة بـ caption قصير ثم نص منفصل.
            short_caption = "🧠 AI Daily Digest"
            with open(image_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=short_caption,
                    parse_mode=ParseMode.HTML,
                )
            await bot.send_message(
                chat_id=chat_id,
                text=text[: config.TELEGRAM_MESSAGE_LIMIT],
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=text[: config.TELEGRAM_MESSAGE_LIMIT],
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        return True
    except TelegramError as exc:
        print(f"[publisher] خطأ تلجرام أثناء النشر: {exc}")
        return False
    except OSError as exc:
        print(f"[publisher] خطأ في قراءة ملف الصورة: {exc}")
        return False


async def publish_quiz(quiz: dict, dry_run: bool = False) -> bool:
    """
    نشر استفتاء من نوع Quiz (send_poll type=quiz).

    quiz: {"question", "options"[4], "correct_index", "explanation"}.
    تُعيد True عند النجاح (أو في dry-run)، False عند الفشل.
    """
    if dry_run:
        print("\n" + "=" * 60)
        print("[DRY-RUN] استفتاء Quiz:")
        print(f"  السؤال: {quiz.get('question')}")
        for i, opt in enumerate(quiz.get("options", [])):
            marker = "✓" if i == quiz.get("correct_index") else " "
            print(f"   [{marker}] {opt}")
        print(f"  الشرح: {quiz.get('explanation')}")
        print("=" * 60 + "\n")
        return True

    bot = _bot()
    if bot is None:
        return False

    try:
        # تلجرام يحدّ شرح الاستفتاء بـ 200 حرف.
        explanation = (quiz.get("explanation") or "")[:200]
        await bot.send_poll(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            question=quiz.get("question", "")[:300],
            options=[o[:100] for o in quiz.get("options", [])][:10],
            type=PollType.QUIZ,
            correct_option_id=int(quiz.get("correct_index", 0)),
            explanation=explanation,
            is_anonymous=True,
        )
        return True
    except TelegramError as exc:
        print(f"[publisher] خطأ تلجرام أثناء نشر الاستفتاء: {exc}")
        return False
    except Exception as exc:
        print(f"[publisher] خطأ غير متوقع أثناء نشر الاستفتاء: {exc}")
        return False
