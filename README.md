# iPhone Duo stock watcher (Apple Store Hong Kong)

Checks every iPhone Duo variant for store pickup continuously (a check about every 30 seconds) on GitHub Actions and sends a
WhatsApp message (and/or Telegram) the moment one is in stock. No computer needs to be on.

## Secrets (Settings → Secrets and variables → Actions)
| Name | Value |
|---|---|
| `WHATSAPP_PHONE` | your number with country code, e.g. `+852XXXXXXXX` |
| `WHATSAPP_APIKEY` | key from CallMeBot (below) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | optional, if you also want Telegram |

## Get the WhatsApp key (free, 1 minute)
1. Save **+34 611 04 87 48** as a contact.
2. From your WhatsApp send it: `I allow callmebot to send me messages`
3. It replies with your API key.

## Test
Actions → "iPhone Duo stock watch" → Run workflow → tick *heartbeat*. You should get a WhatsApp message.
Before 23 Oct Apple answers "pickup not open yet" for the stock check, which is normal; you get a 📣 message when it opens.
