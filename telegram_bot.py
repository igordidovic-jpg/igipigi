"""
CFOS-XG PRO 75 TITAN - Telegram Live Bot

Commands:
    /start          - Initialize bot and show help
    /csv [data]     - Parse CSV and get BET DECISION
    /live [teams]   - Start live match tracking
    /stats          - Show accuracy statistics
    /history        - Show match history
    /alert MODE     - Set alert level (HIGH/MEDIUM/ALL)
    /language CODE  - Set language (SLO/ENG)

Usage:
    1. Set TELEGRAM_BOT_TOKEN in .env or environment
    2. python telegram_bot.py
"""
import os
import sys
import asyncio
import logging
from typing import Optional

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Logging setup
from utils.logging_config import setup_logging, get_logger
setup_logging(level="INFO", use_json=False)
logger = get_logger(__name__)

# Check for python-telegram-bot
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
    )
    from telegram.constants import ParseMode
    PTB_AVAILABLE = True
except ImportError:
    PTB_AVAILABLE = False
    logger.error("python-telegram-bot not installed. Run: pip install 'python-telegram-bot>=20.0'")

# Import CFOS engine
from cfos_optimized import analyze_csv, get_bet_decision_text, get_cache_stats
from engine.bet_scorer import BetScorer
from utils.database import Database

# Global database instance
db = Database()

# Live tracking sessions: {user_id: {home, away, updates: []}}
live_sessions: dict[int, dict] = {}

# ============================================================
# MESSAGES (SLO / ENG)
# ============================================================

MESSAGES = {
    "ENG": {
        "welcome": (
            "⚽ *CFOS-XG PRO 75 TITAN*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Live football betting analytics bot.\n\n"
            "*Commands:*\n"
            "📊 /csv `[data]` — Analyze match CSV\n"
            "📡 /live `[home] [away]` — Start live tracking\n"
            "📈 /stats — Your accuracy stats\n"
            "📜 /history — Match history\n"
            "🔔 /alert `MODE` — Set alerts (HIGH/MEDIUM/ALL)\n"
            "🌐 /language `CODE` — Set language (SLO/ENG)\n\n"
            "_Send /csv followed by your match data to get started._"
        ),
        "csv_prompt": "📥 Please send your CSV data after the command.\n\nFormat: `home,away,odds_h,odds_d,odds_a,minute,score_h,score_a,...`\n\nExample:\n`/csv Arsenal,Chelsea,2.10,3.30,3.80,68,1,0,0.80,0.50,6,4,3,2,22,18,8,5,2,1,1,0,0,0,58,42,1,2,0,1,5,3`",
        "analyzing": "⚡ *Analyzing...*\n\n✅ CSV parsed\n⚡ Running model...",
        "error": "❌ Error processing CSV. Please check your data format.",
        "no_result": "⚠️ Model returned no result. Please verify the input data.",
        "stats_empty": "📊 No matches analyzed yet. Use /csv to get started!",
        "history_empty": "📜 No match history yet. Use /csv to analyze your first match!",
        "live_started": "📡 Live tracking started for *{home} vs {away}*\nSend updates with:\n`/live {home} {away} minute score_h-score_a [csv_data]`",
        "live_stopped": "🔴 Live tracking stopped.",
        "alert_set": "🔔 Alert level set to *{level}*",
        "alert_invalid": "❌ Invalid alert level. Use: HIGH, MEDIUM, or ALL",
        "language_set": "🌐 Language set to *{lang}*",
        "language_invalid": "❌ Invalid language. Use: SLO or ENG",
        "cached": "⚡ _(from cache)_",
    },
    "SLO": {
        "welcome": (
            "⚽ *CFOS-XG PRO 75 TITAN*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Bot za analizo nogometnih tekem v živo.\n\n"
            "*Ukazi:*\n"
            "📊 /csv `[podatki]` — Analiziraj CSV\n"
            "📡 /live `[domači] [gost]` — Začni sledenje v živo\n"
            "📈 /stats — Tvoja natančnost\n"
            "📜 /history — Zgodovina tekem\n"
            "🔔 /alert `NIVO` — Nastavi alerting (HIGH/MEDIUM/ALL)\n"
            "🌐 /language `KOD` — Nastavi jezik (SLO/ENG)\n\n"
            "_Pošlji /csv skupaj s podatki tekme._"
        ),
        "csv_prompt": "📥 Prosim pošlji CSV podatke za tekmo.\n\nFormat: `domači,gost,kvota_d,kvota_r,kvota_g,minuta,goli_d,goli_g,...`",
        "analyzing": "⚡ *Analiziram...*\n\n✅ CSV razčlenjen\n⚡ Izvajam model...",
        "error": "❌ Napaka pri obdelavi CSV. Preverite format podatkov.",
        "no_result": "⚠️ Model ni vrnil rezultata. Preverite vhodne podatke.",
        "stats_empty": "📊 Še ni analiziranih tekem. Uporabite /csv za začetek!",
        "history_empty": "📜 Zgodovina tekem je prazna. Uporabite /csv za analizo prve tekme!",
        "live_started": "📡 Sledenje v živo začeto za *{home} vs {away}*",
        "live_stopped": "🔴 Sledenje v živo ustavljeno.",
        "alert_set": "🔔 Nivo alertov nastavljen na *{level}*",
        "alert_invalid": "❌ Neveljaven nivo. Uporabite: HIGH, MEDIUM ali ALL",
        "language_set": "🌐 Jezik nastavljen na *{lang}*",
        "language_invalid": "❌ Neveljaven jezik. Uporabite: SLO ali ENG",
        "cached": "⚡ _(iz predpomnilnika)_",
    },
}


