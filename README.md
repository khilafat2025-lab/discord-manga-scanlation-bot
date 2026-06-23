# 🎌 Discord Manga Scanlation Bot

> **Advanced Manga Scanlation & File Processing Assistant for Discord**
> Built with `discord.py` · Slash Commands · SQLite · EasyOCR · OpenCV · googletrans

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![discord.py](https://img.shields.io/badge/discord.py-2.3+-5865F2.svg)](https://discordpy.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📖 **Manga OCR** | Upload a manga panel → EasyOCR extracts text → translate to 12 languages |
| 🎨 **Auto Colorization** | B&W manga panels → colorized using OpenCV DNN (Zhang et al.) |
| 📄 **File Translator** | Upload `.txt`/`.md`/`.srt` → line-by-line translation → download result |
| 💬 **Text Translator** | Translate text snippets directly in Discord |
| 🔧 **Admin Panel** | Stats, ban/unban, premium, broadcast, audit logs |
| 🌐 **12 Languages** | Urdu · English · Chinese · Russian · Arabic · French · Spanish · German · Japanese · Korean · Hindi · Turkish |
| 🎛️ **Modern UI** | Slash commands, dropdown menus, pagination buttons, progress bars |
| 🔒 **Security** | Rate limiting, input validation, ban system, owner-only commands |

---

## 🚀 Quick Setup (Local)

### 1. Clone the repo
```bash
git clone https://github.com/khilafat2025-lab/discord-manga-scanlation-bot.git
cd discord-manga-scanlation-bot
```

### 2. Install system dependencies
```bash
# Ubuntu/Debian
sudo apt-get install -y tesseract-ocr tesseract-ocr-jpn tesseract-ocr-chi-sim \
    libgl1-mesa-glx libglib2.0-0 libgomp1

# macOS
brew install tesseract tesseract-lang
```

### 3. Install Python dependencies
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in your values (see below)
```

### 5. Run the bot
```bash
python bot.py
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | ✅ **Required** | Bot token from [Discord Developer Portal](https://discord.com/developers/applications) |
| `OWNER_IDS` | ✅ **Required** | Comma-separated Discord user IDs of bot owners |
| `OPENAI_API_KEY` | Optional | GPT-3.5 translation fallback ([get one](https://platform.openai.com/api-keys)) |
| `DEEPL_API_KEY` | Optional | DeepL high-quality translation ([get one](https://www.deepl.com/pro-api)) |
| `LOG_CHANNEL_ID` | Optional | Discord channel ID for audit logs |
| `TEST_GUILD_ID` | Optional | Guild ID for instant slash command sync (dev only) |
| `OCR_COOLDOWN_SECONDS` | Optional | OCR rate limit per user (default: 10) |
| `TRANSLATE_COOLDOWN_SECONDS` | Optional | Translation rate limit (default: 5) |
| `COLORIZE_COOLDOWN_SECONDS` | Optional | Colorization rate limit (default: 30) |
| `MAX_FILE_SIZE_MB` | Optional | Max upload size in MB (default: 10) |

### How to get your Discord bot token:
1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** → name it
3. Go to **Bot** tab → **Reset Token** → copy it
4. Enable **Message Content Intent** under Privileged Gateway Intents
5. Go to **OAuth2 → URL Generator** → select `bot` + `applications.commands`
6. Select permissions: Send Messages, Embed Links, Attach Files, Read Message History
7. Copy the generated URL and invite the bot to your server

### How to get your Discord user ID:
1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click your username → **Copy User ID**

---

## 🌐 Deploy to Render (Free, 24/7)

1. Fork this repo on GitHub
2. Go to [render.com](https://render.com) → **New → Background Worker**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — just add env vars:
   - `DISCORD_TOKEN` → your bot token
   - `OWNER_IDS` → your Discord user ID
5. Click **Deploy**

> **Note:** Render free tier may sleep after inactivity. Use a paid plan or Railway for always-on.

---

## 🚂 Deploy to Railway (Free $5/month credit)

1. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub**
2. Select this repo
3. Add environment variables in the Railway dashboard
4. Railway auto-detects `railway.json` and deploys

---

## 🐳 Deploy with Docker

```bash
docker build -t manga-bot .
docker run -d \
  -e DISCORD_TOKEN=your_token \
  -e OWNER_IDS=your_id \
  -v $(pwd)/data:/app/data \
  manga-bot
```

---

## 📁 Project Structure

```
discord-manga-scanlation-bot/
├── bot.py                    # Main entry point
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker container config
├── render.yaml               # Render deployment config
├── railway.json              # Railway deployment config
├── Procfile                  # Heroku/Render process file
├── .env.example              # Environment variable template
├── .gitignore
│
├── cogs/                     # Discord.py Cogs (feature modules)
│   ├── manga_ocr.py          # OCR + Translation commands
│   ├── colorizer.py          # Manga colorization commands
│   ├── file_translator.py    # File translation commands
│   ├── admin.py              # Admin panel commands
│   └── help.py               # Help & info commands
│
├── utils/                    # Shared utilities
│   ├── config.py             # Environment config manager
│   ├── database.py           # Async SQLite database layer
│   ├── translator.py         # Multi-backend translation
│   └── image_processor.py    # OCR + colorization pipeline
│
├── data/                     # Runtime data (gitignored)
│   ├── manga_bot.db          # SQLite database
│   └── bot.log               # Log file
│
└── temp/                     # Temporary files (gitignored)
```

---

## 🎮 Commands Reference

### Manga OCR
| Command | Description |
|---------|-------------|
| `/scan_manga` | Upload manga panel → OCR → translate |
| `/detect_text` | OCR only, no translation |

### Colorization
| Command | Description |
|---------|-------------|
| `/colorize` | Colorize B&W manga panel (4 styles) |
| `/colorize_help` | How colorization works |

### Translation
| Command | Description |
|---------|-------------|
| `/translate_file` | Upload text file → translate → download |
| `/translate_text` | Translate a text snippet |
| `/languages` | List all supported languages |

### Admin (owner/admin only)
| Command | Description |
|---------|-------------|
| `/admin stats` | Global bot statistics |
| `/admin ban <user>` | Ban a user |
| `/admin unban <user_id>` | Unban a user |
| `/admin premium <user>` | Grant/revoke premium |
| `/admin broadcast <msg>` | Announce to all guilds |
| `/admin logs` | Audit log |
| `/admin recent` | Recent requests |
| `/admin reload <cog>` | Hot-reload a cog |
| `/admin sync` | Sync slash commands |
| `/admin shutdown` | Graceful shutdown |

### General
| Command | Description |
|---------|-------------|
| `/help` | Interactive help menu |
| `/about` | Bot info and stats |
| `/ping` | Latency check |

---

## 🔒 Security Features

- **Rate limiting** per user per command (configurable via env vars)
- **Ban system** — banned users cannot use any commands
- **Owner-only commands** — admin panel restricted to `OWNER_IDS`
- **Input validation** — file type, size, and content checks
- **No token logging** — tokens never appear in logs or output
- **SQLite WAL mode** — safe concurrent database access
- **Non-root Docker** — runs as unprivileged user in container

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- [discord.py](https://github.com/Rapptz/discord.py) — Discord API wrapper
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — OCR engine
- [Zhang et al. 2016](https://richzhang.github.io/colorization/) — Colorization model
- [googletrans](https://github.com/ssut/py-googletrans) — Google Translate wrapper
