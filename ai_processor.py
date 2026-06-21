"""
ai_processor.py — دوال Groq للترجمة/التبسيط بالعربي وتوليد الكويز والملخص.

الموديل: llama-3.3-70b-versatile.
السياسة: عربية فصيحة بسيطة، إبقاء المصطلحات التقنية بالإنجليزية، وبدون مقدمات
مثل "إليك" أو "بالطبع". كل دالة تعالج فشل الشبكة/التحليل بـ fallback ثابت
حتى لا يتعطّل البوت.
"""

import json
import re

import config

try:
    from groq import Groq
except Exception:  # pragma: no cover - groq قد لا يكون مثبّتاً وقت الاختبار
    Groq = None


# توجيه عام يُحقن في كل نداء.
_SYSTEM_PROMPT = (
    "أنت محرّر تقني عربي متخصص في الذكاء الاصطناعي. اكتب بعربية فصيحة بسيطة وواضحة. "
    "أبقِ المصطلحات التقنية بالإنجليزية كما هي (مثل: Transformer, fine-tuning, LLM). "
    "لا تبدأ بمقدمات مثل 'إليك' أو 'بالطبع' أو 'في ما يلي'. ادخل في صلب الموضوع مباشرة. "
    "لا تستخدم تنسيق Markdown."
)


def _client():
    """إنشاء عميل Groq. يُعيد None إن لم تتوفر المكتبة أو المفتاح."""
    if Groq is None:
        print("[ai] مكتبة groq غير متوفرة.")
        return None
    if not config.GROQ_API_KEY:
        print("[ai] مفتاح GROQ_API_KEY غير موجود.")
        return None
    try:
        return Groq(api_key=config.GROQ_API_KEY)
    except Exception as exc:
        print(f"[ai] تعذّر إنشاء عميل Groq: {exc}")
        return None


def _chat(prompt: str, temperature: float = 0.5, max_tokens: int = 700):
    """
    نداء محادثة واحد إلى Groq. يُعيد النص الناتج أو None عند الفشل.
    """
    client = _client()
    if client is None:
        return None
    try:
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"[ai] خطأ في نداء Groq: {exc}")
        return None


def _strip_intro(text: str) -> str:
    """إزالة أي مقدمات شائعة قد يبدأ بها الموديل رغم التوجيه."""
    if not text:
        return text
    text = text.strip()
    intros = ("إليك", "بالطبع", "في ما يلي", "فيما يلي", "هذه")
    for intro in intros:
        if text.startswith(intro):
            # نحذف حتى أول علامة ترقيم/سطر.
            parts = re.split(r"[:\n]", text, maxsplit=1)
            if len(parts) == 2 and len(parts[0]) < 40:
                text = parts[1].strip()
            break
    return text


def _extract_json(text: str):
    """
    استخراج أول كائن JSON من نص قد يحوي زوائد. يُعيد dict أو None.
    """
    if not text:
        return None
    # إزالة أسوار الكود إن وُجدت.
    text = re.sub(r"```(?:json)?", "", text).strip("` \n")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# الدوال العامة
# ---------------------------------------------------------------------------
def explain_paper(paper: dict) -> str:
    """شرح ورقة arXiv بالعربي في 3-4 جمل."""
    prompt = (
        "اشرح الورقة البحثية التالية بالعربي في 3 إلى 4 جمل واضحة لغير المتخصص، "
        "موضّحاً الفكرة الأساسية وأهميتها العملية.\n\n"
        f"العنوان: {paper.get('title', '')}\n"
        f"الملخص: {paper.get('summary', '')[:1500]}"
    )
    result = _chat(prompt, temperature=0.5, max_tokens=500)
    if not result:
        return "تعذّر توليد الشرح حالياً. اطّلع على الورقة عبر الرابط أدناه."
    return _strip_intro(result)


def explain_paper_deep(paper: dict) -> str:
    """
    شرح معمّق لورقة arXiv بالعربي (6-8 جمل) يغطّي: المشكلة التي تعالجها، الفكرة/المنهج
    الأساسي، لماذا هي مهمة، وأبرز نتيجة أو حدّ من حدودها. أعمق من explain_paper.
    """
    prompt = (
        "اشرح الورقة البحثية التالية بالعربي شرحاً معمّقاً ومترابطاً في 6 إلى 8 جمل، "
        "بحيث يفهمها قارئ مهتم بالذكاء الاصطناعي دون أن يكون متخصصاً. غطِّ بالترتيب: "
        "(1) ما المشكلة التي تعالجها الورقة؟ (2) ما الفكرة أو المنهج الأساسي المقترح؟ "
        "(3) لماذا هذا مهم وما الذي يميّزه عن السابق؟ (4) أبرز نتيجة أو حدّ من حدوده. "
        "اكتب فقرات نثرية متصلة دون عناوين أو ترقيم أو نقاط.\n\n"
        f"العنوان: {paper.get('title', '')}\n"
        f"الملخص: {paper.get('summary', '')[:2000]}"
    )
    result = _chat(prompt, temperature=0.5, max_tokens=900)
    if not result:
        return "تعذّر توليد الشرح المعمّق حالياً. اطّلع على الورقة عبر الرابط أدناه."
    return _strip_intro(result)


