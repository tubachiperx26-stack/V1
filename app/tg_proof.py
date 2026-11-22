import html
import random
import string
from datetime import datetime, timezone, timedelta
import httpx

from app.config import TG_BOT_TOKEN, TG_PROOF_CHANNEL_ID, SITE_URL, OFFICIAL_CHANNEL_URL
from app.db import db

BD_TZ = timezone(timedelta(hours=6))

_LAST_STATUS_KEY = None

REF_PREFIXES = [
    "ARIF", "RAFI", "TANV", "SADI", "MEHE", "NUSR", "SABB", "MAHM", "NAIM", "SHAW",
    "FAHM", "JUBA", "IMRA", "RAKI", "TASP", "FARI", "SUMI", "NAZM", "KAMR", "RIFA",
    "TOUH", "HABI", "SOHA", "MIRA", "SAIF", "ASIF", "ZAYN", "NABI", "TARE", "ALAM",
    "SHAK", "ROBI", "MUNI", "RIYA", "ANIK", "EMON", "HRID", "KABI", "LAMI", "MONI",
    "NIHA", "OMAR", "PARV", "RUMU", "SHIH", "TARI", "UMME", "WASI", "YASI", "ZAKI",
    "RUBEL", "SUJON", "MARU", "NISH", "TANI", "AKAS", "BISH", "CHOW", "DIPA", "FARH",
]

ALPHANUM = string.ascii_uppercase + string.digits


def random_alnum(length: int) -> str:
    return "".join(random.choices(ALPHANUM, k=length))


def mask_account(acc: str) -> str:
    s = (acc or "").strip()
    if "@" in s:
        name, dom = s.split("@", 1)
        return f"{name[:3]}••••@{dom}"
    if len(s) <= 5:
        return (s[:1] + "•••" + s[-1:]) if len(s) > 2 else s
    return f"{s[:3]}••••{s[-4:]}"


def pick_weighted_status() -> tuple[str, str, str, str, str]:
    """
    60% -> Withdrawal Success
    37% -> Withdraw Request Success
    3%  -> Withdrawal Rejected
    """
    global _LAST_STATUS_KEY
    r = random.random() * 100

    if r < 60:
        if _LAST_STATUS_KEY == "success" and random.random() < 0.45:
            _LAST_STATUS_KEY = "request"
            return ("request", "📥", "Withdraw Request Success", "Pending Review ⏳", "New payout request queued for verification")
        _LAST_STATUS_KEY = "success"
        return ("success", "✅", "Withdrawal Success", "Paid Successfully ✅", "Instant 0% fee payout completed")
    elif r < 97:
        _LAST_STATUS_KEY = "request"
        return ("request", "📥", "Withdraw Request Success", "Pending Review ⏳", "New payout request queued for verification")
    else:
        _LAST_STATUS_KEY = "rejected"
        return ("rejected", "❌", "Withdrawal Rejected", "Rejected & Refunded ↩️", "Verification failed • Balance returned")


def pick_weighted_amount() -> float:
    """
    Minimum 100৳+:
    35% -> 100 - 350
    35% -> 350 - 550
    20% -> 550 - 1000
    7%  -> 1000 - 1500
    3%  -> 2000 - 2200
    """
    r = random.random() * 100
    if r < 35:
        return float(random.randint(20, 70) * 5)       # 100 - 350
    elif r < 70:
        return float(random.randint(70, 110) * 5)      # 350 - 550
    elif r < 90:
        return float(random.randint(110, 200) * 5)     # 550 - 1000
    elif r < 97:
        return float(random.randint(100, 150) * 10)    # 1000 - 1500
    else:
        return float(random.randint(200, 220) * 10)    # 2000 - 2200


def generate_realistic_fake_proof(force_type: str | None = None) -> dict:
    if force_type == "request":
        emoji, headline, status_text, subtitle = (
            "📥", "Withdraw Request Success", "Pending Review ⏳", "New payout request queued for verification"
        )
    elif force_type == "rejected":
        emoji, headline, status_text, subtitle = (
            "❌", "Withdrawal Rejected", "Rejected & Refunded ↩️", "Verification failed • Balance returned"
        )
    elif force_type == "success":
        emoji, headline, status_text, subtitle = (
            "✅", "Withdrawal Success", "Paid Successfully ✅", "Instant 0% fee payout completed"
        )
    else:
        _, emoji, headline, status_text, subtitle = pick_weighted_status()

    amount = pick_weighted_amount()

    method = random.choices(
        ["bKash", "Nagad", "Rocket", "Binance"],
        weights=[50, 30, 12, 8],
        k=1,
    )[0]

    if method == "Binance":
        uid_num = random.randint(110, 999)
        last3 = random.randint(100, 999)
        masked_acc = f"UID-{uid_num}••••{last3}"
    else:
        prefix = random.choice(["017", "018", "019", "016", "013"])
        last4 = random.randint(1000, 9999)
        masked_acc = f"{prefix}••••{last4}"

    user_id = random.randint(1024, 19890)
    refer_id = "DIRECT" if random.random() < 0.12 else f"{random.choice(REF_PREFIXES)}{random_alnum(5)}"
    trx_hash = f"IW-PAY-{random.randint(78329, 99999)}"

    return {
        "emoji": emoji,
        "headline": headline,
        "subtitle": subtitle,
        "status_text": status_text,
        "method": method,
        "masked_acc": masked_acc,
        "amount": amount,
        "user_id": user_id,
        "refer_id": refer_id,
        "trx_hash": trx_hash,
    }


