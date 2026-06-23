"""
Image processing utilities:
  - OCR text extraction (EasyOCR primary, pytesseract fallback)
  - Manga colorization pipeline (OpenCV + PIL)
  - Image validation and preprocessing
"""

import asyncio
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

log = logging.getLogger("MangaBot.ImageProcessor")


# ── OCR ───────────────────────────────────────────────────────────────────────

async def extract_text_from_image(
    image_bytes: bytes,
    languages: List[str] = None,
) -> Tuple[str, str]:
    """
    Extract text from image bytes using EasyOCR (primary) or pytesseract (fallback).
    Returns (extracted_text, detected_language).
    """
    if languages is None:
        languages = ["en", "ja", "ko", "ch_sim"]  # common manga languages

    loop = asyncio.get_event_loop()

    # ── EasyOCR ───────────────────────────────────────────────────────────────
    try:
        text, lang = await loop.run_in_executor(
            None, _easyocr_extract, image_bytes, languages
        )
        if text.strip():
            return text, lang
    except Exception as exc:
        log.warning(f"EasyOCR failed: {exc}")

    # ── pytesseract fallback ──────────────────────────────────────────────────
    try:
        text = await loop.run_in_executor(None, _tesseract_extract, image_bytes)
        if text.strip():
            return text, "unknown"
    except Exception as exc:
        log.warning(f"pytesseract failed: {exc}")

    return "", "unknown"


def _easyocr_extract(image_bytes: bytes, languages: List[str]) -> Tuple[str, str]:
    import easyocr
    import numpy as np
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(img)

    # Try with requested languages; fall back to English only
    for lang_set in [languages, ["en"]]:
        try:
            reader = easyocr.Reader(lang_set, gpu=False, verbose=False)
            results = reader.readtext(img_array, detail=1, paragraph=True)
            if results:
                text = "\n".join(r[1] for r in results if r[2] > 0.3)
                detected = lang_set[0] if lang_set else "en"
                return text, detected
        except Exception:
            continue

    return "", "en"


def _tesseract_extract(image_bytes: bytes) -> str:
    import pytesseract
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # Preprocess: upscale for better OCR
    w, h = img.size
    if w < 800:
        scale = 800 / w
        img = img.resize((int(w * scale), int(h * scale)))

    return pytesseract.image_to_string(img, config="--psm 6")


# ── Colorization ──────────────────────────────────────────────────────────────