def explain_news(news: dict) -> str:
    """شرح خبر RSS بالعربي مع توضيح تأثيره."""
    prompt = (
        "لخّص الخبر التقني التالي بالعربي في جملتين إلى ثلاث، ثم وضّح تأثيره أو "
        "أهميته في مجال الذكاء الاصطناعي في جملة واحدة.\n\n"
        f"العنوان: {news.get('title', '')}\n"
        f"المحتوى: {news.get('summary', '')[:1500]}"
    )
    result = _chat(prompt, temperature=0.5, max_tokens=500)
    if not result:
        return "تعذّر توليد الشرح حالياً. اطّلع على الخبر عبر الرابط أدناه."
    return _strip_intro(result)


def extract_concept(context_text: str) -> dict:
    """
    استخراج مصطلح تقني واحد من سياق نص وشرحه ببساطة.
    تُعيد dict: {"term": str (إنجليزي), "explanation": str (عربي)}.
    عند الفشل تُعيد fallback ثابت.
    """
    fallback = {
        "term": "Neural Network",
        "explanation": (
            "نموذج حاسوبي مستوحى من طريقة عمل الدماغ، يتعلّم من البيانات عبر طبقات "
            "من الوحدات الحسابية (neurons) لاكتشاف الأنماط واتخاذ القرارات."
        ),
    }

    prompt = (
        "من النص التقني التالي، اختر مصطلحاً تقنياً واحداً مهماً في مجال الذكاء "
        "الاصطناعي. أعد فقط كائن JSON بالشكل التالي تماماً دون أي نص إضافي:\n"
        '{"term": "المصطلح بالإنجليزية", "explanation": "شرح مبسّط بالعربي في جملتين"}\n\n'
        f"النص:\n{(context_text or '')[:1500]}"
    )
    result = _chat(prompt, temperature=0.4, max_tokens=400)
    data = _extract_json(result or "")
    if not data or "term" not in data or "explanation" not in data:
        print("[ai] فشل تحليل extract_concept — استخدام fallback.")
        return fallback
    return {
        "term": str(data["term"]).strip(),
        "explanation": _strip_intro(str(data["explanation"]).strip()),
    }


def generate_quiz(context_text: str) -> dict:
    """
    توليد سؤال اختيار من متعدد (Quiz) من سياق نص.
    تُعيد dict: {"question": str, "options": [str x4], "correct_index": int, "explanation": str}.
    كل النصوص بالعربي مع إبقاء المصطلحات بالإنجليزية. عند الفشل تُعيد fallback ثابت.
    """
    fallback = {
        "question": "ماذا يعني مصطلح LLM في مجال الذكاء الاصطناعي؟",
        "options": [
            "Large Language Model",
            "Linear Learning Method",
            "Logical Layer Mapping",
            "Local Linked Memory",
        ],
        "correct_index": 0,
        "explanation": "LLM هو اختصار لـ Large Language Model، أي نموذج لغوي ضخم.",
    }

    prompt = (
        "بناءً على النص التقني التالي، أنشئ سؤال اختيار من متعدد واحداً عن الذكاء "
        "الاصطناعي بأربعة خيارات. أعد فقط كائن JSON بالشكل التالي تماماً دون أي نص "
        "إضافي:\n"
        '{"question": "نص السؤال بالعربي", "options": ["خيار 1", "خيار 2", "خيار 3", '
        '"خيار 4"], "correct_index": 0, "explanation": "شرح قصير للإجابة الصحيحة"}\n'
        "اجعل correct_index رقماً بين 0 و 3 يشير للإجابة الصحيحة.\n\n"
        f"النص:\n{(context_text or '')[:1500]}"
    )
    result = _chat(prompt, temperature=0.5, max_tokens=500)
    data = _extract_json(result or "")

    # تحقق صارم من البنية.
    if (
        not data
        or not isinstance(data.get("options"), list)
        or len(data["options"]) != 4
        or not isinstance(data.get("question"), str)
    ):
        print("[ai] فشل تحليل generate_quiz — استخدام fallback.")
        return fallback

    try:
        correct = int(data.get("correct_index", 0))
    except (TypeError, ValueError):
        correct = 0
    if correct < 0 or correct > 3:
        correct = 0

    return {
        "question": str(data["question"]).strip(),
        "options": [str(o).strip()[:100] for o in data["options"]],
        "correct_index": correct,
        "explanation": _strip_intro(str(data.get("explanation", "")).strip())[:200],
    }


def generate_weekly_summary(history: list) -> str:
    """
    توليد ملخص أسبوعي نصي من سجل المنشورات الأخيرة.
    history: قائمة dicts فيها على الأقل 'title' و 'kind'.
    """
    if not history:
        items_text = "لا توجد منشورات مسجّلة هذا الأسبوع."
    else:
        recent = history[-15:]
        lines = []
        for h in recent:
            kind = h.get("kind", "")
            title = h.get("title", "")
            if title:
                lines.append(f"- ({kind}) {title}")
        items_text = "\n".join(lines) if lines else "لا توجد عناوين."

    prompt = (
        "اكتب ملخصاً أسبوعياً بالعربي لأبرز ما نُشر في قناة عن الذكاء الاصطناعي، "
        "بأسلوب جذّاب ومنظّم في 4 إلى 6 جمل. ركّز على الاتجاهات والمواضيع المشتركة، "
        "لا على تعداد كل عنصر.\n\n"
        f"المنشورات:\n{items_text}"
    )
    result = _chat(prompt, temperature=0.6, max_tokens=600)
    if not result:
        return (
            "هذا الأسبوع تابعنا أحدث أوراق وأخبار الذكاء الاصطناعي. "
            "تابعونا للمزيد من المحتوى التعليمي اليومي."
        )
    return _strip_intro(result)