def format_tg_message(data: dict) -> str:
    bd_time = datetime.now(BD_TZ).strftime("%d %b %Y • %I:%M %p")
    acc = html.escape(str(data["masked_acc"]))
    method = html.escape(str(data["method"]))
    st_txt = html.escape(str(data["status_text"]))
    uid = html.escape(str(data["user_id"]))
    ref_id = html.escape(str(data["refer_id"]))
    trx = html.escape(str(data["trx_hash"]))
    headline = html.escape(str(data["headline"]))
    subtitle = html.escape(str(data.get("subtitle") or "InfinityWork Official Payout"))

    return (
        f"{data['emoji']} <b>{headline.upper()}</b>\n"
        f"<i>{subtitle}</i>\n\n"
        f"<blockquote>💳 <b>Withdrawal Data</b>\n"
        f"┣ <b>Account:</b> <code>{acc}</code>\n"
        f"┣ <b>Method:</b> {method}\n"
        f"┣ <b>Amount:</b> <b>৳{data['amount']:,.2f}</b>\n"
        f"┗ <b>Status:</b> {st_txt}\n\n"
        f"👤 <b>User Data</b>\n"
        f"┣ <b>User ID:</b> <code>#IW-{uid}</code>\n"
        f"┣ <b>Refer ID:</b> <code>{ref_id}</code>\n"
        f"┗ <b>Payment ID:</b> <code>{trx}</code></blockquote>\n"
        f"🕒 <i>{bd_time} (BDT)</i>  •  ⚡ <b>0% Fee</b>"
    )


async def send_to_proof_channel(text: str) -> tuple[bool, str]:
    if not TG_BOT_TOKEN or not TG_PROOF_CHANNEL_ID:
        return False, "Missing TG_BOT_TOKEN or TG_PROOF_CHANNEL_ID"

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_PROOF_CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "🚀 Start Earning Free", "url": SITE_URL},
                    {"text": "📢 Official Channel", "url": OFFICIAL_CHANNEL_URL},
                ]
            ]
        },
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                return True, "ok"
            return False, r.text
    except Exception as e:
        return False, str(e)


async def notify_real_withdrawal(
    user: dict,
    method: str,
    account_number: str,
    amount: float,
    status: str = "request",
    payout_id: int | None = None,
):
    if status == "paid":
        emoji, headline, st_txt, sub = (
            "✅", "Withdrawal Success", "Paid Successfully ✅", "Instant 0% fee payout completed"
        )
    elif status == "rejected":
        emoji, headline, st_txt, sub = (
            "❌", "Withdrawal Rejected", "Rejected & Refunded ↩️", "Verification failed • Balance returned"
        )
    else:
        emoji, headline, st_txt, sub = (
            "📥", "Withdraw Request Success", "Pending Review ⏳", "New payout request queued for verification"
        )

    pay_num = payout_id if payout_id else random.randint(78329, 99999)
    data = {
        "emoji": emoji,
        "headline": headline,
        "subtitle": sub,
        "status_text": st_txt,
        "method": method,
        "masked_acc": mask_account(account_number),
        "amount": float(amount),
        "user_id": user.get("id", 0),
        "refer_id": user.get("referral_code") or "DIRECT",
        "trx_hash": f"IW-PAY-{pay_num}",
    }
    await send_to_proof_channel(format_tg_message(data))


async def should_post_cron_now(force: bool = False) -> tuple[bool, str]:
    if force:
        return True, "forced"

    bd_now = datetime.now(BD_TZ)
    hour = bd_now.hour
    # Night Slow Mode: 11:00 PM (23) to 8:00 AM (07:59) -> min 360s (6 min) interval
    is_night = hour >= 23 or hour < 8
    min_gap_sec = 360 if is_night else 45

    try:
        row = await db.select("site_settings", filters={"key": "last_proof_cron_ts"}, single=True)
        now_ts = int(bd_now.timestamp())
        if row and row.get("value"):
            last_ts = int(row["value"])
            if (now_ts - last_ts) < min_gap_sec:
                return False, f"cooldown ({'night-slow' if is_night else 'day'} mode)"
            await db.update("site_settings", {"key": "last_proof_cron_ts"}, {"value": str(now_ts)})
        else:
            await db.insert("site_settings", {"key": "last_proof_cron_ts", "value": str(now_ts)})
    except Exception:
        if is_night and random.random() > 0.16:
            return False, "night-slow-prob"

    return True, "night-slow" if is_night else "day-normal"
