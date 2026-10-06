"""Starter catalog created on the first run (only if there are no sections yet).

Products with automatic delivery are visible right away: they show «sold out» until keys are added.
Products delivered manually (Stars, Premium, top-ups) start hidden so nobody pays for something the
shop doesn't deliver yet — enable them in /admin → 📦 Products. Prices are examples: change them.
"""
import json

from .loader import db


def L(en, ru):
    return json.dumps({"en": en, "ru": ru}, ensure_ascii=False)


AI_INSTR = L(
    "Open the link within 24 hours, sign in to the account you want to upgrade and confirm the subscription. "
    "If the service isn't available in your country, use a VPN during activation.",
    "Откройте ссылку в течение 24 часов, войдите в нужный аккаунт и подтвердите подписку. "
    "Если сервис недоступен в вашей стране — включите VPN на время активации.",
)
ACCOUNT_INSTR = L(
    "We activate the subscription on your account, usually within 1–12 hours. You'll get a message here.",
    "Подключим подписку на ваш аккаунт, обычно за 1–12 часов. Сообщение придёт в этот чат.",
)
EMAIL_PROMPT = L(
    "✉️ Send the <b>e-mail of your account</b> — we'll activate the subscription on it.",
    "✉️ Отправьте <b>e-mail вашего аккаунта</b> — подключим подписку на него.",
)
CODE_INSTR = L(
    "Redeem the code in the store app or on the website within its validity period. Region of the card is shown "
    "in the product name.",
    "Активируйте код в приложении магазина или на сайте. Регион карты указан в названии товара.",
)
TG_INSTR = L(
    "Delivered to the recipient's Telegram account, usually within 5–30 minutes. Check «Settings → Stars / Premium».",
    "Зачисляется на аккаунт получателя, обычно за 5–30 минут. Проверьте «Настройки → Звёзды / Premium».",
)
GAME_INSTR = L(
    "In-game currency is credited to the Player ID you sent, usually within 5–60 minutes.",
    "Валюта зачисляется на указанный ID игрока, обычно за 5–60 минут.",
)

AI_SERVICES = [
    ("💬", "ChatGPT", "ai_chatgpt.jpg",
     L("<b>ChatGPT</b> by OpenAI — the most popular AI assistant: chat, code, files, image generation, "
       "voice mode and the newest GPT models.",
       "<b>ChatGPT</b> от OpenAI — самый популярный ИИ-ассистент: чат, код, файлы, генерация изображений, "
       "голосовой режим и новейшие модели GPT."),
     [("ChatGPT Plus · 1 month", 1299, "auto", AI_INSTR, ""),
      ("ChatGPT Plus · 12 months", 11900, "auto", AI_INSTR, ""),
      ("ChatGPT Pro · 1 month", 14900, "manual", ACCOUNT_INSTR, "text")]),
    ("🧡", "Claude", "ai_claude.jpg",
     L("<b>Claude</b> by Anthropic — a top model for writing, analysis and coding, with Projects, long "
       "context and Claude Code.",
       "<b>Claude</b> от Anthropic — топовая модель для текстов, анализа и программирования: проекты, длинный "
       "контекст и Claude Code."),
     [("Claude Pro · 1 month", 1399, "auto", AI_INSTR, ""),
      ("Claude Max 5× · 1 month", 7900, "manual", ACCOUNT_INSTR, "text")]),
    ("✨", "Gemini", "ai_gemini.jpg",
     L("<b>Google AI Pro</b> — Gemini Pro, Deep Research, Veo video, image generation and 2 TB of storage.",
       "<b>Google AI Pro</b> — Gemini Pro, Deep Research, видео Veo, генерация изображений и 2 ТБ хранилища."),
     [("Google AI Pro · 1 month", 899, "auto", AI_INSTR, ""),
      ("Google AI Pro · 12 months", 3999, "auto", AI_INSTR, "")]),
    ("🔎", "Perplexity", "ai_perplexity.jpg",
     L("<b>Perplexity Pro</b> — AI search with sources, the best models in one place and file analysis.",
       "<b>Perplexity Pro</b> — ИИ-поиск с источниками, лучшие модели в одном месте и анализ файлов."),
     [("Perplexity Pro · 1 month", 499, "auto", AI_INSTR, ""),
      ("Perplexity Pro · 12 months", 1999, "auto", AI_INSTR, "")]),
    ("⚡", "Grok", "ai_grok.jpg",
     L("<b>SuperGrok</b> by xAI — Grok with higher limits, DeepSearch, Think mode and image generation.",
       "<b>SuperGrok</b> от xAI — Grok с повышенными лимитами, DeepSearch, режимом Think и генерацией картинок."),
     [("SuperGrok · 1 month", 1999, "auto", AI_INSTR, ""),
      ("SuperGrok Heavy · 1 month", 19900, "manual", ACCOUNT_INSTR, "text")]),
    ("🎨", "Midjourney", "ai_midjourney.jpg",
     L("<b>Midjourney</b> — the best AI image generator: art, design, photorealism and video.",
       "<b>Midjourney</b> — лучший генератор изображений: арт, дизайн, фотореализм и видео."),
     [("Midjourney Basic · 1 month", 999, "auto", AI_INSTR, ""),
      ("Midjourney Standard · 1 month", 2699, "auto", AI_INSTR, "")]),
    ("💻", "Cursor", "ai_cursor.jpg",
     L("<b>Cursor Pro</b> — the AI code editor: agents, autocomplete and the best coding models.",
       "<b>Cursor Pro</b> — ИИ-редактор кода: агенты, автодополнение и лучшие модели для программирования."),
     [("Cursor Pro · 1 month", 1699, "auto", AI_INSTR, "")]),
]


