# 🎌 MangaFlow AI — AI Manga & Comic Translator

[![Next.js](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)](https://docker.com)

**Production-ready AI-powered manga and comic translation SaaS platform.**

---

## ✨ Features

### 🔄 Complete Translation Pipeline
- **Upload** PDF or EPUB manga/comics (up to 2GB)
- **Auto-extract** every page with PyMuPDF / ebooklib
- **Detect speech bubbles** using OpenCV contour analysis
- **OCR** with MangaOCR (Japanese) + PaddleOCR (multilingual)
- **AI Translation** via OpenAI GPT-4o or Google Gemini 1.5 Pro
- **Context memory** — consistent character names across all pages
- **Text removal** + AI inpainting to clean original text
- **Typesetting** — insert translated text back into bubbles
- **Export** as PDF, EPUB, or ZIP of images

### 🌍 100+ Languages
Japanese, Chinese, Korean, English, Spanish, French, German, Italian, Portuguese, Russian, Arabic, Hindi, Urdu, Turkish, Thai, Vietnamese, Indonesian, and 80+ more.

### 🎨 Beautiful UI
- Anime-inspired dark theme with glassmorphism
- Real-time progress tracking with live logs
- WebSocket-powered live updates
- Mobile-first responsive design
- Translation editor — click any bubble to edit

### 🔐 Authentication
- Google OAuth, GitHub OAuth, Email/Password, Guest mode

### 👑 Admin Panel
- User management, Queue monitoring, Revenue analytics

---

## 🏗️ Architecture

```
mangaflow-ai/
├── frontend/                    # Next.js 15 + TypeScript + Tailwind CSS
│   └── src/
│       ├── app/(app)/           # Dashboard, Upload, Projects, Editor, Admin
│       ├── app/auth/            # Login/Register
│       ├── app/pricing/         # Pricing page
│       ├── components/          # Reusable components
│       └── lib/api.ts           # Typed API client
│
├── backend/                     # Python FastAPI
│   └── app/
│       ├── api/v1/endpoints/    # auth.py, projects.py, admin.py
│       ├── core/                # config.py, security.py
│       ├── db/                  # SQLAlchemy async
│       ├── models/              # ORM models (8 tables)
│       ├── services/
│       │   ├── ocr/             # bubble_detector.py, ocr_engine.py
│       │   ├── translation/     # translator.py (OpenAI + Gemini)
│       │   ├── pipeline/        # pdf_processor.py, epub_processor.py, inpainter.py
│       │   └── export/          # exporter.py (PDF/EPUB/ZIP)
│       ├── tasks/               # translation_tasks.py (Celery)
│       └── main.py              # FastAPI app entry point
│
├── docker-compose.yml           # Full stack (Postgres + Redis + API + Worker + Frontend + Nginx)
└── backend/.env.example         # Environment variables template
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/khilafat2025-lab/discord-manga-scanlation-bot.git
cd discord-manga-scanlation-bot/mangaflow-ai

# Configure
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Start everything
docker-compose up -d
```

Access at: http://localhost:3000

---

## 📡 API Endpoints

```
POST /api/v1/auth/register       # Register
POST /api/v1/auth/login          # Login
POST /api/v1/auth/guest          # Guest mode
GET  /api/v1/auth/google         # Google OAuth
GET  /api/v1/auth/github         # GitHub OAuth

POST /api/v1/projects/upload     # Upload PDF/EPUB
GET  /api/v1/projects            # List projects
GET  /api/v1/projects/{id}/job   # Job status + live logs
WS   /api/v1/projects/{id}/ws    # WebSocket live progress
GET  /api/v1/projects/{id}/download/{format}  # Download PDF/EPUB/ZIP

GET  /api/v1/admin/stats         # Platform stats
GET  /api/v1/admin/queue         # Queue monitor
```

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Framer Motion |
| Backend | Python FastAPI, Uvicorn, SQLAlchemy async |
| Database | PostgreSQL 16 |
| Queue | Redis + Celery |
| OCR | MangaOCR, PaddleOCR |
| AI | OpenAI GPT-4o, Google Gemini 1.5 Pro |
| PDF | PyMuPDF (fitz) |
| EPUB | ebooklib |
| Images | OpenCV, Pillow |
| Storage | Cloudflare R2 (S3-compatible) |
| Auth | JWT + Google/GitHub OAuth |
| Deploy | Docker Compose + Nginx |

---

## 📄 License

MIT License — Built with ❤️ by MangaFlow AI Team
