"""What a Free account gets beyond the daily file quota (2026-10-06, owner decisions).

* **Weekly tries.** Tools that cost money to run, or that used to be Pro-only, can be used once per calendar
  week (Monday 00:00 UTC) without Pro: ``bg`` AI background removal, ``doctor`` Profile Rating, ``dna`` Steam DNA,
  ``loop`` Seamless Loop, ``design`` Design Selection, ``da`` publishing to DeviantArt.
  A use is counted for the account AND for the IP address, and either one being spent blocks the next use:
  the owner chose this so that a second account from the same address does not get a second try.
  The address is stored as a keyed hash, never in the clear.
* **Beta features are Pro-only** (``BETA_FEATURES``, default ``gifopt``). New tools start here.
* **Builder exports:** ``BUILDER_EXPORTS_PER_DAY`` a day (was 1).

Still Pro-only with no free try: Upscale and Steam Check. The daily file quota itself lives in core.quota_state.

Extra tries from the owner (admin user card, 2026-10-09) are a separate row ``+u:<uid>`` per feature and week whose
``used`` column counts the extra tries LEFT. They are spent only after the normal account + address try is gone,
so they also help when the address was used by somebody else first.

A try spent on a job that then fails is given back (``ticket`` in the job payload, ``refund_job`` from
redis_store.job_update), so a server error never costs the user their week.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta, timezone

import auth_db

WEEKLY_FEATURES = ("bg", "doctor", "dna", "loop", "design", "da")
DEFAULT_BETA = "gifopt,aianim"


def weekly_limit() -> int:
    """Uses per week of each weekly tool (FREE_WEEKLY_USES, default 1)."""
    try:
        return max(1, min(50, int(os.environ.get("FREE_WEEKLY_USES") or 1)))
    except ValueError:
        return 1


def builder_exports_per_day() -> int:
    try:
        return max(1, min(100, int(os.environ.get("BUILDER_EXPORTS_PER_DAY") or 3)))
    except ValueError:
        return 3


def beta_features() -> tuple[str, ...]:
    """Feature ids that are in beta and therefore Pro-only. BETA_FEATURES="" switches the list off."""
    raw = os.environ.get("BETA_FEATURES")
    if raw is None:
        raw = DEFAULT_BETA
    return tuple(sorted({part.strip().lower() for part in raw.split(",") if part.strip()}))


def is_beta(feature: str) -> bool:
    return feature in beta_features()


# ---------------------------------------------------------------- the calendar
def _now(now: float | None = None) -> datetime:
    return datetime.fromtimestamp(time.time() if now is None else now, tz=timezone.utc)


def week(now: float | None = None) -> str:
    """ISO week of the moment, e.g. '2026-W41'. It changes on Monday 00:00 UTC."""
    year, number, _weekday = _now(now).isocalendar()
    return f"{year}-W{number:02d}"


def week_resets_at(now: float | None = None) -> float:
    moment = _now(now)
    monday = (moment - timedelta(days=moment.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return (monday + timedelta(days=7)).timestamp()


def day_resets_at(now: float | None = None) -> float:
    moment = _now(now)
    return (moment.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).timestamp()


# ---------------------------------------------------------------- who is counted
def _ip_subject(ip: str) -> str:
    key = (os.environ.get("SECRET_KEY") or "showcasemaker-free-limits").encode("utf-8")
    return "ip:" + hmac.new(key, str(ip or "").encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def subjects(user_id: int | None, ip: str | None) -> list[str]:
    result = []
    if user_id:
        result.append(f"u:{int(user_id)}")
    if ip:
        result.append(_ip_subject(ip))
    return result


def bonus_subject(user_id: int) -> str:
    return f"+u:{int(user_id)}"


def _used(c, feature: str, subject: str, period: str) -> int:
    row = c.execute("SELECT used FROM feature_uses WHERE feature=? AND subject=? AND period=?",
                    (feature, subject, period)).fetchone()
    return int(row["used"] or 0) if row else 0


def left(feature: str, user_id: int | None, ip: str | None, now: float | None = None) -> int:
    """Uses left this week: the smaller of what the account and the address still have."""
    who = subjects(user_id, ip)
    if feature not in WEEKLY_FEATURES or not who:
        return 0
    period, limit = week(now), weekly_limit()
    c = auth_db._conn()
    try:
        bonus = _used(c, feature, bonus_subject(user_id), period) if user_id else 0
        return max(0, min(limit - _used(c, feature, subject, period) for subject in who)) + bonus
    finally:
        c.close()


def consume(feature: str, user_id: int | None, ip: str | None, now: float | None = None) -> bool:
    """Spend one weekly use for the account and the address together, or nothing at all."""
    who = subjects(user_id, ip)
    if feature not in WEEKLY_FEATURES or not who:
        return False
    period, limit, stamp = week(now), weekly_limit(), time.time()
    c = auth_db._conn()
    try:
        # Old weeks are of no use to anybody; the table stays small.
        c.execute("DELETE FROM feature_uses WHERE updated_at<?", (stamp - 60 * 86400,))
        for subject in who:
            cursor = c.execute(
                "INSERT INTO feature_uses (feature, subject, period, used, updated_at) VALUES (?,?,?,1,?) "
                "ON CONFLICT(feature, subject, period) DO UPDATE SET used=feature_uses.used+1, "
                "updated_at=excluded.updated_at WHERE feature_uses.used < ?",
                (feature, subject, period, stamp, limit))
            if cursor.rowcount != 1:
                c.rollback()
                return _spend_bonus(c, feature, user_id, period, stamp)
        c.commit()
        return True
    finally:
        c.close()


def _spend_bonus(c, feature: str, user_id: int | None, period: str, stamp: float) -> bool:
    """An extra try the owner gave this account for this week, if one is left."""
    if not user_id:
        return False
    cursor = c.execute("UPDATE feature_uses SET used=used-1, updated_at=? WHERE feature=? AND subject=? AND period=? AND used>0",
                       (stamp, feature, bonus_subject(user_id), period))
    if cursor.rowcount == 1:
        c.commit()
        return True
    c.rollback()
    return False


def give_bonus(user_id: int, features, count: int = 1, now: float | None = None) -> dict:
    """Owner action: extra tries for this week (they vanish on Monday like the normal ones)."""
    period, stamp = week(now), time.time()
    count = max(1, min(10, int(count or 1)))
    chosen = [f for f in (features or WEEKLY_FEATURES) if f in WEEKLY_FEATURES]
    if not chosen:
        raise ValueError("feature")
    c = auth_db._conn()
    try:
        for feature in chosen:
            c.execute(
                "INSERT INTO feature_uses (feature, subject, period, used, updated_at) VALUES (?,?,?,?,?) "
                "ON CONFLICT(feature, subject, period) DO UPDATE SET used=feature_uses.used+excluded.used, "
                "updated_at=excluded.updated_at",
                (feature, bonus_subject(user_id), period, count, stamp))
        c.commit()
    finally:
        c.close()
    return account_week(user_id, now)


def clear_bonus(user_id: int, now: float | None = None) -> dict:
    c = auth_db._conn()
    try:
        c.execute("DELETE FROM feature_uses WHERE subject=? AND period=?", (bonus_subject(user_id), week(now)))
        c.commit()
    finally:
        c.close()
    return account_week(user_id, now)


def account_week(user_id: int, now: float | None = None) -> dict:
    """For the admin user card: this week's tries of the account (the address part is not known here)."""
    period, limit = week(now), weekly_limit()
    c = auth_db._conn()
    try:
        rows = {}
        for feature in WEEKLY_FEATURES:
            used = _used(c, feature, f"u:{int(user_id)}", period)
            bonus = _used(c, feature, bonus_subject(user_id), period)
            rows[feature] = {"used": used, "limit": limit, "bonus": bonus, "left": max(0, limit - used) + bonus}
    finally:
        c.close()
    return {"period": period, "resets_at": week_resets_at(now), "limit": limit, "features": rows}