async def _product(cid, name, price, delivery, instruction, input_kind="", description="{}", **extra):
    active = 1 if delivery == "auto" else 0
    prompt = EMAIL_PROMPT if input_kind == "text" and "input_prompt" not in extra else extra.pop("input_prompt", "{}")
    await db.add_product(cid, name, price, delivery=delivery, instruction=instruction, input_kind=input_kind,
                         input_prompt=prompt, description=description, is_active=active, **extra)


async def ensure_catalog():
    if await db.count_categories():
        return
    # ── AI subscriptions
    ai = await db.add_category("AI Subscriptions", "🤖", featured=1, image="asset:cat_ai.jpg", description=L(
        "🤖 <b>Premium AI subscriptions</b> — ChatGPT, Claude, Gemini, Grok and more.\n\n"
        "⚡ Instant delivery 24/7 · 🔒 Activation guarantee · 💬 Support in this chat",
        "🤖 <b>Подписки на нейросети</b> — ChatGPT, Claude, Gemini, Grok и другие.\n\n"
        "⚡ Моментальная выдача 24/7 · 🔒 Гарантия активации · 💬 Поддержка в этом чате"))
    for emoji, name, image, desc, products in AI_SERVICES:
        cid = await db.add_category(name, emoji, parent_id=ai, description=desc, image=f"asset:{image}")
        for title, price, delivery, instr, input_kind in products:
            await _product(cid, title, price, delivery, instr, input_kind)

    # ── Telegram
    tg = await db.add_category("Telegram", "⭐", featured=1, image="asset:cat_telegram.jpg", description=L(
        "⭐ <b>Telegram Stars & Premium</b> for yourself or as a gift — just enter the @username.",
        "⭐ <b>Звёзды и Premium в Telegram</b> себе или в подарок — просто укажите @username."))
    await _product(tg, "Telegram Stars", 160, "manual", TG_INSTR, "username", per=100, qty_min=50, qty_max=35000,
                   unit="⭐", presets="50,100,250,500,1000,2500", input_prompt=L(
                       "👤 Who gets the Stars? Send the recipient's <b>@username</b>.",
                       "👤 Кому отправить звёзды? Пришлите <b>@username</b> получателя."),
                   description=L("Any amount from 50 to 35 000 ⭐ — to your account or as a gift.",
                                 "Любое количество от 50 до 35 000 ⭐ — себе или в подарок."))
    for months, price in ((3, 1199), (6, 1599), (12, 2899)):
        await _product(tg, f"Telegram Premium · {months} mo", price, "manual", TG_INSTR, "username",
                       input_prompt=L("👤 Send the recipient's <b>@username</b>.",
                                      "👤 Пришлите <b>@username</b> получателя."),
                       description=L("Premium gift: no ads, 4 GB uploads, faster downloads, stickers and more.",
                                     "Premium подарком: без рекламы, файлы до 4 ГБ, быстрая загрузка, стикеры и др."))

    # ── Steam
    steam = await db.add_category("Steam", "🎮", featured=1, image="asset:cat_steam.jpg", description=L(
        "🎮 <b>Steam</b> — wallet top-ups by login and gift cards.",
        "🎮 <b>Steam</b> — пополнение кошелька по логину и подарочные карты."))
    await _product(steam, "Steam wallet top-up", 106, "manual", L(
        "The amount is credited to the Steam account, usually within 5–30 minutes.",
        "Сумма зачисляется на аккаунт Steam, обычно за 5–30 минут."), "text", qty_min=5, qty_max=500, unit="$",
        presets="5,10,20,50,100", input_prompt=L("🎮 Send your <b>Steam login</b> (not the nickname).",
                                                "🎮 Пришлите <b>логин Steam</b> (не никнейм)."),
        description=L("Top up your Steam wallet by login. You choose the amount.",
                      "Пополнение кошелька Steam по логину. Сумму выбираете сами."))
    for value, price in ((10, 1149), (20, 2249), (50, 5499)):
        await _product(steam, f"Steam Gift Card ${value} (US)", price, "auto", CODE_INSTR)

    # ── Mobile games
    games = await db.add_category("Mobile Games", "🕹", image="asset:cat_games.jpg", description=L(
        "🕹 <b>In-game currency</b> by Player ID — fast and safe.",
        "🕹 <b>Игровая валюта</b> по ID игрока — быстро и безопасно."))
    id_prompt = L("🆔 Send your <b>Player ID</b> (UID).", "🆔 Пришлите ваш <b>ID игрока</b> (UID).")
    for uc, price in ((60, 119), (325, 549), (660, 1049), (1800, 2599)):
        await _product(games, f"PUBG Mobile · {uc} UC", price, "manual", GAME_INSTR, "text", input_prompt=id_prompt)
    for name, price in (("Genshin Impact · Welkin Moon", 499), ("Genshin Impact · 980 Genesis Crystals", 1499)):
        await _product(games, name, price, "manual", GAME_INSTR, "text", input_prompt=id_prompt)

    # ── Gift cards
    gifts = await db.add_category("Gift Cards", "🎁", image="asset:cat_gifts.jpg", description=L(
        "🎁 <b>Gift cards</b> — codes are delivered instantly after payment.",
        "🎁 <b>Подарочные карты</b> — код приходит сразу после оплаты."))
    for name, price in (("Apple Gift Card $10 (US)", 1099), ("Apple Gift Card $25 (US)", 2699),
                        ("Google Play $10 (US)", 1099), ("PlayStation Store $10 (US)", 1149),
                        ("Xbox Gift Card $10 (US)", 1149)):
        await _product(gifts, name, price, "auto", CODE_INSTR)