async def get_user_lang(user_id: int) -> str:
    """Get user's language preference."""
    prefs = await db.get_user_prefs(user_id)
    return prefs.get("language", "ENG")


async def get_user_alert(user_id: int) -> str:
    """Get user's alert level preference."""
    prefs = await db.get_user_prefs(user_id)
    return prefs.get("alert_level", "HIGH")


def msg(lang: str, key: str, **kwargs) -> str:
    """Get a localized message string."""
    text = MESSAGES.get(lang, MESSAGES["ENG"]).get(key, "")
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            pass
    return text


def should_alert(bet: str, confidence: str, alert_level: str) -> bool:
    """
    Determine whether to send an alert based on user's alert level setting.

    Args:
        bet: Bet type
        confidence: HIGH/MEDIUM/LOW
        alert_level: User preference HIGH/MEDIUM/ALL

    Returns:
        True if alert should be sent
    """
    if bet == "NO BET":
        return False
    if alert_level == "ALL":
        return True
    if alert_level == "MEDIUM":
        return confidence in ("HIGH", "MEDIUM")
    # HIGH: only HIGH confidence bets
    return confidence == "HIGH"


# ============================================================
# COMMAND HANDLERS
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)
    await update.message.reply_text(
        msg(lang, "welcome"),
        parse_mode=ParseMode.MARKDOWN,
    )


async def _handle_csv_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               csv_data: str, lang: str, user_id: int):
    """Shared CSV analysis logic used by cmd_csv and handle_message."""
    progress_msg = await update.message.reply_text(
        msg(lang, "analyzing"),
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: analyze_csv(csv_data))

        if result is None:
            await progress_msg.edit_text(msg(lang, "error"))
            return

        decision = result.get("_decision") or BetScorer.extract_decision(result)
        score_home = int(float(result.get("score_home", 0) or 0))
        score_away = int(float(result.get("score_away", 0) or 0))

        bet_msg = BetScorer.format_telegram_message(decision, score_home, score_away)
        if result.get("_cached"):
            bet_msg += f"\n\n{msg(lang, 'cached')}"

        alert_level = await get_user_alert(user_id)
        if should_alert(decision["bet"], decision["confidence"], alert_level):
            await progress_msg.edit_text(bet_msg, parse_mode=ParseMode.MARKDOWN)
        else:
            note = f"\n\n_Alert level {alert_level}: This bet did not meet threshold_"
            await progress_msg.edit_text(bet_msg + note, parse_mode=ParseMode.MARKDOWN)

        await db.save_match(user_id, decision, csv_data, score_home, score_away)

        logger.info(
            "CSV analysis complete",
            extra={
                "user_id": user_id,
                "match": f"{decision['home']} vs {decision['away']}",
                "bet": decision["bet"],
                "confidence": decision["confidence"],
            },
        )

    except Exception as e:
        logger.error(f"CSV analysis error: {e}", exc_info=True)
        await progress_msg.edit_text(msg(lang, "error"))


