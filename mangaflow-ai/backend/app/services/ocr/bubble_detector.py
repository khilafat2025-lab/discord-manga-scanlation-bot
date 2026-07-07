"""
MangaFlow AI - Speech Bubble Detector (OpenCV)
Multi-strategy: white regions + edge-enclosed + heuristic filtering
"""
import cv2
import numpy as np
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class BubbleDetector:
    def __init__(self):
        self.min_area = 500
        self.max_area_ratio = 0.4
        self.min_aspect_ratio = 0.2
        self.max_aspect_ratio = 5.0
        self.min_convexity = 0.7

    def detect(self, image: np.ndarray) -> List[Dict]:
        h, w = image.shape[:2]
        page_area = h * w
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        bubbles = []
        bubbles.extend(self._detect_white_regions(gray, w, h, page_area))
        bubbles.extend(self._detect_edge_enclosed(gray, w, h, page_area))
        bubbles = self._merge_overlapping(bubbles)
        bubbles.sort(key=lambda b: (b["bbox"][1] // 100, -b["bbox"][0]))
        return bubbles

    def _detect_white_regions(self, gray, w, h, page_area):
        bubbles = []
        _, binary = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area or area > page_area * self.max_area_ratio:
                continue
            x, y, bw, bh = cv2.boundingRect(contour)
            aspect = bw / bh if bh > 0 else 0
            if not (self.min_aspect_ratio <= aspect <= self.max_aspect_ratio):
                continue
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            convexity = area / hull_area if hull_area > 0 else 0
            if convexity < self.min_convexity:
                continue
            roi = gray[y:y+bh, x:x+bw]
            white_ratio = np.sum(roi > 200) / roi.size
            if white_ratio < 0.5:
                continue
            bubbles.append({
                "id": f"bubble_{len(bubbles)}", "bbox": [int(x), int(y), int(bw), int(bh)],
                "area": float(area), "convexity": float(convexity),
                "confidence": float(min(convexity * white_ratio, 1.0)), "strategy": "white_region",
                "original_text": "", "translated_text": "", "font_size": 14,
                "font_family": "default", "edited": False,
            })
        return bubbles

    def _detect_edge_enclosed(self, gray, w, h, page_area):
        bubbles = []
        edges = cv2.Canny(gray, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area * 2 or area > page_area * self.max_area_ratio:
                continue
            x, y, bw, bh = cv2.boundingRect(contour)
            aspect = bw / bh if bh > 0 else 0
            if not (self.min_aspect_ratio <= aspect <= self.max_aspect_ratio):
                continue
            roi = gray[y:y+bh, x:x+bw]
            if roi.size == 0:
                continue
            mean_brightness = np.mean(roi)
            if mean_brightness < 150:
                continue
            bubbles.append({
                "id": f"bubble_edge_{len(bubbles)}", "bbox": [int(x), int(y), int(bw), int(bh)],
                "area": float(area), "convexity": 0.8,
                "confidence": float(mean_brightness / 255 * 0.8), "strategy": "edge_enclosed",
                "original_text": "", "translated_text": "", "font_size": 14,
                "font_family": "default", "edited": False,
            })
        return bubbles

    def _merge_overlapping(self, bubbles, iou_threshold=0.3):
        if not bubbles:
            return bubbles
        bubbles.sort(key=lambda b: b["confidence"], reverse=True)
        merged = []
        for bubble in bubbles:
            x1, y1, w1, h1 = bubble["bbox"]
            overlap = False
            for kept in merged:
                x2, y2, w2, h2 = kept["bbox"]
                ix = max(0, min(x1+w1, x2+w2) - max(x1, x2))
                iy = max(0, min(y1+h1, y2+h2) - max(y1, y2))
                intersection = ix * iy
                union = w1*h1 + w2*h2 - intersection
                iou = intersection / union if union > 0 else 0
                if iou > iou_threshold:
                    overlap = True
                    break
            if not overlap:
                merged.append(bubble)
        return merged
