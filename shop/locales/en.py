from .en_admin import ADMIN

STRINGS = {
    # ── main
    "welcome": "✨ <b>{shop}</b> — digital store\n\n"
               "🤖 AI subscriptions · ⭐ Telegram Stars & Premium\n"
               "🎮 Steam & games · 🎁 Gift cards\n\n"
               "⚡ <b>Instant delivery 24/7</b> — the bot sends your order automatically\n"
               "🔒 <b>Guarantee</b> on every purchase · 💬 support right here\n\n"
               "Choose a section ⤵️",
    "maintenance": "🛠 The store is under maintenance. Please come back in a few minutes!",
    "banned": "⛔ Access to the store is restricted.",
    "spam_slow": "⏳ Not so fast — try again in a second.",
    "spam_wait": "⏳ Too many requests. Try again in {minutes} min.",
    "spam_muted": "🛡 Too many requests in a row. The bot will answer you again in {minutes} min.",
    "captcha_items": "banana,apple,car,cat,ball,balloon,moon,fire,pizza,guitar,dog,star",
    "captcha_flood": "🛡 <b>Quick check</b>\n\nYou're tapping very fast. Tap the <b>{item}</b> to continue:",
    "captcha_new": "👋 <b>Welcome!</b>\n\nTo protect the store from bots, tap the <b>{item}</b>:",
    "captcha_first": "🛡 Please pass the quick check above first.",
    "captcha_ok": "✅ Thanks, you're verified!",
    "captcha_wrong": "❌ Wrong one. Try again — a new check has been sent.",
    "sub_required": "📢 <b>Subscribe to continue</b>\n\nTo use <b>{shop}</b>, please join our channel — "
                    "news, giveaways and promo codes are posted there.\n\n"
                    "1️⃣ Tap «Open channel» and subscribe\n2️⃣ Come back and tap «I've subscribed»",
    "sub_not_found": "❌ Subscription not found yet. Join the channel and try again.",
    "sub_ok": "✅ Thank you for subscribing!",
    "btn_channel": "📢 Open channel",
    "btn_check_sub": "✅ I've subscribed",

    # ── buttons
    "btn_catalog": "🛍 Catalog",
    "btn_profile": "👤 Profile",
    "btn_orders": "📦 My orders",
    "btn_topup": "💰 Top up",
    "btn_support": "💬 Support",
    "btn_faq": "❓ How it works",
    "btn_language": "🌐 Language",
    "btn_menu": "🏠 Menu",
    "btn_back": "◀️ Back",
    "btn_buy": "🛒 Buy",
    "btn_cancel": "✖️ Cancel",
    "btn_back_methods": "◀️ Back to payment methods",
    "btn_buy_more": "🔁 Buy again",
    "btn_change_input": "✏️ Change recipient / data",
    "btn_change_qty": "🔢 Change amount",
    "btn_check_payment": "🔄 Check payment",
    "btn_contact_support": "👤 Contact manager",
    "btn_copy": "📋 Copy",
    "btn_for_me": "👤 For me ({username})",
    "btn_i_paid": "✅ I've paid",
    "btn_new_order": "🔁 New order",
    "btn_open_link": "🔗 Open link",
    "btn_pay_invoice": "Pay {amount}",
    "btn_pay_link": "💳 Pay {amount}",
    "btn_product": "{name} — {price}",
    "btn_product_from": "{name} — {price}",
    "btn_product_oos": "{name} — sold out",
    "btn_promo": "🎟 Enter promo code",
    "btn_promo_remove": "✖️ Remove promo code",
    "btn_resend": "📩 Send again",
    "btn_share": "📤 Share link",
    "btn_write_support": "✍️ Write to support",

    # ── catalog
    "catalog": "🛍 <b>Catalog</b>\n\nChoose a section ⤵️",
    "catalog_empty": "🛍 The catalog is being filled — come back soon!",
    "choose_item": "⤵️ <b>Choose an option</b>",
    "category_empty": "Nothing here yet — check back soon.",
    "card_delivery_auto": "⚡ Delivered <b>automatically</b> right after payment, with instructions.",
    "card_delivery_manual": "👨‍💻 Fulfilled by our team after payment — usually within minutes.",
    "card_guarantee": "🔒 <b>Guarantee:</b> if something goes wrong, we'll replace it or refund you.",
    "card_price": "💵 <b>Price:</b> {price}",
    "card_qty_range": "🔢 Amount: from {min} to {max}",
    "card_in_stock": "✅ In stock",
    "card_stock_count": "✅ In stock: {n}",
    "card_out_of_stock": "⛔ Sold out — new stock is coming soon",
    "card_sold": "🛒 Purchased: {n}",
    "oos_alert": "This product just sold out. Please check back a bit later.",
    "qty_title": "🔢 <b>{product}</b>\n\nPrice: {unit_price}\n\nChoose an amount below or <b>type any number</b> "
                 "from {min} to {max} in the chat.",
    "qty_invalid": "⚠️ Enter a number from {min} to {max}.",
    "qty_no_stock": "⚠️ Only {n} left in stock — choose a smaller amount.",
    "input_prompt_username": "👤 Send the recipient's <b>@username</b>.",
    "input_prompt_text": "✍️ Send the details needed for this order (login, ID or e-mail).",
    "input_bad_username": "⚠️ That doesn't look like a Telegram username. Example: <code>@durov</code>",
    "input_bad_text": "⚠️ Please send a short text message (up to 200 characters).",

    # ── checkout
    "checkout_title": "🧾 <b>Checkout</b>",
    "checkout_product": "📦 {product}",
    "checkout_qty": "🔢 Amount: <b>{qty}</b>",
    "checkout_recipient": "👤 Recipient",
    "checkout_data": "✍️ Your data",
    "checkout_price": "💵 Price: <b>{price}</b>",
    "checkout_promo": "🎟 Promo <b>{code}</b> −{percent}% → <b>{price}</b>",
    "checkout_balance": "💰 Your balance: {balance}",
    "checkout_choose": "💳 <b>Choose a payment method</b> ⤵️",
    "checkout_no_methods": "⚠️ Payment is temporarily unavailable. Please contact support.",
    "promo_enter": "🎟 Send your promo code in a message:",
    "promo_applied": "✅ Promo code applied: −{percent}%",
    "promo_invalid": "❌ This promo code is invalid or has expired.",
    "promo_used": "❌ You've already used this promo code.",
    "too_many_unpaid": "⚠️ You have several unpaid orders. Pay or cancel them first.",
    "pay_unavailable": "⚠️ This payment method is temporarily unavailable. Please choose another one.",
    "payment_error": "⚠️ Couldn't create the payment. Try again or choose another method.",
    "balance_low": "Not enough money on the balance.",
    "payment_ok": "✅ Payment received!",
    "already_paid": "✅ This order is already paid.",
    "order_not_active": "This order is no longer active. Please create a new one.",
    "invoice_desc": "Order #{order} · {product}. Delivered automatically right after payment.",
    "precheckout_invalid": "This invoice is no longer valid. Please create a new order.",
    "precheckout_oos": "Sorry, this product just sold out. You haven't been charged.",
    "pay_title": "💳 <b>Payment · {method}</b>",
    "pay_order": "🧾 Order <b>#{order}</b> · {product}",
    "pay_amount": "💰 Amount: <b>{amount}</b>",
    "pay_amount_exact": "💰 Amount: <b>{amount}</b> (exactly this amount)",
    "pay_invoice_hint": "Tap «Pay» — the payment page will open. The payment is confirmed "
                        "<b>automatically</b>, and your order arrives in this chat. No need to pay twice.",
    "pay_ton_details": "📬 Address: <code>{wallet}</code>\n"
                       "💬 Comment (memo): <code>{memo}</code>\n"
                       "💎 Amount: <code>{amount}</code> TON\n\n"
                       "❗ <b>Be sure to include the comment and the exact amount</b> — otherwise the payment "
                       "won't be matched. Tap «Pay» to open the wallet with everything filled in.",
    "pay_ttl": "⏳ Valid for {minutes} min.",
    "manual_hint": "After the transfer tap «I've paid» — we'll check it and send your order.",
    "manual_hint_receipt": "After the transfer tap «I've paid» and send a <b>screenshot of the receipt</b>.",
    "manual_send_receipt": "📎 <b>Send the receipt</b> — a screenshot or PDF in one message.",
    "manual_sent": "✅ <b>Payment sent for review</b>\n\nOrder #{order}. Usually it takes a few minutes — "
                   "your order will arrive in this chat.",
    "manual_rejected": "❌ We couldn't find your payment for order #{order}. If you did pay, please write to "
                       "support and attach the receipt.",
    "payment_not_found": "⏳ Payment not received yet. If you've just paid — wait a minute and check again.",
    "payment_expired": "⌛ <b>The invoice for order #{order} has expired.</b>\n\nCreate a new order — it takes a "
                       "couple of seconds.",
    "payment_expired_short": "⌛ The invoice has expired. Create a new order.",
    "pay_received_pending": "✅ <b>Payment received!</b>\n\nOrder #{order} · {product}\n\n"
                            "We're preparing your order — it will arrive in this chat automatically. "
                            "You don't need to do anything else.",

    # ── delivery
    "order_done": "✨ <b>Order #{order} completed!</b>\n\n📦 {product}",
    "order_qty": "🔢 Amount: <b>{qty}</b>",
    "order_input": "👤 Details: <b>{value}</b>",
    "order_item": "🔑 <b>Your item:</b>\n{item}",
    "item_in_file": "in the file above 📎",
    "instruction": "📖 <b>Instruction:</b>\n{text}",
    "default_instruction": "Use the item within 24 hours. If something doesn't work — tap «Support» and "
                           "include the order number.",
    "ref_joined": "🎉 A new friend joined via your referral link!",
    "ref_bonus": "🎉 <b>+{amount}</b> to your balance — your referral made a purchase!",
    "balance_gift": "🎁 <b>+{amount}</b> has been added to your balance. Balance: {balance}",
    "refund_balance": "↩️ Order #{order}: <b>{amount}</b> has been refunded to your balance.",
    "refund_stars": "↩️ Order #{order}: {amount} have been refunded.",

    # ── top-up
    "topup_title": "Balance top-up",
    "topup_text": "💰 <b>Top up balance</b>\n\nCurrent balance: <b>{balance}</b>\n\nChoose an amount or "
                  "<b>type any amount</b> in the chat (min. {min}). The balance can be spent on any product.",
    "topup_bad_amount": "⚠️ Enter an amount, for example 25 (minimum {min}).",
    "topup_choose": "💰 Top-up: <b>{amount}</b>\n\n💳 Choose a payment method ⤵️",
    "topup_done": "✅ <b>Balance topped up by {amount}</b>\n\nBalance: <b>{balance}</b>",

    # ── profile & orders
    "profile": "👤 <b>Profile</b>\n\n🆔 ID: <code>{id}</code>\n💰 Balance: <b>{balance}</b>\n"
               "🛒 Purchases: {orders} · {spent}",
    "profile_ref": "🤝 <b>Referral program</b>\nInvite friends and get <b>{percent}%</b> of every purchase they "
                   "make — to your balance.\n\n🔗 Your link:\n<code>{link}</code>\n"
                   "👥 Invited: {invited} · Earned: {earned}",
    "share_text": "Instant AI subscriptions, Telegram Stars and game top-ups 👇",
    "orders_title": "📦 <b>My orders</b> · {total}\n\nTap an order to see the details.",
    "orders_empty": "📦 You don't have any orders yet.",
    "order_info": "🧾 <b>Order #{order}</b>\n\n📦 {product}\n💵 {price} · paid {paid}\n💳 {method}\n📅 {date}\n"
                  "📍 Status: {status}",
    "status_created": "⏳ awaiting payment",
    "status_review": "🔎 payment is being checked",
    "status_paid": "💳 paid",
    "status_pending": "⏳ being prepared",
    "status_delivered": "✅ completed",
    "status_refunded": "↩️ refunded",
    "status_expired": "⌛ expired",
    "status_canceled": "✖️ canceled",
    "language_choose": "🌐 Choose your language:",
    "language_set": "✅ Language changed",

    # ── support & FAQ
    "support": "💬 <b>Support</b>\n\nQuestion about an order or need help choosing? Write to us — we'll reply "
               "right here.\n\nPlease include your <b>order number</b> if you have one.",
    "support_prompt": "✍️ Describe your question in one message. You can attach a screenshot.",
    "support_sent": "✅ Message sent! We'll reply in this chat as soon as possible.",
    "support_reply": "💬 <b>Reply from support:</b>",
    "support_wait": "⏳ You've just written to us — please wait a bit for the reply.",
    "support_too_long": "⚠️ The message is too long. Please make it shorter.",
    "faq": "❓ <b>How it works</b>\n\n"
           "1️⃣ Choose a product in the catalog\n"
           "2️⃣ Pay in a convenient way: {methods}\n"
           "3️⃣ The bot sends your item (key, link or account) with instructions — usually instantly\n\n"
           "<b>Is it safe?</b> Every item is unique and is given only to you. If something goes wrong — we'll "
           "replace it or refund you.\n\n"
           "<b>How long does delivery take?</b> Items marked ⚡ arrive instantly. Others (Stars, Premium, "
           "top-ups) — usually within minutes.\n\n"
           "<b>Need a VPN?</b> Some services aren't available in every country — then a VPN is needed to "
           "activate and use them.\n\n"
           "<b>Problems?</b> Tap «Support» and include the order number.",

    # ── payment methods (default button titles)
    "pm_stars": "⭐ Telegram Stars",
    "pm_balance": "💰 Balance",
    "pm_cryptobot": "💎 CryptoBot",
    "pm_xrocket": "🚀 xRocket",
    "pm_ton": "💠 TON",
    "pm_heleket": "🪙 Crypto",
    "pm_yookassa": "🏦 Card / SBP",
    "pm_pally": "💳 Card / SBP",
    "pm_manual": "🏦 Bank transfer",
    "pm_custom": "💳 Online payment",

    # ── bot profile
    "cmd_start": "Main menu",
    "cmd_catalog": "Catalog",
    "cmd_orders": "My orders",
    "cmd_profile": "Profile & balance",
    "cmd_support": "Support",
    "cmd_language": "Language",
    "bot_description": "✨ Digital goods store: AI subscriptions (ChatGPT, Claude, Gemini…), Telegram Stars & "
                       "Premium, Steam top-ups, game currency and gift cards.\n\n⚡ Instant automatic delivery "
                       "24/7\n🔒 Guarantee on every purchase\n💳 Stars, crypto, cards & SBP",
    "bot_short_description": "AI subscriptions, Telegram Stars, Steam & gift cards — instant delivery 24/7",
}

STRINGS.update(ADMIN)
