# iPhone Duo stock watcher (Apple Store Hong Kong)

Checks every iPhone Duo variant for store pickup continuously (a check about every 30 seconds) on GitHub Actions and sends a
WhatsApp message (and/or Telegram) the moment one is in stock. No computer needs to be on.

## Secrets (Settings → Secrets and variables → Actions)
| Name | Value |
|---|---|
| `WHATSAPP_PHONE` | your WhatsApp number with country code, e.g. `+852XXXXXXXX` |
| `TEXTMEBOT_APIKEY` | key from textmebot.com (2-day free demo, then US$1/month for messages to yourself) |
| `WHATSAPP_APIKEY` | alternative: CallMeBot key (free, but its number is often full) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | optional, if you also want Telegram |

## Get the TextMeBot key
1. On textmebot.com request a demo ApiKey (arrives by email).
2. Open the two links in that email: add your phone number, then link your WhatsApp (QR scan, like WhatsApp Web).
3. Put the key and your number in the secrets above.

## Test
Actions → "iPhone Duo stock watch" → Run workflow → tick *heartbeat*. You should get a WhatsApp message.
Before 23 Oct Apple answers "pickup not open yet" for the stock check, which is normal; you get a 📣 message when it opens.