def refund(feature: str, who: list[str], period: str) -> None:
    """Give a use back (the job it paid for failed)."""
    if feature not in WEEKLY_FEATURES or not who or not period:
        return
    c = auth_db._conn()
    try:
        for subject in who:
            c.execute("UPDATE feature_uses SET used=used-1, updated_at=? WHERE feature=? AND subject=? AND period=? AND used>0",
                      (time.time(), feature, str(subject), period))
        c.commit()
    finally:
        c.close()


def ticket(feature: str, user_id: int | None, ip: str | None, now: float | None = None) -> dict:
    """What a job remembers about the free use that paid for it, so a failure can give it back."""
    return {"feature": feature, "subjects": subjects(user_id, ip), "period": week(now)}


def refund_ticket(value) -> bool:
    if not isinstance(value, dict) or not value.get("feature"):
        return False
    refund(str(value["feature"]), [str(item) for item in value.get("subjects") or []], str(value.get("period") or ""))
    return True


def refund_job(jid: str, job: dict | None) -> None:
    """Called when a job ends in an error: return its free weekly use, once."""
    if not job or not job.get("free_try") or job.get("free_try_refunded"):
        return
    if refund_ticket(job.get("free_try")):
        import redis_store as rs
        rs._job_update(jid, free_try_refunded=True)


