"""Admin panel texts (English). Russian version: ru_admin.py."""

ADMIN = {
    # ── common
    "a_no_access": "⛔ You don't have access to this section.",
    "a_btn_panel": "⚙️ Admin panel",
    "a_btn_home": "🏠 Panel",
    "a_btn_back": "◀️ Back",
    "a_btn_cancel": "✖️ Cancel",
    "a_btn_yes": "✅ Yes",
    "a_btn_no": "✖️ No",
    "a_btn_help": "📖 Instructions",
    "a_btn_done": "✅ Done",
    "a_btn_delete": "🗑 Delete",
    "a_btn_enable": "✅ Turn on",
    "a_btn_disable": "⛔ Turn off",
    "a_btn_to_shop": "🛍 Open the store as a customer",
    "a_on": "on",
    "a_off": "off",
    "a_yes": "yes",
    "a_no": "no",
    "a_auto": "auto",
    "a_saved": "✅ Saved",
    "a_sent": "✅ Sent",
    "a_bad_value": "⚠️ Invalid value — try again or tap «Cancel».",
    "a_bad_price": "⚠️ Send the price as a number, e.g. <code>9.99</code>",
    "a_bad_json": "⚠️ That's not valid JSON with a \"url\" field. Check quotes and brackets.",
    "a_bad_json_detail": "⚠️ Config error: <code>{error}</code>\nFix it and send again, or tap «Cancel».",
    "a_bad_image": "⚠️ Send a photo, GIF, video or a direct https link to an image.",
    "a_too_long": "⚠️ Too long (max 3500 characters).",
    "a_current": "Now:\n{value}",
    "a_already_processed": "This order has already been processed.",
    "a_send_failed": "⚠️ Not delivered: {error}",
    "a_filled": "filled in",

    # ── startup
    "a_started_first": "🚀 <b>{shop} is running!</b> (@{username})\n\n"
                       "Everything is managed from the admin panel — send /admin.\n\n"
                       "<b>Start in 3 steps:</b>\n"
                       "1️⃣ <b>📦 Products</b> — set prices, enable the products you sell and upload keys\n"
                       "2️⃣ <b>💳 Payments</b> — Telegram Stars already works; add CryptoBot, SBP, cards…\n"
                       "3️⃣ <b>⚙️ Settings</b> — support contact, channel, currency\n\n"
                       "Every section has a «📖 Instructions» button.",
    "a_started": "🟢 <b>{shop}</b> restarted (@{username}). Panel: /admin",

    # ── home
    "a_home": "⚙️ <b>Admin panel · {shop}</b>\n\n"
              "📊 <b>Today:</b> {orders_today} orders · {revenue_today} · +{users_today} users\n"
              "📈 <b>All time:</b> {orders} orders · {revenue} · {users} users\n"
              "⏳ To deliver: <b>{pending}</b> · 🔎 Payments to check: <b>{review}</b>",
    "a_checklist": "🚀 <b>Launch checklist</b>",
    "a_chk_products": "Products on sale: {n}",
    "a_chk_no_keys": "{n} products are out of keys — «🔑 Keys»",
    "a_chk_methods": "Payment methods: {names}",
    "a_chk_channel_ok": "Channel subscription check works",
    "a_chk_channel_err": "Channel check is off: {error}",
    "a_chk_channel_off": "Mandatory channel subscription is not set (optional)",
    "a_chk_support_off": "Support works inside the bot; you can add a contact in Settings (optional)",
    "a_chk_maintenance": "Maintenance mode is ON — customers can't buy",
    "a_btn_catalog": "📦 Products",
    "a_btn_keys": "🔑 Keys",
    "a_btn_orders": "🧾 Orders",
    "a_btn_payments": "💳 Payments",
    "a_btn_users": "👥 Users",
    "a_btn_promo": "🎟 Promo codes",
    "a_btn_broadcast": "📢 Broadcast",
    "a_btn_design": "🎨 Design",
    "a_btn_settings": "⚙️ Settings",
    "a_btn_security": "🛡 Protection",
    "a_btn_admins": "👮 Admins",
    "a_btn_system": "🖥 System",

    # ── catalog
    "a_catalog": "📦 <b>Products</b> · {n} sections\n\n"
                 "Open a section → a product. 🙈 = hidden from customers, ⭐ = shown on the main menu.\n"
                 "Numbers = how many products are inside.",
    "a_btn_add_section": "➕ New section",
    "a_btn_add_sub": "➕ Subsection",
    "a_btn_add_product": "➕ New product",
    "a_section": "📂 <b>{emoji} {name}</b>\n\n"
                 "👁 Visible: {visible} · ⭐ On main menu: {featured}\n"
                 "📝 Description: {desc} · 🖼 Image: {image}\n"
                 "🔗 Direct link: <code>{link}</code>\n\n"
                 "Products and subsections are listed below.",
    "a_btn_rename": "✏️ Name",
    "a_btn_emoji": "😀 Emoji",
    "a_btn_desc": "📝 Description",
    "a_btn_image": "🖼 Image",
    "a_btn_hide": "🙈 Hide",
    "a_btn_show": "👁 Show",
    "a_btn_feature": "⭐ To main menu",
    "a_btn_unfeature": "☆ Off main menu",
    "a_ask_section_name": "📂 Send the section name. You can put an emoji first:\n<code>🤖 AI Subscriptions</code>",
    "a_ask_name": "✏️ Send the new name (up to 64 characters):",
    "a_ask_emoji": "😀 Send one emoji (or «-» to remove):",
    "a_confirm_del_section": "🗑 Delete section «{name}» together with ALL its subsections, products and keys?",
    "a_choose_section": "📂 Choose where to move the product:",
    "a_product": "📦 <b>{name}</b>\n📂 Section: {section}\n\n"
                 "💵 Price: <b>{price}</b>\n🔢 Quantity: {qty}\n🚚 Delivery: {delivery}\n"
                 "🔑 Keys in stock: <b>{stock}</b> · 🛒 Sold: {sold}\n"
                 "👁 On sale: {visible}\n✍️ Asks the customer: {input}\n"
                 "📝 Description: {desc} · 📖 Instruction: {instr}\n"
                 "🔗 Direct link: <code>{link}</code>",
    "a_product_created": "✅ Product created! Now: add keys (or switch delivery to «manually»), "
                         "write a description and check the price.",
    "a_btn_add_keys": "🔑 Add keys",
    "a_btn_export": "📤 Download keys",
    "a_btn_clear": "🧹 Delete all keys",
    "a_btn_price": "💵 Price",
    "a_btn_instruction": "📖 Instruction",
    "a_btn_qty": "🔢 Quantity",
    "a_btn_input": "✍️ Customer data",
    "a_btn_delivery": "🚚 Delivery",
    "a_btn_move": "📂 Move",
    "a_ask_product_name": "📦 Send the product name (as customers will see it):\n<code>ChatGPT Plus · 1 month</code>",
    "a_ask_product_price": "💵 Send the price in {currency}, e.g. <code>9.99</code>\n"
                           "(for quantity products — the price of the number of units you set later)",
    "a_ask_price": "💵 Send the new price in {currency} (for {per} {unit}):",
    "a_confirm_del_product": "🗑 Delete product «{name}» and its {stock} keys?",
    "a_qty_fixed": "1 pc (fixed price)",
    "a_qty_range": "from {min} to {max} · price per {per} {unit} · buttons: {presets}",
    "a_qty_screen": "🔢 <b>Quantity · {name}</b>\n\n"
                    "Minimum: <b>{min}</b> · Maximum: <b>{max}</b>\n"
                    "Price is for: <b>{per}</b> {unit} → {price}\n"
                    "Unit: <b>{unit}</b> · Quick buttons: {presets}\n\n"
                    "If Maximum is greater than 1, the customer chooses the amount (e.g. 50–35000 Stars, "
                    "5–500 $ for Steam). Example for Stars: min 50, max 35000, price 1.60 for 100, unit ⭐, "
                    "buttons 50,100,250,500,1000,2500.",
    "a_btn_qty_min": "Minimum",
    "a_btn_qty_max": "Maximum",
    "a_btn_per": "Price is for N units",
    "a_btn_unit": "Unit",
    "a_btn_presets": "Quick buttons",
    "a_btn_qty_off": "🔄 Make it a normal product (1 pc)",
    "a_ask_qty_min": "🔢 Minimum amount a customer can buy (number):",
    "a_ask_qty_max": "🔢 Maximum amount (number; 1 = normal product):",
    "a_ask_per": "🔢 The price is set for how many units? (e.g. 100 → «$1.60 per 100 ⭐»)",
    "a_ask_unit": "🏷 Unit shown next to the amount, e.g. <code>⭐</code>, <code>$</code>, <code>UC</code> "
                  "(«-» to remove):",
    "a_ask_presets": "⚡ Quick amount buttons separated by commas, e.g. <code>50,100,250,500</code> "
                     "(«-» = automatic):",
    "a_input_none": "Nothing",
    "a_input_username": "Telegram @username of the recipient",
    "a_input_text": "Text (login, Player ID, e-mail…)",
    "a_input_screen": "✍️ <b>What to ask the customer · {name}</b>\n\n"
                      "• <b>Nothing</b> — for keys and links.\n"
                      "• <b>@username</b> — for Stars and Premium: «For me» button + any recipient.\n"
                      "• <b>Text</b> — Steam login, game ID, account e-mail.\n\n"
                      "The answer is shown in the order and sent to you.",
    "a_btn_input_prompt": "✏️ Question text",
    "a_delivery_auto": "🔑 Automatically from keys",
    "a_delivery_manual": "👨‍💻 Manually by the admin",
    "a_delivery_webhook": "🌐 Automatically via API",
    "a_delivery_screen": "🚚 <b>Delivery · {name}</b>\n\n"
                         "• <b>From keys</b> — the bot sends a key/link/account from the stock. If keys run out, "
                         "orders wait in the queue and are delivered automatically when you add keys.\n"
                         "• <b>Manually</b> — after payment you get a notification with a «Deliver» button.\n"
                         "• <b>Via API</b> — the bot calls your supplier's API (Stars, top-ups…). "
                         "If it fails, the order goes to the manual queue.\n\n"
                         "API config: <code>{webhook}</code>",
    "a_btn_webhook": "⚙️ Configure API",
    "a_ask_webhook": "🌐 Send the supplier API config as JSON. Placeholders: {{input}} {{qty}} {{order_id}} "
                     "{{user_id}} {{username}} {{product}} {{price}}.\n\nExample:\n<pre>{example}</pre>",
    "a_loc_cd": "section description",
    "a_loc_pd": "product description",
    "a_loc_pi": "instruction after purchase",
    "a_loc_pp": "question to the customer",
    "a_choose_lang": "🌐 Choose the language for the {what}.\n✅ = filled in. Customers see their own language, "
                     "otherwise English.",
    "a_ask_desc": "📝 Send the description ({lang}). Formatting (bold, links, quotes) is kept.\n«-» — delete.",
    "a_ask_instruction": "📖 Send the instruction the customer receives with the order ({lang}).\n«-» — delete.",
    "a_ask_input_prompt": "✏️ Send the question to the customer ({lang}), e.g. «Send your Steam login».\n«-» — delete.",
    "a_ask_image": "🖼 Send a photo, GIF or video (or a direct link). It will be shown on this screen.",
    "a_btn_remove_image": "🗑 Remove image",

    # ── keys
    "a_keys": "🔑 <b>Keys</b> · {n} products with automatic delivery\n\nTap a product to add keys. ⚠️ = out of keys.",
    "a_keys_empty": "🔑 No products with automatic delivery yet.",
    "a_ask_keys": "🔑 <b>Adding keys · {name}</b>\nIn stock: <b>{stock}</b>\n\n"
                  "Send keys/links/accounts <b>one per line</b> in a message, or a <b>.txt file</b>.\n"
                  "Multi-line items (login + password + 2FA) — separate them with a line <code>---</code>.\n\n"
                  "Duplicates are skipped. You can send several messages, then tap «Done».",
    "a_keys_added": "✅ Added: <b>{added}</b> · duplicates skipped: {dups}\n🔑 In stock: <b>{stock}</b>\n"
                    "📦 Queued orders delivered: {delivered}\n\nSend more or tap «Done».",
    "a_no_keys": "⚠️ No keys found in the message.",
    "a_file_too_big": "⚠️ The file is too big (max 5 MB).",
    "a_no_keys_in_stock": "No keys in stock.",
    "a_confirm_clear": "🧹 Delete all {stock} keys of «{name}»?",
    "a_cleared": "🧹 Deleted keys: {n}",

    # ── orders
    "a_orders_title": "🧾 <b>Orders · {filter}</b> · {total}",
    "a_orders_empty": "Nothing here 🎉",
    "a_ord_work": "To do",
    "a_ord_paid": "All paid",
    "a_ord_review": "To check",
    "a_ord_pending": "To deliver",
    "a_btn_find_order": "🔎 Find by number",
    "a_ask_order_id": "🔎 Send the order number:",
    "a_order_not_found": "Order not found.",
    "a_topup": "Balance top-up",
    "a_order": "🧾 <b>Order #{order}</b>\n\n📦 {product} · {qty} pcs\n💵 {price} · paid {paid}\n💳 {method}\n"
               "📍 {status}\n👤 {user}\n\n📅 Created: {created}\n💳 Paid: {paid_at}\n✅ Delivered: {delivered}",
    "a_order_input": "✍️ Customer data: <code>{value}</code>",
    "a_order_content": "🔑 Delivered:\n{item}",
    "a_status_created": "awaiting payment",
    "a_status_review": "payment needs checking",
    "a_status_paid": "paid",
    "a_status_pending": "waiting for delivery",
    "a_status_delivered": "delivered",
    "a_status_refunded": "refunded",
    "a_status_expired": "expired",
    "a_status_canceled": "canceled",
    "a_btn_deliver": "✍️ Deliver",
    "a_btn_confirm": "✅ Payment received",
    "a_btn_reject": "❌ No payment",
    "a_btn_resend": "📩 Send to the customer again",
    "a_btn_refund_stars": "↩️ Refund Stars",
    "a_btn_refund_balance": "↩️ Refund to balance",
    "a_btn_user": "👤 Customer",
    "a_btn_write": "✉️ Write",
    "a_btn_order": "🧾 Open order",
    "a_ask_delivery": "✍️ <b>Delivering order #{order}</b> · {product}\nQuantity: {qty} · Data: <code>{input}</code>\n\n"
                      "Send what the customer receives (key, link, text). If you've already done it (e.g. sent "
                      "Stars), just send <code>+</code>.",
    "a_delivered_ok": "✅ Delivered to the customer",
    "a_payment_confirmed": "✅ Payment confirmed — the order is being delivered",
    "a_payment_rejected": "❌ Rejected, the customer was notified",
    "a_confirm_refund_stars": "↩️ Refund the Stars for order #{order} to the customer?",
    "a_confirm_refund_balance": "↩️ Refund order #{order} to the customer's balance?",
    "a_refunded": "✅ Refunded",
    "a_refund_failed": "⚠️ Refund failed: {error}",

    # ── notifications
    "a_new_sale": "💰 <b>New sale #{order}</b>\n📦 {product}\n💵 {price} · paid {paid} ({method})\n👤 {user}",
    "a_new_topup": "💰 <b>Top-up #{order}</b>: {amount} · paid {paid} ({method})\n👤 {user}",
    "a_sale_input": "✍️ Data: <code>{value}</code>",
    "a_sale_qty": "🔢 Quantity: {qty}",
    "a_sale_promo": "🎟 Promo {code} (−{discount})",
    "a_pending_stock": "⚠️ <b>Order #{order} is paid, but the keys ran out!</b>\n📦 {product}\n👤 {user}\n\n"
                       "Add keys — the order will be delivered automatically. Or deliver it manually.",
    "a_pending_manual": "👨‍💻 <b>Order #{order} to deliver</b>\n📦 {product}\n👤 {user}\n\n"
                        "Fulfil it and tap «Deliver».",
    "a_low_stock": "⚠️ <b>Few keys left:</b> {product} — {left} pcs.",
    "a_out_of_stock": "⛔ <b>Out of keys:</b> {product}. The product shows «sold out».",
    "a_manual_review": "🔎 <b>Check the payment · order #{order}</b>\n📦 {product}\n💰 {amount} via {method}\n👤 {user}\n\n"
                       "The receipt is above. If the money arrived — tap «Payment received».",
    "a_unmatched_payment": "⚠️ <b>A payment couldn't be matched to an order</b>\n{amount} · charge <code>{charge}</code>\n"
                           "payload <code>{payload}</code>\n👤 {user}\n\nCheck it and refund if needed.",
    "a_webhook_failed": "⚠️ API delivery of order #{order} failed: <code>{error}</code>\nThe order is in the manual queue.",
    "a_provider_error": "⚠️ <b>{method}</b> couldn't create a payment: <code>{error}</code>\nCheck the keys in 💳 Payments.",
    "a_support_msg": "📩 <b>Message to support</b> from {user}:",
    "a_btn_reply": "↩️ Reply",
    "a_btn_add_stock": "🔑 Add keys",

    # ── payments
    "a_methods": "💳 <b>Payment methods</b>\n\n✅ works · ⚠️ on, but keys are missing · ⚪️ off\n\n"
                 "Open a method → fill in the fields (each has a guide) → «Turn on». The order of buttons here "
                 "is the order customers see.",
    "a_btn_add_method": "➕ Add a method (SBP 2, your API…)",
    "a_add_method": "➕ <b>Which method to add?</b>\nYou can add several of the same type, e.g. two «SBP».",
    "a_method_added": "✅ Method added. Fill in the fields and turn it on.",
    "a_method": "💳 <b>{title}</b> ({type})\nStatus: {status}\nCurrency: {currency} · Fee: {fee}%\n",
    "a_method_missing": "⚠️ To turn it on, fill in: <b>{fields}</b>",
    "a_method_fill_first": "Fill in the required fields (marked *) first.",
    "a_btn_title": "🏷 Button title",
    "a_btn_fee": "💸 Fee %",
    "a_btn_test": "🧪 Test connection",
    "a_test_ok": "✅ <b>Connection works:</b> {result}",
    "a_test_fail": "❌ <b>Connection error:</b> <code>{error}</code>",
    "a_ask_field": "✏️ <b>{field}</b>\n{hint}\n\nSend the value («-» — clear). Secret keys are deleted from "
                   "the chat right after saving.",
    "a_choose_value": "Choose: <b>{field}</b>",
    "a_ask_method_title": "🏷 Send the button title, e.g. <code>🏦 SBP</code> («-» — default title):",
    "a_ask_fee": "💸 Fee in % added to the price for this method, e.g. <code>3</code>. A negative number "
                 "is a discount (<code>-5</code>). 0 — no fee.",
    "a_confirm_del_method": "🗑 Delete the payment method «{title}»?",
    "a_ask_custom_api": "🌐 <b>Universal API</b> — connect any payment service with an API (Cashera, Paycore, "
                        "Lava, AAIO…).\n\nSend JSON:\n• <b>create</b> — request that creates a payment and the "
                        "path to the link in the reply (<code>pay_url</code>) and to its id (<code>invoice_id</code>)\n"
                        "• <b>status</b> — request for the status, the path to the status and values meaning "
                        "«paid» / «failed»\n\nPlaceholders: {{amount}} {{amount_int}} {{currency}} {{order_id}} "
                        "{{description}} {{return_url}} {{invoice_id}}\n\nExample:\n<pre>{example}</pre>",
    "a_f_token": "API token",
    "a_f_assets": "Accepted coins",
    "a_f_testnet": "Testnet",
    "a_f_api_key": "API key",
    "a_f_coin": "Coin",
    "a_f_merchant": "Merchant ID",
    "a_f_platform": "Platform",
    "a_f_wallet": "Wallet address",
    "a_f_prefix": "Comment prefix",
    "a_f_shop_id": "Shop ID",
    "a_f_secret_key": "Secret key",
    "a_f_pay_type": "Payment type",
    "a_f_receipt_email": "E-mail for receipts",
    "a_f_vat_code": "VAT code",
    "a_f_api": "API domain",
    "a_f_payer_fee": "Customer pays the fee",
    "a_f_spec": "API config (JSON)",
    "a_f_details": "Requisites",
    "a_f_currency": "Currency",
    "a_f_receipt": "Ask for a receipt",
    "a_fh_details": "What the customer sees, e.g.:\n<code>SBP transfer to +7 900 000-00-00 (T-Bank), Ivan I.\n"
                    "Comment: order {order}</code>\n{amount} and {order} are replaced automatically. "
                    "Formatting is kept.",
    "a_fh_currency": "Currency of the transfer: RUB, USD, EUR, USDT… (empty — the store currency). "
                     "The amount is converted at the current rate.",
    "a_fh_wallet": "Your TON wallet address (Tonkeeper, Telegram Wallet → TON → Receive).",
    "a_fh_api_key": "Optional for TON: a toncenter.com key (@tonapibot) raises the request limit.",
    "a_fh_assets": "Comma-separated, e.g. USDT,TON,BTC. Empty — all coins.",
    "a_fh_receipt_email": "Only if your YooKassa account sends fiscal receipts (54-FZ). Otherwise leave empty.",
    "a_pm_short_stars": "works out of the box",
    "a_pm_short_balance": "customer balance",
    "a_pm_short_cryptobot": "crypto via @CryptoBot",
    "a_pm_short_xrocket": "crypto via @xRocket",
    "a_pm_short_ton": "TON straight to your wallet",
    "a_pm_short_heleket": "crypto gateway Heleket/Cryptomus",
    "a_pm_short_yookassa": "SBP and cards (Russia)",
    "a_pm_short_pally": "SBP and cards (Pally/Paypalych/Cardlink)",
    "a_pm_short_manual": "any requisites + receipt check",
    "a_pm_short_custom": "any service with an API",
    "a_pm_help_stars": "📖 <b>Telegram Stars</b> works without any setup: customers pay with Stars right in "
                       "Telegram (cards, Apple/Google Pay). Prices are converted at ~0.013 $ per ⭐ (Settings → "
                       "Payments to change). Withdraw Stars: @BotFather → your bot → Balance (Fragment).",
    "a_pm_help_balance": "📖 <b>Balance</b>: customers top up the balance with any method and pay for "
                         "orders instantly. Referral rewards and refunds also go to the balance.",
    "a_pm_help_cryptobot": "📖 <b>How to connect CryptoBot</b>\n1. Open @CryptoBot → Crypto Pay → Create App.\n"
                           "2. Copy the <b>API token</b> and paste it into «API token».\n3. Tap «Test connection», "
                           "then «Turn on».\nThe customer pays in USDT/TON/BTC…, the amount is calculated in your "
                           "currency automatically.",
    "a_pm_help_xrocket": "📖 <b>How to connect xRocket</b>\n1. Open @xRocket → Rocket Pay → Create app.\n"
                         "2. Copy the <b>API key</b> into «API key».\n3. Choose the coin (USDT or TONCOIN), "
                         "test and turn on.",
    "a_pm_help_ton": "📖 <b>TON to your wallet</b> — no registration.\n1. Paste your wallet address.\n"
                     "2. Turn on. Each order gets a unique comment; the bot finds the transfer by it and "
                     "confirms the payment automatically (via toncenter.com).",
    "a_pm_help_heleket": "📖 <b>Heleket / Cryptomus</b>\n1. Register at heleket.com (or cryptomus.com), create a "
                         "merchant.\n2. Settings → API: copy the <b>Merchant ID</b> and the <b>payment API key</b>.\n"
                         "3. Choose the platform, test and turn on.",
    "a_pm_help_yookassa": "📖 <b>YooKassa (SBP and cards)</b>\n1. yookassa.ru → Integration → API keys.\n"
                          "2. Paste the <b>shopId</b> and the <b>secret key</b>.\n3. Payment type: «sbp» — SBP only, "
                          "«bank_card» — cards, «any» — the customer chooses.\nPrices are converted to RUB "
                          "at the Central Bank rate.",
    "a_pm_help_pally": "📖 <b>Pally / Paypalych / Cardlink</b> (SBP and cards)\n1. In your account create a shop.\n"
                       "2. Copy the <b>API token</b> and the <b>shop ID</b>.\n3. Choose the API domain of your "
                       "service, test and turn on.",
    "a_pm_help_manual": "📖 <b>Manual transfer</b> — any requisites: SBP by phone, card, PayPal, IBAN, USDT "
                        "address…\n1. Fill in «Requisites» and «Currency».\n2. Turn on.\nThe customer pays, "
                        "sends a receipt — you get it with «Payment received / No payment» buttons. After "
                        "confirmation the order is delivered automatically.\nAdd several such methods for "
                        "different banks («SBP», «SBP 2»…).",
    "a_pm_help_custom": "📖 <b>Universal API</b> — for any payment service not in the list (Cashera, Paycore, "
                        "Lava, AAIO, FreeKassa, your own backend). Fill in «API config (JSON)»: how to create a "
                        "payment and how to check its status. The example is shown when editing.",

    # ── users
    "a_users": "👥 <b>Users</b>\n\nTotal: <b>{total}</b> · new today: {today}\nActive in 24 h: {active} · "
               "blocked the bot: {blocked}",
    "a_btn_find_user": "🔎 Find user",
    "a_btn_banned": "⛔ Banned",
    "a_ask_user": "🔎 Send the user ID, @username or t.me link:",
    "a_user_not_found": "User not found. They must have started the bot.",
    "a_user": "👤 {link}\n\n🌐 Language: {lang} · 📅 Since: {joined}\n👁 Last seen: {seen}\n"
              "💰 Balance: <b>{balance}</b>\n🛒 Purchases: {orders} · {spent}\n🤝 Referrals: {refs} · earned {earned}\n"
              "↪️ Invited by: {referrer}\n📍 Status: {status} · blocked the bot: {blocked}",
    "a_active": "active",
    "a_banned": "⛔ banned",
    "a_banned_until": "⏳ muted until {until}",
    "a_btn_balance": "💰 Balance",
    "a_btn_ban": "⛔ Ban",
    "a_btn_unban": "✅ Unban",
    "a_btn_user_orders": "🧾 Orders",
    "a_ask_balance": "💰 Change the balance:\n<code>+10</code> — add · <code>-5</code> — subtract · "
                     "<code>=20</code> — set exactly",
    "a_ask_reply": "✉️ Send the message for the user (text, photo, file…). It will be delivered on behalf "
                   "of the bot.",
    "a_banned_list": "⛔ <b>Banned and muted</b> · {n}",

    # ── promo
    "a_promos": "🎟 <b>Promo codes</b>\n\nA promo code gives a % discount at checkout. Each customer can use a "
                "code once.",
    "a_btn_add_promo": "➕ New promo code",
    "a_ask_promo": "🎟 Send: <code>CODE PERCENT [LIMIT]</code>\n\nExamples:\n<code>SALE10 10</code> — 10%, "
                   "unlimited\n<code>VIP25 25 100</code> — 25%, first 100 uses",
    "a_bad_promo": "⚠️ Format: <code>CODE PERCENT [LIMIT]</code>, percent 1–99, the code — Latin letters/digits.",
    "a_promo": "🎟 <b>{code}</b>\nDiscount: {percent}%\nUsed: {used} / {max}\nActive: {active}",
    "a_confirm_del_promo": "🗑 Delete promo code {code}?",

    # ── broadcast
    "a_broadcast": "📢 <b>Broadcast</b>\n\nChoose who gets it (number = recipients). Users who blocked the bot "
                   "are excluded automatically.",
    "a_seg_all": "👥 Everyone",
    "a_seg_buyers": "🛒 Customers with purchases",
    "a_seg_nonbuyers": "🆕 No purchases yet",
    "a_ask_broadcast": "📢 Send the message for the broadcast: text, photo, video, GIF or a file — with "
                       "formatting. You'll see a preview before sending.",
    "a_bc_preview": "👆 Preview. Audience: {segment} · {n} people.",
    "a_btn_bc_send": "🚀 Send to {n}",
    "a_btn_bc_button": "🔗 Add a link button",
    "a_ask_bc_button": "🔗 Send: <code>Button text | https://link</code>",
    "a_bc_canceled": "✖️ Broadcast canceled.",
    "a_bc_running": "A broadcast is already running — wait until it finishes.",
    "a_bc_started": "🚀 Broadcast started: {n} recipients. You'll get a report.",
    "a_bc_progress": "📢 Sending… {done}/{total} · delivered {sent}",
    "a_bc_done": "✅ <b>Broadcast finished</b>\nDelivered: {sent} of {total}\nBlocked the bot: {blocked} · "
                 "errors: {failed}",

    # ── design
    "a_design": "🎨 <b>Design</b>\n\nEvery screen has a branded banner. Replace any of them with your photo, "
                "GIF or video — or turn it off. «Default» = built-in banner.",
    "a_slot_main": "Main menu",
    "a_slot_catalog": "Catalog",
    "a_slot_payment": "Payment",
    "a_slot_success": "Order completed",
    "a_slot_profile": "Profile",
    "a_slot_orders": "My orders",
    "a_slot_topup": "Top-up",
    "a_slot_support": "Support",
    "a_slot_faq": "How it works",
    "a_slot_subscribe": "Channel subscription",
    "a_slot_admin": "Admin panel",
    "a_media_default": "default",
    "a_media_custom": "yours",
    "a_media_off": "off",
    "a_slot": "🖼 <b>{name}</b> · {state}",
    "a_btn_media_set": "📤 Upload my own",
    "a_btn_media_reset": "♻️ Default",
    "a_btn_media_off": "🚫 No image",
    "a_ask_media": "📤 Send a photo, GIF (animation) or video. Recommended size 1280×720.",
    "a_btn_shop_name": "🏷 Store name",
    "a_btn_welcome": "👋 Welcome text",
    "a_welcome_screen": "👋 <b>Welcome text</b> on the main menu for each language. ✅ = your text, "
                        "▫️ = built-in.",
    "a_ask_welcome": "👋 Send the welcome text ({lang}). {{name}} — customer's name, {{shop}} — store name. "
                     "Formatting is kept. «-» — back to built-in.",

    # ── settings
    "a_settings": "⚙️ <b>Settings</b>\n\nChoose a group:",
    "a_setgroup_shop": "🏪 Store",
    "a_setgroup_sales": "🛒 Sales",
    "a_setgroup_pay": "💳 Payments",
    "a_setgroup_security": "🛡 Protection",
    "a_ask_setting": "⚙️ <b>{name}</b>\nNow: {value}\n\n{hint}\n\nSend the new value:",
    "a_set_shop_name": "Store name",
    "a_set_currency": "Store currency",
    "a_set_default_lang": "Default language",
    "a_set_support": "Support contact",
    "a_set_channel": "Mandatory channel",
    "a_set_channel_url": "Channel link",
    "a_set_maintenance": "Maintenance mode",
    "a_set_referral_percent": "Referral reward, %",
    "a_set_topup_enabled": "Balance top-up",
    "a_set_topup_min": "Minimum top-up",
    "a_set_low_stock": "Low keys alert at",
    "a_set_show_sold": "Show «Purchased: N»",
    "a_set_show_stock": "Show the number of keys",
    "a_set_invoice_ttl": "Invoice lifetime, min",
    "a_set_max_unpaid": "Max unpaid orders",
    "a_set_star_rate": "Price of 1 ⭐",
    "a_set_rub_rate": "Rate for RUB",
    "a_set_rate_limit": "Request limit",
    "a_set_captcha_flood": "Captcha on flood",
    "a_set_captcha_new": "Captcha for new users",
    "a_set_autoban": "Auto-mute spammers",
    "a_seth_shop_name": "Shown in the welcome text and payments.",
    "a_seth_currency": "All prices are stored in this currency. ⚠️ Changing it does NOT convert existing prices — "
                       "update them after switching.",
    "a_seth_default_lang": "For customers whose Telegram language isn't supported.",
    "a_seth_support": "@username or link of your manager. Empty — support works only inside the bot.",
    "a_seth_channel": "@channel or -100… ID. Add the bot to the channel as an admin. «-» — turn off the check.",
    "a_seth_channel_url": "Only for private channels: the invite link. Usually not needed.",
    "a_seth_maintenance": "Customers see «maintenance»; admins work as usual.",
    "a_seth_referral_percent": "Share of a referral's purchases credited to the inviter's balance. 0 — off.",
    "a_seth_topup_enabled": "«Top up» button in the menu and profile.",
    "a_seth_topup_min": "Amount in the store currency, e.g. 5.",
    "a_seth_low_stock": "You get an alert when this many keys are left.",
    "a_seth_show_sold": "Social proof on the product card.",
    "a_seth_show_stock": "Show «In stock: N» instead of just «In stock».",
    "a_seth_invoice_ttl": "How long a payment link is valid (5–1440).",
    "a_seth_max_unpaid": "Protection from spam orders.",
    "a_seth_star_rate": "How much 1 ⭐ is worth in the store currency. 0 — automatic (~0.013 $).",
    "a_seth_rub_rate": "How many RUB in 1 unit of the store currency for SBP/RUB methods. 0 — Central Bank rate.",
    "a_seth_rate_limit": "Actions per 2 seconds before slowing a user down (default 8).",
    "a_seth_captcha_flood": "Emoji captcha for those who tap too fast.",
    "a_seth_captcha_new": "Emoji captcha at the first /start (protection from bots).",
    "a_seth_autoban": "Temporary mute (5 min → 24 h) for persistent flooding.",
    "a_channel_ok": "✅ Channel connected — the check works.",
    "a_channel_error": "⚠️ Channel check is off: <code>{error}</code>\nAdd the bot to the channel as an "
                       "administrator and send the setting again.",

    # ── security
    "a_security": "🛡 <b>Protection</b>\n\n⛔ Banned/muted now: {banned}\n🚫 Requests dropped: {dropped}\n"
                  "🧩 Captchas shown: {captchas} · 🔇 auto-mutes: {mutes}\n\n"
                  "Limit: {rate} actions / 2 s\nCaptcha on flood: {captcha_flood}\nCaptcha for new users: "
                  "{captcha_new}\nAuto-mute: {autoban}",
    "a_btn_sec_settings": "⚙️ Protection settings",

    # ── admins
    "a_admins": "👮 <b>Admins</b>\n\nOwners (config.py): <code>{owners}</code> — full access.\n"
                "Add staff and choose what they can do.",
    "a_btn_add_admin": "➕ Add admin",
    "a_ask_admin": "👮 Send the ID or @username of the person (they must have started the bot):",
    "a_admin_perms": "👮 <b>{name}</b> — access rights:",
    "a_btn_remove_admin": "🗑 Remove from admins",
    "a_perm_catalog": "📦 Products and keys",
    "a_perm_orders": "🧾 Orders (+ notifications)",
    "a_perm_users": "👥 Users and support",
    "a_perm_payments": "💳 Payment methods",
    "a_perm_promo": "🎟 Promo codes",
    "a_perm_broadcast": "📢 Broadcast",
    "a_perm_design": "🎨 Design",
    "a_perm_settings": "⚙️ Settings and protection",

    # ── system
    "a_system": "🖥 <b>System</b>\n\nMemory: <b>{rss} MB</b> (peak {peak}) · threads {threads}\n"
                "Database: {db} MB · background tasks: {tasks}\nUptime: {uptime}\n"
                "Active in 24 h: {users_active} · blocked the bot: {blocked}\n\n"
                "🛡 banned {banned} · dropped {dropped} · captchas {captchas} · mutes {mutes}",
    "a_btn_gc": "🧹 Free memory",
    "a_btn_backup": "💾 Database backup",
    "a_btn_rates": "💱 Exchange rates",
    "a_backup_caption": "💾 Database backup. Keep it safe: it contains keys and orders.",
    "a_rates_title": "💱 <b>Current rates</b>",

    # ── help
    "a_help_t_start": "🚀 Quick start",
    "a_help_t_catalog": "📦 Products",
    "a_help_t_keys": "🔑 Keys & delivery",
    "a_help_t_qty": "⭐ Stars, Steam, amounts",
    "a_help_t_payments": "💳 Payments",
    "a_help_t_orders": "🧾 Orders",
    "a_help_t_design": "🎨 Design",
    "a_help_t_security": "🛡 Protection",
    "a_help_t_settings": "⚙️ Settings",
    "a_help_start": "🚀 <b>Quick start</b>\n\n"
                    "1️⃣ <b>📦 Products</b>: the demo catalog is already created. Open a product → set the "
                    "<b>price</b> → <b>🔑 Add keys</b> (one per line or a .txt file). Products with keys go on "
                    "sale automatically.\n"
                    "2️⃣ Products delivered by you (Stars, Premium, top-ups) are hidden 🙈 — open them and tap "
                    "«✅ Turn on».\n"
                    "3️⃣ <b>💳 Payments</b>: Stars already work. Add CryptoBot, TON, SBP, cards — open the method, "
                    "paste the keys (the guide is right there) and turn it on.\n"
                    "4️⃣ <b>⚙️ Settings → Store</b>: currency, support contact, channel.\n"
                    "5️⃣ Open the store as a customer and make a test purchase.\n\n"
                    "Everything else works automatically: payment checks, delivery, the queue when keys run out, "
                    "referrals, notifications.",
    "a_help_catalog": "📦 <b>Products</b>\n\n• Sections can be nested (AI → ChatGPT → products).\n"
                      "• «⭐ To main menu» puts a section on the main menu.\n"
                      "• «🙈 Hide» / «✅ Turn on» — remove from sale without deleting.\n"
                      "• Descriptions are per language; formatting (bold, links) is kept.\n"
                      "• 🔗 Direct link to a product/section — use it in channel posts.\n"
                      "• 🖼 Each section/product can have its own photo, GIF or video.",
    "a_help_keys": "🔑 <b>Keys & delivery</b>\n\n<b>From keys:</b> add keys — one per line or a .txt file; for "
                   "multi-line items separate them with <code>---</code>. One purchase = one key (or N keys if "
                   "the customer buys several). If keys run out, paid orders wait and are delivered "
                   "<b>automatically</b> as soon as you add keys.\n\n<b>Manually:</b> after payment you get a "
                   "notification → do the job → «Deliver» → send the text or «+».\n\n<b>Via API:</b> the bot calls "
                   "your supplier (e.g. a Stars/Premium reseller) with the order data.",
    "a_help_qty": "⭐ <b>Stars, Steam and other amounts</b>\n\nFor goods sold by amount, open the product → "
                  "«🔢 Quantity»:\n• <b>Minimum/Maximum</b> — e.g. 50 and 35000\n• <b>Price is for N units</b> — "
                  "e.g. price 1.60 for 100 ⭐\n• <b>Unit</b> — ⭐, $, UC…\n• <b>Quick buttons</b> — 50,100,250…\n\n"
                  "Then «✍️ Customer data»: <b>@username</b> for Stars/Premium (with a «For me» button) or "
                  "<b>text</b> for a Steam login / Player ID. The customer can also type any amount.",
    "a_help_payments": "💳 <b>Payments</b>\n\n• <b>Telegram Stars</b> — works immediately.\n"
                       "• <b>CryptoBot / xRocket / Heleket</b> — crypto, automatic confirmation.\n"
                       "• <b>TON</b> — straight to your wallet, matched by comment.\n"
                       "• <b>YooKassa / Pally</b> — SBP and bank cards.\n"
                       "• <b>Manual transfer</b> — any requisites + receipt check by you.\n"
                       "• <b>Universal API</b> — any other service with an API (Cashera, Paycore…).\n\n"
                       "Amounts are converted from the store currency at current rates. «💸 Fee %» adds a "
                       "markup (or a discount) per method. Each method has a guide and a «Test connection» button.",
    "a_help_orders": "🧾 <b>Orders</b>\n\n«To do» — orders waiting for you: delivery (⏳) and payment checks (🔎). "
                     "You also get a notification with buttons for each.\n• Refund: Stars — back to the customer's "
                     "Stars; any other method — to the customer's balance.\n• /order 123 — open an order by "
                     "number.",
    "a_help_design": "🎨 <b>Design</b>\n\nThe store comes with branded banners (photos and animations). Replace any "
                     "screen with your photo, GIF or MP4: 🎨 Design → screen → «Upload my own». Sections and "
                     "products get their images in 📦 Products → 🖼 Image. The store name and the welcome text "
                     "can be changed here too.",
    "a_help_security": "🛡 <b>Protection</b>\n\n• Users who tap too fast get «not so fast», then an emoji captcha.\n"
                       "• Persistent flooding → temporary mute: 5 min → 30 min → 2 h → 24 h.\n"
                       "• Double taps are ignored, one user's actions run strictly one after another (no double "
                       "orders).\n• Limit of unpaid orders per user.\n• Banned users are ignored completely.\n"
                       "• Optional captcha at the first /start.\n• Secret keys are hidden in logs and removed "
                       "from the chat.",
    "a_help_settings": "⚙️ <b>Settings</b>\n\nEverything is stored in the database and applied instantly — no "
                       "restart needed. Only the bot token and the owner ID live in config.py.",
}
