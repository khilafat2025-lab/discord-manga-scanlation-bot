"""
utils/image_processor.py
------------------------
Image processing pipeline:

OCR priority:
  1. Google Gemini Vision (via GOOGLE_API_KEY — AI Studio key)
  2. EasyOCR (local, GPU/CPU)
  3. pytesseract (local)

Colorization:
  - OpenCV DNN (anime colorization model if available)
  - PIL-based grayscale-to-color enhancement fallback
"""

import asyncio
import base64
import io
import json
import logging
import os
import ssl
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from utils.config import Config
    GOOGLE_API_KEY = Config.GOOGLE_API_KEY
except Exception:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

_ssl_ctx = ssl.create_default_context()

# ── Provider detection ────────────────────────────────────────────────────────
def get_active_ocr_provider() -> str:
    if GOOGLE_API_KEY:
        return "Google Gemini Vision (AI Studio) ✅"
    try:
        import easyocr  # noqa
        return "EasyOCR (local)"
    except ImportError:
        pass
    try:
        import pytesseract  # noqa
        return "pytesseract (local)"
    except ImportError:
        pass
    return "No OCR provider available"


# ── OCR Provider 1: Gemini Vision ────────────────────────────────────────────
async def _ocr_gemini(image_bytes: bytes) -> Optional[str]:
    """Use Gemini 2.5 Flash to extract text from manga panels."""
    if not GOOGLE_API_KEY:
        return None

    b64 = base64.b64encode(image_bytes).decode()
    # Detect mime type
    mime = "image/jpeg"
    if image_bytes[:4] == b'\x89PNG':
        mime = "image/png"
    elif image_bytes[:4] == b'RIFF':
        mime = "image/webp"

    prompt = (
        "You are an OCR engine specialized in manga panels. "
        "Extract ALL text visible in this image — speech bubbles, narration boxes, sound effects. "
        "Return ONLY the extracted text, one line per text element. "
        "If no text is found, return 'NO_TEXT_FOUND'."
    )
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": b64}},
            ]
        }],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1024},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.5-flash:generateContent?key={GOOGLE_API_KEY}"
    )
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        loop = asyncio.get_event_loop()
        def _call():
            with urllib.request.urlopen(req, timeout=20, context=_ssl_ctx) as r:
                return json.loads(r.read())
        data = await loop.run_in_executor(None, _call)
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text == "NO_TEXT_FOUND" or not text:
            return None
        logger.info("Gemini Vision OCR succeeded")
        return text
    except Exception as e:
        logger.warning(f"Gemini Vision OCR failed: {e}")
        return None


# ── OCR Provider 2: EasyOCR ───────────────────────────────────────────────────
async def _ocr_easyocr(image_bytes: bytes) -> Optional[str]:
    try:
        import easyocr
        import numpy as np
        from PIL import Image

        loop = asyncio.get_event_loop()
        def _run():
            reader = easyocr.Reader(["en", "ja", "ko", "ch_sim"], gpu=False, verbose=False)
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            arr = np.array(img)
            results = reader.readtext(arr, detail=0, paragraph=True)
            return "\n".join(results)

        text = await loop.run_in_executor(None, _run)
        if text.strip():
            logger.info("EasyOCR succeeded")
            return text.strip()
        return None
    except Exception as e:
        logger.warning(f"EasyOCR failed: {e}")
        return None


# ── OCR Provider 3: pytesseract ───────────────────────────────────────────────
async def _ocr_tesseract(image_bytes: bytes) -> Optional[str]:
    try:
        import pytesseract
        from PIL import Image

        loop = asyncio.get_event_loop()
        def _run():
            img = Image.open(io.BytesIO(image_bytes)).convert("L")  # grayscale
            return pytesseract.image_to_string(img, config="--psm 6")

        text = await loop.run_in_executor(None, _run)
        if text.strip():
            logger.info("pytesseract OCR succeeded")
            return text.strip()
        return None
    except Exception as e:
        logger.warning(f"pytesseract failed: {e}")
        return None