# ---------------------------------------------------------------- what the pages show
def state(user_id: int | None, ip: str | None, pro: bool) -> dict:
    """For /api/quota: weekly tries left, when they renew, which features are beta, Builder exports today."""
    result: dict = {"pro": bool(pro), "beta": list(beta_features()), "week_resets_at": week_resets_at(),
                    "day_resets_at": day_resets_at(), "weekly_limit": weekly_limit()}
    if pro:
        return result
    period, limit = week(), weekly_limit()
    who = subjects(user_id, ip)
    weekly = {}
    c = auth_db._conn()
    try:
        for feature in WEEKLY_FEATURES:
            used = max((_used(c, feature, subject, period) for subject in who), default=0)
            bonus = _used(c, feature, bonus_subject(user_id), period) if user_id else 0
            weekly[feature] = {"limit": limit, "left": (max(0, limit - used) + bonus) if who else 0}
        if user_id:
            day = time.strftime("%Y-%m-%d", time.gmtime())
            row = c.execute("SELECT renders FROM builder_usage WHERE user_id=? AND day_key=?", (int(user_id), day)).fetchone()
            exports = builder_exports_per_day()
            result["builder"] = {"limit": exports, "left": max(0, exports - (int(row["renders"] or 0) if row else 0))}
    finally:
        c.close()
    result["weekly"] = weekly
    return result


