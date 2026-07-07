# 🎌 MangaFlow AI

> AI-powered Manga & Comic Translator — Upload PDF/EPUB, get fully translated output with original artwork preserved.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)

## ✨ Features

- 📄 **Upload PDF & EPUB** manga/comics (up to 2GB)
- 🔍 **AI Speech Bubble Detection** (OpenCV multi-strategy)
- 📝 **OCR** — MangaOCR (Japanese) + PaddleOCR (Chinese/Korean) + Tesseract (fallback)
- 🌐 **AI Translation** — GPT-4o + Gemini + LibreTranslate fallback
- 🎨 **Inpainting** — Remove original text, reconstruct background
- ✍️ **Typesetting** — Insert translated text with auto-sizing
- 📦 **Export** — PDF, EPUB, or ZIP
- 🔄 **Real-time Progress** — WebSocket live logs
- ✏️ **Bubble Editor** — Click any bubble to edit translation
- 👤 **Auth** — Google, GitHub, Email, Guest mode
- 💰 **Pricing** — Free (20 pages/day) + Premium (unlimited)
- 🛡️ **Admin Panel** — User management, queue monitoring, analytics

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React, TypeScript, Tailwind CSS |
| Backend | Python FastAPI |
| Database | PostgreSQL (8 tables) |
| Queue | Redis + Celery |
| Storage | Cloudflare R2 (S3-compatible) |
| OCR | MangaOCR + PaddleOCR + Tesseract |
| PDF | PyMuPDF |
| EPUB | ebooklib |
| Images | OpenCV + Pillow |
| AI | OpenAI GPT-4o + Google Gemini |
| Auth | JWT + OAuth (Google, GitHub) |
| Proxy | Nginx |

## 🚀 Quick Start

```bash
git clone https://github.com/khilafat2025-lab/discord-manga-scanlation-bot.git
cd discord-manga-scanlation-bot/mangaflow-ai
cp backend/.env.example backend/.env
# Edit .env with your API keys
docker-compose up -d
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/api/docs |
| Queue Monitor | http://localhost:5555 |

## 📁 Structure

```
mangaflow-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # auth, projects, admin
│   │   ├── core/                # config, security
│   │   ├── db/                  # async PostgreSQL
│   │   ├── models/              # 8 database tables
│   │   ├── services/
│   │   │   ├── ocr/             # bubble_detector, ocr_engine
│   │   │   ├── translation/     # translator (OpenAI+Gemini)
│   │   │   ├── pipeline/        # inpainter, pdf/epub processors
│   │   │   └── storage.py       # Cloudflare R2
│   │   └── tasks/               # Celery pipeline
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/app/
│       ├── auth/login/
│       ├── dashboard/
│       ├── upload/
│       ├── projects/[id]/
│       ├── admin/
│       └── pricing/
├── nginx/nginx.conf
├── docker-compose.yml
└── README.md
```

## 🗄️ Database Schema (8 Tables)

1. **users** — Auth, roles, usage tracking
2. **projects** — Uploaded manga files
3. **translation_jobs** — Celery job tracking + logs
4. **pages** — Per-page OCR + bubble data
5. **glossaries** — Character/term consistency
6. **api_keys** — API access management
7. **audit_logs** — Security audit trail
8. **payments** — Stripe subscription data

## 🔄 Pipeline

```
Upload → Extract Pages → Detect Bubbles → OCR → Translate → Inpaint → Typeset → Export
```

## 🌍 Languages

Japanese, Chinese, Korean, English, French, German, Spanish, Italian, Portuguese, Russian, Arabic, Turkish, Indonesian, Hindi, Urdu, Bengali, Dutch, Thai, Vietnamese, Persian, and 80+ more.

---
Built with ❤️ by MangaFlow AI Team
