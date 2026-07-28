#!/usr/bin/env python3
"""Telegram bot for proxy scraping and management."""

import asyncio
import os
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv
from telegram import InputFile, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from proxy_scraper import check_proxies, scrape_proxies

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"⚠️  .env file not found at {env_file}")
    print("   Create a .env file by copying .env.example")

BOT_TOKEN: Final[str | None] = os.getenv("TELEGRAM_BOT_TOKEN")
RATE_LIMIT_SECONDS = 20
MAX_PROXY_PREVIEW = 20


def _can_execute(user_data: dict[str, Any], key: str, limit: int = RATE_LIMIT_SECONDS) -> tuple[bool, float]:
    now = datetime.utcnow()
    last_time = user_data.get(key)
    if isinstance(last_time, datetime):
        elapsed = (now - last_time).total_seconds()
        if elapsed < limit:
            return False, limit - elapsed
    user_data[key] = now
    return True, 0.0


def _preview_text(proxies: list[str]) -> str:
    preview = proxies[:MAX_PROXY_PREVIEW]
    result = "\n".join(preview)
    if len(proxies) > MAX_PROXY_PREVIEW:
        result += f"\n\n... and {len(proxies) - MAX_PROXY_PREVIEW} more proxies."
    return result


def _build_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Export ALL", callback_data="export_type_all")],
        [InlineKeyboardButton("Export HTTP", callback_data="export_type_http")],
        [InlineKeyboardButton("Export SOCKS", callback_data="export_type_socks")],
        [InlineKeyboardButton("Refresh proxies", callback_data="refresh_proxies")],
    ]
    return InlineKeyboardMarkup(keyboard)


def _build_live_keyboard(selection: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("All proxies", callback_data=f"export_live_{selection}_all")],
        [InlineKeyboardButton("Alive only", callback_data=f"export_live_{selection}_alive")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_action")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "🤖 *Proxy Scraper Bot*\n\n"
        "Fetch public proxies from multiple sources with a clean export flow.\n\n"
        "*Commands:*\n"
        "/proxies - Fetch and preview proxies\n"
        "/export - Export proxy lists by type\n"
        "/help - Show this help message",
        parse_mode="Markdown"
    )


async def proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /proxies command - fetch and preview proxies."""
    allowed, wait = _can_execute(context.user_data, "last_proxies")
    if not allowed:
        await update.message.reply_text(
            f"⏳ Please wait {int(wait)} seconds before requesting proxies again."
        )
        return

    await update.message.reply_text("⏳ Fetching proxies from sources, please wait...")
    try:
        categories = await scrape_proxies(return_categories=True)
        all_proxies = categories.get("all", [])
        http_proxies = categories.get("http", [])
        socks_proxies = categories.get("socks", [])

        if not all_proxies:
            await update.message.reply_text("❌ Could not retrieve proxies at this time.")
            return

        context.user_data["proxy_cache"] = categories

        message = (
            "✅ *Proxy list ready*\n\n"
            f"• *ALL:* {len(all_proxies)}\n"
            f"• *HTTP/HTTPS:* {len(http_proxies)}\n"
            f"• *SOCKS4/SOCKS5:* {len(socks_proxies)}\n\n"
            "*Preview:*\n"
            f"{_preview_text(all_proxies)}\n\n"
            "Use the buttons below to export or refresh the proxy list."
        )

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=_build_main_keyboard(),
        )
    except Exception as exc:
        await update.message.reply_text(f"❌ An error occurred: {exc}")


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export command - show export options."""
    if not context.user_data.get("proxy_cache"):
        await update.message.reply_text(
            "Please use /proxies first to fetch a fresh proxy list, then export it from the buttons."
        )
        return

    await update.message.reply_text(
        "Choose the proxy type to export:",
        reply_markup=_build_main_keyboard(),
    )


async def export_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle export type selection buttons."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    selection = query.data.replace("export_type_", "")
    if selection not in {"all", "http", "socks"}:
        await query.message.reply_text("❌ Unknown proxy type.")
        return

    await query.edit_message_text(
        "Choose whether you want all proxies or only alive ones:",
        reply_markup=_build_live_keyboard(selection),
    )