# ── Public OCR API ────────────────────────────────────────────────────────────
async def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract text from a manga panel image.
    Priority: Gemini Vision → EasyOCR → pytesseract
    """
    for provider in [_ocr_gemini, _ocr_easyocr, _ocr_tesseract]:
        result = await provider(image_bytes)
        if result:
            return result
    return "No text could be extracted from this image."


# ── Colorization ──────────────────────────────────────────────────────────────
async def colorize_manga_panel(
    image_bytes: bytes,
    style: str = "warm"
) -> bytes:
    """
    Colorize a B&W manga panel.
    Styles: warm, cool, vivid, sepia
    Uses OpenCV DNN if available, else PIL enhancement.
    """
    loop = asyncio.get_event_loop()

    def _colorize():
        from PIL import Image, ImageEnhance, ImageFilter
        import struct

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Try OpenCV DNN colorization
        try:
            import cv2
            import numpy as np

            model_dir = Path(__file__).parent.parent / "assets" / "models"
            proto = model_dir / "colorization_deploy_v2.prototxt"
            weights = model_dir / "colorization_release_v2.caffemodel"
            pts = model_dir / "pts_in_hull.npy"

            if proto.exists() and weights.exists() and pts.exists():
                net = cv2.dnn.readNetFromCaffe(str(proto), str(weights))
                pts_arr = np.load(str(pts))
                class8 = net.getLayerId("class8_ab")
                conv8 = net.getLayerId("conv8_313_rh")
                pts_arr = pts_arr.transpose().reshape(2, 313, 1, 1)
                net.getLayer(class8).blobs = [pts_arr.astype("float32")]
                net.getLayer(conv8).blobs = [np.full([1, 313], 2.606, dtype="float32")]

                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                scaled = img_cv.astype("float32") / 255.0
                lab = cv2.cvtColor(scaled, cv2.COLOR_BGR2LAB)
                resized = cv2.resize(lab, (224, 224))
                L = cv2.split(resized)[0]
                L -= 50
                net.setInput(cv2.dnn.blobFromImage(L))
                ab = net.forward()[0, :, :, :].transpose((1, 2, 0))
                ab = cv2.resize(ab, (img_cv.shape[1], img_cv.shape[0]))
                L_orig = cv2.split(lab)[0]
                colorized = np.concatenate((L_orig[:, :, np.newaxis], ab), axis=2)
                colorized = np.clip(cv2.cvtColor(colorized, cv2.COLOR_LAB2BGR), 0, 1)
                colorized = (colorized * 255).astype("uint8")
                img = Image.fromarray(cv2.cvtColor(colorized, cv2.COLOR_BGR2RGB))
        except Exception:
            pass  # Fall through to PIL enhancement

        # PIL style enhancement
        style_map = {
            "warm": {"color": 1.6, "brightness": 1.15, "contrast": 1.2, "hue_shift": (255, 220, 180)},
            "cool": {"color": 1.5, "brightness": 1.1,  "contrast": 1.15, "hue_shift": (180, 210, 255)},
            "vivid": {"color": 2.0, "brightness": 1.2,  "contrast": 1.3,  "hue_shift": (220, 255, 200)},
            "sepia": {"color": 0.3, "brightness": 1.05, "contrast": 1.1,  "hue_shift": (240, 200, 150)},
        }
        s = style_map.get(style, style_map["warm"])

        # Convert to RGB if grayscale
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Apply color tint
        tint = Image.new("RGB", img.size, s["hue_shift"])
        img = Image.blend(img, tint, alpha=0.25)

        # Enhance
        img = ImageEnhance.Color(img).enhance(s["color"])
        img = ImageEnhance.Brightness(img).enhance(s["brightness"])
        img = ImageEnhance.Contrast(img).enhance(s["contrast"])
        img = ImageEnhance.Sharpness(img).enhance(1.3)

        # Slight blur then sharpen for anime look
        img = img.filter(ImageFilter.SMOOTH_MORE)
        img = ImageEnhance.Sharpness(img).enhance(1.5)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    return await loop.run_in_executor(None, _colorize)


# ── Validation ────────────────────────────────────────────────────────────────
def validate_image(image_bytes: bytes, max_size_mb: float = 8.0) -> tuple[bool, str]:
    """Validate image bytes. Returns (ok, error_message)."""
    if not image_bytes:
        return False, "Empty image data."
    if len(image_bytes) > max_size_mb * 1024 * 1024:
        return False, f"Image too large (max {max_size_mb}MB)."
    # Check magic bytes
    magic = image_bytes[:4]
    if magic[:3] == b'\xff\xd8\xff':
        return True, ""  # JPEG
    if magic == b'\x89PNG':
        return True, ""  # PNG
    if magic[:4] == b'RIFF':
        return True, ""  # WEBP
    if magic[:2] == b'BM':
        return True, ""  # BMP
    if magic[:3] == b'GIF':
        return True, ""  # GIF
    return False, "Unsupported image format. Please use JPG, PNG, WEBP, or GIF."