async def cmd_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /csv command - analyze match CSV data."""
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)

    # Get CSV data from message
    text = update.message.text or ""
    csv_data = text[len("/csv"):].strip()

    if not csv_data:
        await update.message.reply_text(
            msg(lang, "csv_prompt"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await _handle_csv_analysis(update, context, csv_data=csv_data, lang=lang, user_id=user_id)


async def cmd_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /live command - live match tracking.

    Usage:
        /live home away           - Start tracking session
        /live home away minute score  csv...  - Update with new data
        /live stop                - Stop tracking
    """
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)

    text = update.message.text or ""
    args = text[len("/live"):].strip()

    if not args or args.lower() == "stop":
        if user_id in live_sessions:
            del live_sessions[user_id]
            await update.message.reply_text(msg(lang, "live_stopped"))
        else:
            await update.message.reply_text(
                "📡 No active live session.\nStart one with: `/live HomeTeam AwayTeam`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    parts = args.split(",", 1)
    if len(parts) == 1:
        # Just team names: /live Arsenal Chelsea
        team_parts = args.split()
        if len(team_parts) >= 2:
            home = team_parts[0]
            away = team_parts[1]
            live_sessions[user_id] = {
                "home": home,
                "away": away,
                "updates": [],
                "last_minute": 0,
            }
            await update.message.reply_text(
                msg(lang, "live_started", home=home, away=away),
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.message.reply_text(
                "Usage: `/live HomeTeam AwayTeam`\nor `/live HomeTeam,AwayTeam,odds_h,...`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    # CSV data provided - analyze and update live session
    csv_data = args
    session = live_sessions.get(user_id)

    progress_msg = await update.message.reply_text(
        "📡 *Live update...*", parse_mode=ParseMode.MARKDOWN
    )

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: analyze_csv(csv_data))

        if result is None:
            await progress_msg.edit_text(msg(lang, "error"))
            return

        decision = result.get("_decision") or BetScorer.extract_decision(result)
        score_home = int(float(result.get("score_home", 0) or 0))
        score_away = int(float(result.get("score_away", 0) or 0))
        minute = decision.get("minute", 0)

        # Update session
        home = result.get("home", "HOME")
        away = result.get("away", "AWAY")
        if user_id not in live_sessions:
            live_sessions[user_id] = {"home": home, "away": away, "updates": [], "last_minute": 0}

        live_sessions[user_id]["updates"].append({
            "minute": minute,
            "score": f"{score_home}-{score_away}",
            "bet": decision["bet"],
            "confidence": decision["confidence"],
        })
        live_sessions[user_id]["last_minute"] = minute

        # Format live update message
        bet_msg = f"📡 *LIVE UPDATE [{minute}']*\n\n" + BetScorer.format_telegram_message(
            decision, score_home, score_away
        )

        # Add update timeline
        updates = live_sessions[user_id]["updates"][-5:]  # last 5 updates
        if len(updates) > 1:
            timeline = "\n*📊 Session timeline:*\n"
            for u in updates:
                conf_sym = "🟢" if u["confidence"] == "HIGH" else "🟡" if u["confidence"] == "MEDIUM" else "⚪"
                timeline += f"{conf_sym} [{u['minute']}'] {u['score']} → {u['bet']}\n"
            bet_msg += f"\n{timeline}"

        alert_level = await get_user_alert(user_id)
        if should_alert(decision["bet"], decision["confidence"], alert_level):
            await progress_msg.edit_text(bet_msg, parse_mode=ParseMode.MARKDOWN)
        else:
            await progress_msg.edit_text(
                bet_msg + f"\n_Alert level {alert_level}: threshold not met_",
                parse_mode=ParseMode.MARKDOWN,
            )

    except Exception as e:
        logger.error(f"cmd_live error: {e}", exc_info=True)
        await progress_msg.edit_text(msg(lang, "error"))


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show accuracy statistics."""
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)

    stats = await db.get_accuracy(user_id)

    if stats["total"] == 0:
        await update.message.reply_text(msg(lang, "stats_empty"))
        return

    acc_pct = round(stats["accuracy"] * 100, 1)
    lines = [
        "📈 *YOUR ACCURACY STATS*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ Total analyzed: *{stats['total']}*",
        f"🎯 Correct: *{stats['correct']}* ({acc_pct}%)",
        "",
        "*By confidence level:*",
    ]

    for conf, cstats in stats.get("by_confidence", {}).items():
        acc = round(cstats["accuracy"] * 100, 1)
        emoji = "🔥" if conf == "HIGH" else "🟡" if conf == "MEDIUM" else "⚪"
        lines.append(f"{emoji} {conf}: {cstats['correct']}/{cstats['total']} ({acc}%)")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history command - show match history."""
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)

    history = await db.get_match_history(user_id, limit=10)

    if not history:
        await update.message.reply_text(msg(lang, "history_empty"))
        return

    lines = ["📜 *MATCH HISTORY* (last 10)", "━━━━━━━━━━━━━━━━━━━━━━━━━━━"]

    for i, match in enumerate(history, 1):
        home = match.get("home", "?")
        away = match.get("away", "?")
        minute = match.get("minute", "?")
        bet = match.get("bet", "?")
        conf = match.get("confidence", "?")
        result = match.get("final_result", "")
        correct = match.get("correct")

        result_icon = ""
        if correct == 1:
            result_icon = " ✅"
        elif correct == 0:
            result_icon = " ❌"

        conf_icon = "🔥" if conf == "HIGH" else "🟡" if conf == "MEDIUM" else "⚪"
        lines.append(f"{i}. {home} vs {away} [{minute}']{result_icon}")
        lines.append(f"   {conf_icon} {bet} ({conf})")
        if result:
            lines.append(f"   Result: {result}")
        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alert command - set alert level."""
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)

    text = update.message.text or ""
    args = text[len("/alert"):].strip().upper()

    valid_levels = {"HIGH", "MEDIUM", "ALL"}

    if args not in valid_levels:
        keyboard = [
            [
                InlineKeyboardButton("🔥 HIGH", callback_data="alert_HIGH"),
                InlineKeyboardButton("🟡 MEDIUM", callback_data="alert_MEDIUM"),
                InlineKeyboardButton("📢 ALL", callback_data="alert_ALL"),
            ]
        ]
        await update.message.reply_text(
            msg(lang, "alert_invalid") + "\n\nOr choose:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await db.set_user_pref(user_id, "alert_level", args)
    await update.message.reply_text(
        msg(lang, "alert_set", level=args),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /language command - set language preference."""
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)

    text = update.message.text or ""
    new_lang = text[len("/language"):].strip().upper()

    valid_langs = {"SLO", "ENG"}
    if new_lang not in valid_langs:
        keyboard = [
            [
                InlineKeyboardButton("🇸🇮 SLO", callback_data="lang_SLO"),
                InlineKeyboardButton("🇬🇧 ENG", callback_data="lang_ENG"),
            ]
        ]
        await update.message.reply_text(
            msg(lang, "language_invalid") + "\n\nOr choose:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await db.set_user_pref(user_id, "language", new_lang)
    await update.message.reply_text(
        msg(new_lang, "language_set", lang=new_lang),
        parse_mode=ParseMode.MARKDOWN,
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    data = query.data or ""
    lang = await get_user_lang(user_id)

    if data.startswith("alert_"):
        level = data[len("alert_"):]
        await db.set_user_pref(user_id, "alert_level", level)
        await query.edit_message_text(
            msg(lang, "alert_set", level=level),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data.startswith("lang_"):
        new_lang = data[len("lang_"):]
        await db.set_user_pref(user_id, "language", new_lang)
        await query.edit_message_text(
            msg(new_lang, "language_set", lang=new_lang),
            parse_mode=ParseMode.MARKDOWN,
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages - treat as CSV if they look like data."""
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)

    # If it looks like CSV data (contains commas and numbers), analyze it directly
    if "," in text and any(c.isdigit() for c in text):
        await _handle_csv_analysis(update, context, csv_data=text, lang=lang, user_id=user_id)
    else:
        await update.message.reply_text(
            "❓ Unknown command. Type /start for help.",
            parse_mode=ParseMode.MARKDOWN,
        )


# ============================================================
# BOT SETUP & RUN
# ============================================================

async def post_init(application: "Application"):
    """Initialize database on bot startup."""
    await db.initialize()
    logger.info("Bot initialized, database ready")


def main():
    """Main entry point."""
    if not PTB_AVAILABLE:
        logger.error("python-telegram-bot not installed!")
        sys.exit(1)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment!")
        print("\n❌ TELEGRAM_BOT_TOKEN not set!")
        print("Set it with: export TELEGRAM_BOT_TOKEN=your_token_here")
        print("Or create a .env file with: TELEGRAM_BOT_TOKEN=your_token_here\n")
        sys.exit(1)

    logger.info("Starting CFOS-XG PRO 75 TITAN Telegram Bot...")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("csv", cmd_csv))
    app.add_handler(CommandHandler("live", cmd_live))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("alert", cmd_alert))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    webhook_url = os.environ.get("WEBHOOK_URL", "")
    if webhook_url:
        logger.info(f"Starting with webhook: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8443)),
            url_path=token,
            webhook_url=f"{webhook_url}/{token}",
        )
    else:
        logger.info("Starting with polling...")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
