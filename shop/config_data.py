"""Static reference data."""

# Shop currencies (all supported by CryptoBot as fiat; RUB rates for them come from the CBR).
CURRENCIES = {
    "USD": "$", "EUR": "€", "RUB": "₽", "GBP": "£", "UAH": "₴", "KZT": "₸", "BYN": "Br",
    "UZS": "so'm", "GEL": "₾", "TRY": "₺", "AMD": "֏", "THB": "฿", "INR": "₹", "BRL": "R$",
    "IDR": "Rp", "AZN": "₼", "AED": "AED", "PLN": "zł", "ILS": "₪", "CNY": "¥",
}
# Symbol goes before the amount for these.
PREFIX_SYMBOLS = {"USD", "GBP", "BRL", "INR", "CNY", "ILS", "THB"}
# Non-fiat units used by payment methods and how many decimals to show/charge.
UNIT_DECIMALS = {"XTR": 0, "TON": 3, "USDT": 2, "USDC": 2, "BTC": 6, "ETH": 5, "LTC": 4, "BNB": 4, "TRX": 1,
                 "RUB": 0}