# ---------------------------------------------------------------- refusals (text in the visitor's language)
MESSAGES = {
    "weekly": {
        "en": "Free: this tool works once a week, and this week's use is spent. It renews on Monday. With Pro there is no weekly limit.",
        "ru": "Бесплатно этот инструмент работает один раз в неделю, и на этой неделе попытка уже использована. Обновится в понедельник. С Pro недельного лимита нет.",
        "de": "Kostenlos funktioniert dieses Werkzeug einmal pro Woche, und der Versuch dieser Woche ist verbraucht. Am Montag gibt es einen neuen. Mit Pro gibt es kein Wochenlimit.",
        "tr": "Bu araç ücretsiz olarak haftada bir kez çalışır ve bu haftaki hakkın kullanıldı. Pazartesi yenilenir. Pro ile haftalık sınır yok.",
        "fr": "En gratuit, cet outil fonctionne une fois par semaine, et l’essai de cette semaine est utilisé. Il se renouvelle lundi. Avec Pro, il n’y a pas de limite hebdomadaire.",
        "uk": "Безкоштовно цей інструмент працює раз на тиждень, і цього тижня спробу вже використано. Оновиться в понеділок. З Pro тижневого ліміту немає.",
        "es": "Gratis, esta herramienta funciona una vez por semana y el uso de esta semana ya está gastado. Se renueva el lunes. Con Pro no hay límite semanal.",
        "pt": "No plano gratuito, esta ferramenta funciona uma vez por semana, e o uso desta semana já foi gasto. Renova na segunda-feira. Com o Pro não há limite semanal.",
    },
    "beta": {
        "en": "This tool is in beta and is available with Pro only.",
        "ru": "Этот инструмент в бета-тесте и пока доступен только с Pro.",
        "de": "Dieses Werkzeug ist in der Beta und nur mit Pro verfügbar.",
        "tr": "Bu araç beta aşamasında ve yalnızca Pro ile kullanılabilir.",
        "fr": "Cet outil est en bêta et n’est disponible qu’avec Pro.",
        "uk": "Цей інструмент у бета-тесті й поки доступний лише з Pro.",
        "es": "Esta herramienta está en beta y solo está disponible con Pro.",
        "pt": "Esta ferramenta está em beta e só está disponível com o Pro.",
    },
    "builder": {
        "en": "Free: {n} Builder exports a day, and today's are spent. They renew at midnight UTC. With Pro there is no limit.",
        "ru": "Бесплатно — экспортов из Builder в день: {n}, и на сегодня они закончились. Обновятся в полночь по UTC. С Pro лимита нет.",
        "de": "Kostenlos: {n} Builder-Exporte pro Tag, und die heutigen sind verbraucht. Um Mitternacht UTC gibt es neue. Mit Pro gibt es kein Limit.",
        "tr": "Ücretsiz: günde {n} Builder dışa aktarımı, bugünküler kullanıldı. UTC gece yarısı yenilenir. Pro ile sınır yok.",
        "fr": "Gratuit : {n} exports Builder par jour, et ceux d’aujourd’hui sont utilisés. Ils se renouvellent à minuit UTC. Avec Pro, pas de limite.",
        "uk": "Безкоштовно — експортів із Builder на день: {n}, і на сьогодні вони закінчилися. Оновляться опівночі за UTC. З Pro ліміту немає.",
        "es": "Gratis: {n} exportaciones de Builder al día, y las de hoy están gastadas. Se renuevan a medianoche UTC. Con Pro no hay límite.",
        "pt": "Grátis: {n} exportações do Builder por dia, e as de hoje já foram usadas. Renovam à meia-noite UTC. Com o Pro não há limite.",
    },
    "daily": {
        "en": "Free: {n} files a day, and today's are spent. They renew at midnight UTC. With Pro there is no daily limit.",
        "ru": "Бесплатно — файлов в день: {n}, и на сегодня они закончились. Обновятся в полночь по UTC. С Pro дневного лимита нет.",
        "de": "Kostenlos: {n} Dateien pro Tag, und die heutigen sind verbraucht. Um Mitternacht UTC gibt es neue. Mit Pro gibt es kein Tageslimit.",
        "tr": "Ücretsiz: günde {n} dosya, bugünküler kullanıldı. UTC gece yarısı yenilenir. Pro ile günlük sınır yok.",
        "fr": "Gratuit : {n} fichiers par jour, et ceux d’aujourd’hui sont utilisés. Ils se renouvellent à minuit UTC. Avec Pro, pas de limite quotidienne.",
        "uk": "Безкоштовно — файлів на день: {n}, і на сьогодні вони закінчилися. Оновляться опівночі за UTC. З Pro денного ліміту немає.",
        "es": "Gratis: {n} archivos al día, y los de hoy están gastados. Se renuevan a medianoche UTC. Con Pro no hay límite diario.",
        "pt": "Grátis: {n} arquivos por dia, e os de hoje já foram usados. Renovam à meia-noite UTC. Com o Pro não há limite diário.",
    },
}
MESSAGES["daily_more"] = {
    "en": "This job needs more files than are left today (Free: {n} a day). They renew at midnight UTC. With Pro there is no daily limit.",
    "ru": "Для этой задачи нужно больше файлов, чем осталось на сегодня (бесплатно — файлов в день: {n}). Лимит обновится в полночь по UTC. С Pro дневного лимита нет.",
    "de": "Dieser Auftrag braucht mehr Dateien, als heute übrig sind (kostenlos: {n} pro Tag). Um Mitternacht UTC gibt es neue. Mit Pro gibt es kein Tageslimit.",
    "tr": "Bu iş, bugün kalan dosyalardan fazlasını gerektiriyor (ücretsiz: günde {n}). UTC gece yarısı yenilenir. Pro ile günlük sınır yok.",
    "fr": "Cette tâche demande plus de fichiers qu’il n’en reste aujourd’hui (gratuit : {n} par jour). Ils se renouvellent à minuit UTC. Avec Pro, pas de limite quotidienne.",
    "uk": "Для цього завдання потрібно більше файлів, ніж лишилося на сьогодні (безкоштовно — файлів на день: {n}). Ліміт оновиться опівночі за UTC. З Pro денного ліміту немає.",
    "es": "Este trabajo necesita más archivos de los que quedan hoy (gratis: {n} al día). Se renuevan a medianoche UTC. Con Pro no hay límite diario.",
    "pt": "Esta tarefa precisa de mais arquivos do que restam hoje (grátis: {n} por dia). Renovam à meia-noite UTC. Com o Pro não há limite diário.",
}
_STATUS = {"weekly": 429, "beta": 403, "builder": 429, "daily": 403, "daily_more": 403}


def message(kind: str, language: str, **values) -> str:
    texts = MESSAGES.get(kind) or {}
    text = texts.get(language) or texts.get("en") or ""
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def _language(request) -> str:
    try:
        from smweb.locales import request_language
        return request_language(request)
    except Exception:
        return "en"


def refusal(request, kind: str, feature: str = "", *, code: str = "", **values):
    """The answer for a spent allowance: text in the visitor's language plus ``limit`` for the page's own dialog.

    ``code`` keeps the value older page scripts already look for (``remove_bg_limit``, ``limit``, ``quota``).
    """
    from fastapi.responses import JSONResponse
    resets = week_resets_at() if kind == "weekly" else (day_resets_at() if kind in ("builder", "daily", "daily_more") else None)
    body = {"ok": False, "code": code or {"weekly": "weekly_limit", "beta": "beta", "builder": "builder_limit",
                                          "daily": "quota", "daily_more": "quota"}[kind],
            "msg": message(kind, _language(request), **values),
            "limit": {"kind": "daily" if kind == "daily_more" else kind, "feature": feature, "resets_at": resets}}
    if kind == "builder":
        body["remaining"] = 0
    return JSONResponse(body, status_code=_STATUS[kind])
