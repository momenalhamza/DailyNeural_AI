# 🧠 Neural Digest

بوت تلجرام ينشر محتوى **AI تعليمي يومي** بشكل أوتوماتيك على قناة [@DailyNeural_AI](https://t.me/DailyNeural_AI) — المصطلحات التقنية بالإنجليزية والشرح بالعربية. يعمل بالكامل عبر **GitHub Actions** بدون أي سيرفر، وكل مصادره مجانية 100%.

---

## ✨ المميزات

- **أوراق arXiv** (تصنيفات `cs.AI` و `cs.LG`، الأحدث أولاً) مشروحة بالعربي.
- **أخبار AI** من VentureBeat و MIT Technology Review و The Batch.
- **مفاهيم تقنية** مستخرجة تلقائياً من سياق المحتوى اليومي.
- **ملخص أسبوعي** + استفتاء Quiz تفاعلي.
- **بطاقات صور** مولّدة بـ Pillow (بلا صور خارجية).
- **منع التكرار** عبر `data/store.json` يُحفظ تلقائياً بعد كل تشغيل.
- ترجمة وتبسيط وتوليد عبر **Groq** (موديل `llama-3.3-70b-versatile`).

---

## 🏗️ البنية

```
DailyNeural_AI/
├── main.py            # نقطة الدخول + الأوضاع (argparse)
├── config.py          # تحميل .env + الثوابت + validate()
├── store.py           # منع التكرار على JSON
├── fetcher.py         # جلب arXiv + RSS مع تخطّي المنشور سابقاً
├── ai_processor.py    # دوال Groq (شرح/مفهوم/كويز/ملخص)
├── image_finder.py    # توليد بطاقة PNG بـ Pillow
├── publisher.py       # النشر على تلجرام (HTML + Poll)
├── data/store.json    # حالة المنشورات
├── requirements.txt
├── .env.example
└── .github/workflows/digest.yml
```

---

## 🚀 الأوضاع (modes)

| الوضع | الوصف |
|-------|-------|
| `paper`   | 📄 أحدث ورقة arXiv مشروحة + بطاقة |
| `news`    | 🔥 أهم خبر RSS مشروح + بطاقة |
| `concept` | 💡 مفهوم تقني مستخرج من السياق + بطاقة |
| `digest`  | منشور مجمّع (ورقة + خبر + مفهوم) |
| `weekly`  | 📊 ملخص أسبوعي + استفتاء Quiz |
| `auto`    | يختار حسب الوقت المحلي (Asia/Damascus) |
| `test`    | يشغّل كل الأوضاع في وضع dry-run (طباعة فقط) |

منطق `auto`: قبل 12ظ → `paper`، 12–6م → `news`، بعد 6م → `concept`، الجمعة مساءً → `weekly`.

---

## 🧪 التشغيل محلياً

```bash
# 1) ثبّت الاعتماديات
pip install -r requirements.txt

# 2) جهّز المفاتيح
cp .env.example .env
# ثم عدّل .env وأضف مفاتيحك الحقيقية

# 3) جرّب بدون نشر فعلي
python main.py --mode test
python main.py --mode paper --dry-run

# 4) نشر فعلي (يتطلب مفاتيح صحيحة)
python main.py --mode auto
```

> `--dry-run` يطبع المنشور على الكونسول بدل النشر الفعلي.

---

## ⚙️ النشر على GitHub Actions

1. ادفع المشروع إلى مستودع GitHub على فرع `main`.
2. أضف الـ Secrets المطلوبة (انظر القسم التالي).
3. الـ workflow يعمل تلقائياً حسب جدول الـ cron، أو شغّله يدوياً من تبويب **Actions**.

مواعيد cron (بتوقيت UTC، والتعليق يوضح التوقيت المحلي لدمشق):

| UTC | دمشق |
|-----|------|
| `0 6 * * *`  | 09:00 ص |
| `0 11 * * *` | 02:00 ظ |
| `0 17 * * *` | 08:00 م |

> ملاحظة: مواعيد GitHub cron قد تتأخر بضع دقائق أحياناً — هذا طبيعي.

---

## 🔐 الـ Secrets المطلوبة

في GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| الاسم | القيمة |
|-------|--------|
| `TELEGRAM_BOT_TOKEN`  | توكن البوت من @BotFather |
| `GROQ_API_KEY`        | مفتاح Groq من console.groq.com |
| `TELEGRAM_CHANNEL_ID` | `@DailyNeural_AI` |

> لا ترفع ملف `.env` أبداً — هو مُستثنى في `.gitignore`.

> يجب جعل البوت **أدمن** في القناة مع صلاحية النشر (Post Messages).

---

## 📄 الترخيص

مفتوح للاستخدام التعليمي. كل المصادر مجانية.