async def export_live_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle live export choice buttons."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    parts = query.data.split("_")
    if len(parts) != 4 or parts[0] != "export" or parts[1] != "live":
        await query.message.reply_text("❌ Unknown option.")
        return

    selection = parts[2]
    live_mode = parts[3]
    await query.edit_message_text("⏳ Preparing your export file, please wait...")

    try:
        if selection == "all":
            categories = await scrape_proxies(return_categories=True, protocol="all")
            proxy_list = categories.get("all", [])
            filename = "all_proxies.txt"
            caption = "ALL proxies"
        elif selection == "http":
            categories = await scrape_proxies(return_categories=True, protocol="http")
            proxy_list = categories.get("all", [])
            filename = "http_https.txt"
            caption = "HTTP/HTTPS proxies"
        elif selection == "socks":
            categories = await scrape_proxies(return_categories=True, protocol="socks")
            proxy_list = categories.get("all", [])
            filename = "socks4_socks5.txt"
            caption = "SOCKS4/SOCKS5 proxies"
        else:
            await query.message.reply_text("❌ Unknown proxy type.")
            return

        if not proxy_list:
            await query.message.reply_text(f"❌ No proxies found for {caption}.")
            return

        if live_mode == "alive":
            await query.message.reply_text(
                "⏳ Checking live proxies quickly... this may take a few seconds."
            )
            proxy_list = await check_proxies(proxy_list, concurrency=120, timeout=3.0)
            caption = f"{caption} (alive only)"
            filename = filename.replace(".txt", "_alive.txt")

        if not proxy_list:
            await query.message.reply_text(
                "❌ No live proxies were found after verification."
            )
            return

        data_stream = BytesIO("\n".join(proxy_list).encode("utf-8"))
        data_stream.name = filename

        await query.message.reply_document(
            document=InputFile(data_stream, filename=filename),
            filename=filename,
            caption=f"✅ {caption} exported: {len(proxy_list)} proxies",
        )
    except Exception as exc:
        await query.message.reply_text(f"❌ An error occurred during export: {exc}")


async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle refresh proxy list button."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    allowed, wait = _can_execute(context.user_data, "last_proxies")
    if not allowed:
        await query.message.reply_text(
            f"⏳ Please wait {int(wait)} seconds before refreshing again."
        )
        return

    await query.edit_message_text("⏳ Refreshing proxies, please wait...")
    try:
        categories = await scrape_proxies(return_categories=True)
        all_proxies = categories.get("all", [])
        http_proxies = categories.get("http", [])
        socks_proxies = categories.get("socks", [])

        if not all_proxies:
            await query.message.reply_text("❌ Could not refresh proxies at this time.")
            return

        context.user_data["proxy_cache"] = categories
        message = (
            "✅ *Proxy list refreshed*\n\n"
            f"• *ALL:* {len(all_proxies)}\n"
            f"• *HTTP/HTTPS:* {len(http_proxies)}\n"
            f"• *SOCKS4/SOCKS5:* {len(socks_proxies)}\n\n"
            "Use the buttons below to export or refresh again."
        )

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=_build_main_keyboard(),
        )
    except Exception as exc:
        await query.message.reply_text(f"❌ An error occurred: {exc}")


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cancel button action."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    await query.edit_message_text(
        "✅ Action canceled. Use /proxies to fetch a fresh list anytime."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "**📖 Proxy Scraper Bot Help**\n\n"
        "**How to use:**\n"
        "1. Use `/proxies` to fetch a fresh list of public proxies.\n"
        "2. After fetching, use the buttons to export ALL, HTTP, or SOCKS proxies.\n"
        "3. Choose whether to export all proxies or only live ones.\n\n"
        "**Commands:**\n"
        "• `/start` - Show welcome message\n"
        "• `/proxies` - Fetch and preview proxies\n"
        "• `/export` - Show export options\n"
        "• `/help` - Show this help text\n\n"
        "**Notes:**\n"
        "• The bot caches the last proxy fetch for faster export.\n"
        "• Rate limiting prevents spam and repeated fetches.\n"
        "• Live check is fast but may take a few seconds.\n"
        "• Public free proxies often have a low working rate.",
        parse_mode="Markdown"
    )


def main() -> None:
    if not BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN is not set")
        print("Set the environment variable: TELEGRAM_BOT_TOKEN=your_token")
        return

    print("🚀 Starting bot...")
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("proxies", proxies_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(export_type_callback, pattern="^export_type_"))
    application.add_handler(CallbackQueryHandler(export_live_callback, pattern="^export_live_"))
    application.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh_proxies$"))
    application.add_handler(CallbackQueryHandler(cancel_callback, pattern="^cancel_action$"))

    print("✅ Bot connected. Listening for messages...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