async def colorize_manga_panel(image_bytes: bytes, style: str = "warm") -> bytes:
    """
    Colorize a black-and-white manga panel.
    style: "warm" | "cool" | "vivid" | "sepia"
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _colorize_sync, image_bytes, style)


def _colorize_sync(image_bytes: bytes, style: str = "warm") -> bytes:
    """Synchronous colorization — runs in thread pool."""
    try:
        result = _opencv_dnn_colorize(image_bytes)
        # Apply style tint on top of DNN result
        return _apply_style_tint(result, style)
    except Exception as exc:
        log.warning(f"OpenCV DNN colorize failed ({exc}), using PIL fallback")
        return _pil_artistic_colorize(image_bytes, style)


def _apply_style_tint(image_bytes: bytes, style: str) -> bytes:
    """Apply a style tint to an already-colorized image."""
    from PIL import Image, ImageEnhance
    import numpy as np

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    if style == "cool":
        img_np = np.array(img, dtype=np.float32)
        img_np[:, :, 0] = np.clip(img_np[:, :, 0] * 0.85, 0, 255)  # reduce red
        img_np[:, :, 2] = np.clip(img_np[:, :, 2] * 1.15, 0, 255)  # boost blue
        img = Image.fromarray(img_np.astype(np.uint8))
    elif style == "vivid":
        img = ImageEnhance.Saturation(img).enhance(2.0)
        img = ImageEnhance.Contrast(img).enhance(1.2)
    elif style == "sepia":
        img_np = np.array(img, dtype=np.float32)
        r = np.clip(img_np[:,:,0]*0.393 + img_np[:,:,1]*0.769 + img_np[:,:,2]*0.189, 0, 255)
        g = np.clip(img_np[:,:,0]*0.349 + img_np[:,:,1]*0.686 + img_np[:,:,2]*0.168, 0, 255)
        b = np.clip(img_np[:,:,0]*0.272 + img_np[:,:,1]*0.534 + img_np[:,:,2]*0.131, 0, 255)
        img = Image.fromarray(np.stack([r, g, b], axis=2).astype(np.uint8))
    # "warm" is the default DNN output — no extra tint needed

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _opencv_dnn_colorize(image_bytes: bytes) -> bytes:
    """
    OpenCV DNN colorization using the Zhang et al. model.
    Model files are downloaded on first use to /tmp/colorize_model/.
    """
    import cv2
    import numpy as np
    from PIL import Image

    MODEL_DIR = Path("/tmp/colorize_model")
    MODEL_DIR.mkdir(exist_ok=True)

    prototxt = MODEL_DIR / "colorization_deploy_v2.prototxt"
    caffemodel = MODEL_DIR / "colorization_release_v2.caffemodel"
    pts_npy = MODEL_DIR / "pts_in_hull.npy"

    # Download model files if missing
    model_files = {
        str(prototxt): "https://raw.githubusercontent.com/richzhang/colorization/caffe/colorization/models/colorization_deploy_v2.prototxt",
        str(caffemodel): "https://eecs.berkeley.edu/~rich.zhang/projects/2016_colorization/files/demo_v2/colorization_release_v2.caffemodel",
        str(pts_npy): "https://github.com/richzhang/colorization/raw/caffe/colorization/resources/pts_in_hull.npy",
    }

    import urllib.request
    for path, url in model_files.items():
        if not Path(path).exists():
            log.info(f"Downloading colorization model: {Path(path).name}")
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                raise RuntimeError(f"Could not download model file: {e}")

    # Load model
    net = cv2.dnn.readNetFromCaffe(str(prototxt), str(caffemodel))
    pts = np.load(str(pts_npy))

    class8 = net.getLayerId("class8_ab")
    conv8 = net.getLayerId("conv8_313_rh")
    pts = pts.transpose().reshape(2, 313, 1, 1)
    net.getLayer(class8).blobs = [pts.astype("float32")]
    net.getLayer(conv8).blobs = [np.full([1, 313], 2.606, dtype="float32")]

    # Process image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_np = np.array(img)
    scaled = img_np.astype("float32") / 255.0
    lab = cv2.cvtColor(scaled, cv2.COLOR_RGB2LAB)
    resized = cv2.resize(lab, (224, 224))
    L = cv2.split(resized)[0]
    L -= 50

    net.setInput(cv2.dnn.blobFromImage(L))
    ab = net.forward()[0, :, :, :].transpose((1, 2, 0))
    ab = cv2.resize(ab, (img_np.shape[1], img_np.shape[0]))

    L_orig = cv2.split(lab)[0]
    colorized = np.concatenate((L_orig[:, :, np.newaxis], ab), axis=2)
    colorized = np.clip(cv2.cvtColor(colorized, cv2.COLOR_LAB2RGB), 0, 1)
    colorized = (colorized * 255).astype("uint8")

    out = Image.fromarray(colorized)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def _pil_artistic_colorize(image_bytes: bytes, style: str = "warm") -> bytes:
    """
    Artistic manga colorization using PIL:
    - Converts to grayscale base
    - Applies warm sepia + selective hue mapping
    - Enhances contrast and saturation
    Returns PNG bytes.
    """
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    import numpy as np

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    gray = img.convert("L")

    # Create a warm-toned colorized version
    # Map grayscale values to a manga-style color palette
    gray_np = np.array(gray, dtype=np.float32) / 255.0

    # Skin tones for light areas, dark ink for dark areas
    r = np.clip(gray_np * 1.1 + 0.05, 0, 1)
    g = np.clip(gray_np * 0.95, 0, 1)
    b = np.clip(gray_np * 0.85, 0, 1)

    colored_np = np.stack([r, g, b], axis=2)
    colored_np = (colored_np * 255).astype(np.uint8)
    colored = Image.fromarray(colored_np, "RGB")

    # Enhance
    colored = ImageEnhance.Contrast(colored).enhance(1.3)
    colored = ImageEnhance.Saturation(colored).enhance(1.8)
    colored = ImageEnhance.Sharpness(colored).enhance(1.2)

    # Slight blur to smooth artifacts
    colored = colored.filter(ImageFilter.SMOOTH_MORE)

    buf = io.BytesIO()
    colored.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ── Validation ────────────────────────────────────────────────────────────────

def validate_image(image_bytes: bytes, max_size_mb: int = 10) -> Tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if len(image_bytes) > max_size_mb * 1024 * 1024:
        return False, f"Image too large (max {max_size_mb}MB)"

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        return True, ""
    except Exception as exc:
        return False, f"Invalid image: {exc}"


def preprocess_for_ocr(image_bytes: bytes) -> bytes:
    """Enhance image for better OCR accuracy."""
    from PIL import Image, ImageEnhance, ImageFilter
    import numpy as np

    img = Image.open(io.BytesIO(image_bytes)).convert("L")  # grayscale

    # Upscale if small
    w, h = img.size
    if w < 1000:
        scale = 1000 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Enhance contrast
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    # Threshold (binarize) for cleaner text
    img_np = np.array(img)
    threshold = 128
    img_np = np.where(img_np > threshold, 255, 0).astype(np.uint8)
    img = Image.fromarray(img_np)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()