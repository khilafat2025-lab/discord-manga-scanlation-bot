"""
MangaFlow AI - OCR Engine
MangaOCR (Japanese) + PaddleOCR (Chinese/Korean) + Tesseract (fallback)
"""
import numpy as np
import logging
from typing import List, Dict, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)


class OCREngine:
    def __init__(self):
        self._manga_ocr = None
        self._paddle_ocr = None
        self._tesseract_available = False
        self._initialized = False

    def _init_engines(self, source_language: str):
        if self._initialized:
            return
        if source_language == "ja":
            try:
                from manga_ocr import MangaOcr
                self._manga_ocr = MangaOcr()
                logger.info("MangaOCR initialized")
            except ImportError:
                logger.warning("MangaOCR not installed")
        if source_language in ("zh", "ko", "en") or self._manga_ocr is None:
            try:
                from paddleocr import PaddleOCR
                lang_map = {"zh": "ch", "ko": "korean", "en": "en", "ja": "japan"}
                self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang=lang_map.get(source_language, "en"), show_log=False)
                logger.info("PaddleOCR initialized")
            except ImportError:
                logger.warning("PaddleOCR not installed")
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
        except Exception:
            pass
        self._initialized = True

    async def extract_text_from_bubbles(self, image: np.ndarray, bubbles: List[Dict], source_language: str = "ja") -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, self._extract_sync, image, bubbles, source_language)

    def _extract_sync(self, image, bubbles, source_language):
        self._init_engines(source_language)
        for bubble in bubbles:
            x, y, w, h = bubble["bbox"]
            pad = 5
            x1, y1 = max(0, x-pad), max(0, y-pad)
            x2, y2 = min(image.shape[1], x+w+pad), min(image.shape[0], y+h+pad)
            roi = image[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            text, confidence = self._ocr_roi(roi, source_language)
            bubble["original_text"] = text.strip()
            bubble["ocr_confidence"] = confidence
        return bubbles

    def _ocr_roi(self, roi, language) -> Tuple[str, float]:
        if language == "ja" and self._manga_ocr is not None:
            try:
                from PIL import Image as PILImage
                text = self._manga_ocr(PILImage.fromarray(roi))
                return text, 0.9
            except Exception:
                pass
        if self._paddle_ocr is not None:
            try:
                result = self._paddle_ocr.ocr(roi, cls=True)
                if result and result[0]:
                    texts = [line[1][0] for line in result[0] if line and len(line) >= 2]
                    confs = [line[1][1] for line in result[0] if line and len(line) >= 2]
                    if texts:
                        return " ".join(texts), sum(confs) / len(confs)
            except Exception:
                pass
        if self._tesseract_available:
            try:
                import pytesseract
                from PIL import Image as PILImage
                lang_map = {"ja": "jpn", "zh": "chi_sim", "ko": "kor", "en": "eng", "fr": "fra", "de": "deu"}
                text = pytesseract.image_to_string(PILImage.fromarray(roi), lang=lang_map.get(language, "eng"))
                return text.strip(), 0.6
            except Exception:
                pass
        return "", 0.0
