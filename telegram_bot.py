#!/usr/bin/env python3
"""Telegram bot for proxy scraping and management."""

import asyncio
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from telegram import InputFile, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from proxy_scraper import filter_live_proxies, scrape_proxies

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"⚠️  .env file not found at {env_file}")
    print("   Create a .env file by copying .env.example")

BOT_TOKEN: Final[str | None] = os.getenv("TELEGRAM_BOT_TOKEN")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "🤖 **Proxy Scraper Bot**\n\n"
        "Welcome! I'm a bot that fetches public proxies from multiple sources.\n\n"
        "**Available commands:**\n"
        "/start - Show this message\n"
        "/proxies - Fetch and send proxies\n"
        "/export - Export SOCKS, HTTP, and ALL proxies as .txt files\n"
        "/help - Show detailed help",
        parse_mode="Markdown"
    )


async def proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /proxies command - fetch and send proxies."""
    await update.message.reply_text("⏳ Gathering proxies from multiple sources, please wait...")

    try:
        proxies = await scrape_proxies()
        if not proxies:
            await update.message.reply_text("❌ Could not retrieve proxies at this time.")
            return

        context.user_data["proxies_requested"] = True
        total = len(proxies)
        preview = proxies[:25]

        message = f"✅ **{total} proxies found**\n\n"
        message += "\n".join(preview)
        
        if total > 25:
            message += f"\n\n... and {total - 25} more proxies."
            message += "\n\n_To save all proxies, use /export_"

        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"❌ An error occurred: {exc}")


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export command - ask the user which proxy file to download."""
    if not context.user_data.get("proxies_requested"):
        await update.message.reply_text(
            "❌ Please use /proxies first to load proxies before exporting."
        )
        return

    keyboard = [
        [InlineKeyboardButton("ALL", callback_data="export_all")],
        [InlineKeyboardButton("SOCKS4/SOCKS5", callback_data="export_socks")],
        [InlineKeyboardButton("HTTP/HTTPS", callback_data="export_http")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Choose which proxy list you want to export:",
        reply_markup=reply_markup,
    )


async def export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for export file selection and cleanup options."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    selection = query.data

    if selection in {"export_all", "export_socks", "export_http"}:
        context.user_data["export_selection"] = selection
        keyboard = [
            [InlineKeyboardButton("Yes, remove dead proxies", callback_data="clean_yes")],
            [InlineKeyboardButton("No, export all proxies", callback_data="clean_no")],
        ]
        await query.edit_message_text(
            "Do you want to remove dead proxies before exporting?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    export_selection = context.user_data.get("export_selection")
    if export_selection is None:
        await query.edit_message_text(
            "❌ Export selection lost. Please use /export again."
        )
        return

    await query.edit_message_text("⏳ Preparing the selected proxy file, please wait...")

    try:
        categories = await scrape_proxies(return_categories=True)
        http_proxies = categories.get("http", [])
        socks_proxies = categories.get("socks", [])
        all_proxies = categories.get("all", [])

        if not all_proxies:
            await query.message.reply_text("❌ Could not retrieve proxies for export at this time.")
            return

        if export_selection == "export_all":
            proxy_list = all_proxies
            filename = "all_proxies.txt"
            caption = "ALL proxies"
        elif export_selection == "export_socks":
            proxy_list = socks_proxies
            filename = "socks4_socks5.txt"
            caption = "SOCKS4/SOCKS5 proxies"
        elif export_selection == "export_http":
            proxy_list = http_proxies
            filename = "http_https.txt"
            caption = "HTTP/HTTPS proxies"
        else:
            await query.message.reply_text("❌ Unknown export option.")
            return

        if selection == "clean_yes":
            await query.message.reply_text(
                "⏳ Checking live proxies. This may take up to a minute..."
            )
            proxy_list = await filter_live_proxies(proxy_list)
            caption += " (live only)"

        if not proxy_list:
            await query.message.reply_text(
                f"❌ No proxies are available after the selected cleanup step for {caption}."
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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "**📖 Proxy Scraper Bot Help**\n\n"
        "**How to use:**\n"
        "1. Use `/proxies` to fetch public proxies\n"
        "2. The bot queries multiple reliable sources\n"
        "3. Proxies are deduplicated (no duplicates)\n\n"
        "**Commands:**\n"
        "• `/start` - Show welcome message\n"
        "• `/proxies` - Fetch and preview proxies\n"
        "• `/export` - Download SOCKS, HTTP, and ALL proxies as .txt files\n"
        "• `/help` - Show this help text\n\n"
        "**Export tip:**\n"
        "• After choosing ALL / SOCKS4/SOCKS5 / HTTP/HTTPS, you can remove dead proxies before export\n"
        "\n"
        "**Info:**\n"
        "• Expected proxies: ~7000-11000 (estimated)\n"
        "• Working rate: 2-5% (expected)\n"
        "• Data is refreshed each request\n\n"
        "**Note:** These are public free proxies.",
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
    application.add_handler(CallbackQueryHandler(export_callback, pattern="^(?:export|clean)_"))
    application.add_handler(CommandHandler("help", help_command))

    print("✅ Bot connected. Listening for messages...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
