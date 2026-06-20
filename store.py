"""
store.py — منع التكرار (dedup) عبر ملف JSON بسيط.

البنية:
{
  "papers":  [arxiv_id, ...],   # معرّفات أوراق arXiv بدون رقم النسخة
  "news":    [url, ...],        # روابط الأخبار المنشورة
  "history": [ {...}, ... ]     # سجل مختصر بآخر المنشورات (للملخص الأسبوعي)
}

نقصّ كل قائمة لآخر STORE_MAX_ITEMS عنصر حتى لا ينمو الملف بلا حدود.
"""

import json
import os

import config


def _empty_store() -> dict:
    return {"papers": [], "news": [], "history": []}


def load() -> dict:
    """تحميل الحالة من القرص. تُعيد بنية فارغة عند أي خطأ."""
    try:
        with open(config.STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # ضمان وجود كل المفاتيح المتوقعة.
        store = _empty_store()
        store.update({k: data.get(k, store[k]) for k in store})
        return store
    except FileNotFoundError:
        return _empty_store()
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[store] تحذير: تعذّر قراءة {config.STORE_PATH} ({exc}) — أبدأ بحالة فارغة.")
        return _empty_store()


def save(store: dict) -> None:
    """حفظ الحالة على القرص مع قصّ القوائم لآخر STORE_MAX_ITEMS عنصر."""
    store = dict(store)
    for key in ("papers", "news", "history"):
        items = store.get(key, [])
        if len(items) > config.STORE_MAX_ITEMS:
            store[key] = items[-config.STORE_MAX_ITEMS:]

    os.makedirs(os.path.dirname(config.STORE_PATH), exist_ok=True)
    try:
        with open(config.STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[store] خطأ: تعذّر حفظ الحالة ({exc}).")


def is_seen(store: dict, kind: str, key: str) -> bool:
    """هل سبق نشر هذا العنصر؟ kind إما 'papers' أو 'news'."""
    if not key:
        return False
    return key in store.get(kind, [])


def mark_seen(store: dict, kind: str, key: str) -> None:
    """تسجيل عنصر كمنشور (يُضاف لنهاية القائمة)."""
    if not key:
        return
    bucket = store.setdefault(kind, [])
    if key not in bucket:
        bucket.append(key)


def add_history(store: dict, entry: dict) -> None:
    """إضافة سجل مختصر بمنشور (للاستفادة منه في الملخص الأسبوعي)."""
    store.setdefault("history", []).append(entry)
