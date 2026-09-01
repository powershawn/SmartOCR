import re
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from app.core.config import settings

_ocr_engine = None
_engine_lock = threading.Lock()
_predict_lock = threading.Lock()


def _engine():
    global _ocr_engine
    if _ocr_engine is None:
        with _engine_lock:
            if _ocr_engine is None:
                from paddleocr import PaddleOCR

                kwargs = {
                    "lang": "chinese_cht",
                    "use_doc_orientation_classify": False,
                    "use_doc_unwarping": False,
                    "use_textline_orientation": True,
                }
                if settings.ocr_det_model_dir:
                    kwargs["text_detection_model_dir"] = settings.ocr_det_model_dir
                if settings.ocr_rec_model_dir:
                    kwargs["text_recognition_model_dir"] = settings.ocr_rec_model_dir
                _ocr_engine = PaddleOCR(**kwargs)
    return _ocr_engine


def _images_for(path: Path) -> tuple[list[Path], tempfile.TemporaryDirectory | None]:
    if path.suffix.lower() != ".pdf":
        from PIL import Image, ImageOps

        # Screenshots are often much smaller than scanned PDFs. Upscaling the
        # source before PaddleOCR gives the detector enough pixels to preserve
        # small grey table labels such as 「客戶單位」 and 「報價單狀態」.
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source)
            if image.width >= 1400:
                return [path], None
            scale = min(2.5, 1600 / max(1, image.width))
            temp = tempfile.TemporaryDirectory()
            image_path = Path(temp.name) / "upscaled.png"
            image.resize(
                (round(image.width * scale), round(image.height * scale)),
                Image.Resampling.LANCZOS,
            ).convert("RGB").save(image_path)
        return [image_path], temp
    import pypdfium2 as pdfium

    temp = tempfile.TemporaryDirectory()
    pdf = pdfium.PdfDocument(str(path))
    images = []
    for index in range(len(pdf)):
        image_path = Path(temp.name) / f"page-{index + 1}.png"
        pdf[index].render(scale=2.2).to_pil().save(image_path)
        images.append(image_path)
    return images, temp


def _read_v3_result(result, page: int) -> list[dict]:
    payload = getattr(result, "json", result)
    if callable(payload):
        payload = payload()
    if isinstance(payload, str):
        import json
        payload = json.loads(payload)
    if isinstance(payload, dict) and "res" in payload:
        payload = payload["res"]
    texts = (payload or {}).get("rec_texts", []) if isinstance(payload, dict) else []
    scores = (payload or {}).get("rec_scores", []) if isinstance(payload, dict) else []
    boxes = (payload or {}).get("rec_polys", []) if isinstance(payload, dict) else []
    return [
        {
            "text": text,
            "confidence": round(float(scores[i]) if i < len(scores) else 0, 4),
            "box": boxes[i].tolist() if i < len(boxes) and hasattr(boxes[i], "tolist") else (boxes[i] if i < len(boxes) else None),
            "page": page,
        }
        for i, text in enumerate(texts)
        if str(text).strip()
    ]


def run_ocr(path: Path) -> dict:
    images, temp = _images_for(path)
    lines: list[dict] = []
    try:
        engine = _engine()
        with _predict_lock:
            for page, image in enumerate(images, start=1):
                results = engine.predict(input=str(image))
                for result in results:
                    lines.extend(_read_v3_result(result, page))
    finally:
        if temp:
            temp.cleanup()
    raw_text = "\n".join(line["text"] for line in lines)
    return {"raw_text": raw_text, "lines": lines, "suggested": suggest_fields(raw_text, lines)}


def suggest_fields(text: str, ocr_lines: list[dict] | None = None) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    field_labels = {
        "customer_name": [r"客[戶户]名稱", r"Customer(?:\s*Name)?"],
        "quotation_number": [
            r"報價單號\s*[/／]?\s*Case\s*(?:編)?號", r"報價單號", r"報價單編號",
            r"Case\s*(?:編號|No\.?|Number)", r"訂單(?:編號|號碼)",
            r"Order\s*(?:No\.?|Number)",
        ],
        "customer_company": [r"客[戶户][單单]位", r"公司名稱", r"Company"],
        "quotation_date": [r"報價日期", r"報價日", r"Quotation\s*Date", r"Date"],
        "contact_person": [r"連絡人", r"聯絡人", r"Contact(?:\s*Person)?"],
        "project_department": [r"專案部門", r"部門", r"Department"],
        "contact_phone": [r"連絡電話", r"聯絡電話", r"Contact\s*(?:Phone|Tel)"],
        "salesperson": [r"業務(?:人員)?", r"Sales(?:person)?"],
        "project_name": [r"專案名稱", r"Project(?:\s*Name)?"],
        "phone": [r"電話", r"Tel(?:ephone)?"],
        "sales_contact": [r"業務窗口", r"業務聯絡人", r"Sales\s*Contact"],
        "quotation_status": [r"報價[單军軍]?狀(?:態)?", r"Status"],
        "subtotal": [r"未[稅税]總計", r"未[稅税]合計", r"Subtotal"],
        "tax_amount": [r"5\s*%?\s*[稅税][額额]", r"[稅税][額额]", r"Tax"],
        "total_with_tax": [r"含[稅税](?:總|合)?計", r"Grand\s*Total"],
        "discounted_total_with_tax": [
            r"含[稅税]優惠(?:價|价|僧)格", r"優惠(?:價|价)", r"Discounted\s*Total"
        ],
        "payment_terms": [r"付款條件", r"Payment\s*Terms?"],
        "quotation_valid_until": [r"報價有效期限", r"有效期限", r"Valid\s*Until"],
        "notes": [r"備註", r"Remarks?", r"Notes?"],
        "customer_approval": [r"客[戶户]確認"],
        "sales_approval": [r"業務確認"],
        "manager_approval": [r"主管核准"],
    }
    all_labels = [pattern for patterns in field_labels.values() for pattern in patterns]

    def normalize_value(value: str) -> str:
        return value.translate(str.maketrans({
            "户": "戶", "税": "稅", "额": "額", "价": "價",
            "划": "劃", "与": "與", "结": "結",
        })).strip()

    def matches_label(value: str, patterns: list[str]) -> bool:
        cleaned = value.strip()
        return any(
            re.fullmatch(rf"(?:{pattern})\s*[：:]?", cleaned, re.IGNORECASE)
            for pattern in patterns
        )

    def box_metrics(line: dict) -> tuple[float, float, float, float, float, float] | None:
        box = line.get("box")
        if not box:
            return None
        try:
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
        except (TypeError, ValueError, IndexError):
            return None
        x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
        return x1, y1, x2, y2, (x1 + x2) / 2, (y1 + y2) / 2

    def spatial_value_for(labels: list[str], direction: str, multiline: bool = False) -> str:
        positioned = [line for line in (ocr_lines or []) if box_metrics(line)]
        label_lines = [line for line in positioned if matches_label(str(line.get("text", "")), labels)]
        candidates: list[tuple[tuple[float, float], str, dict, dict]] = []
        for label_line in label_lines:
            label_box = box_metrics(label_line)
            if not label_box:
                continue
            lx1, ly1, lx2, ly2, lcx, lcy = label_box
            label_height = max(1.0, ly2 - ly1)
            right_boundaries = []
            if direction == "right":
                for other_label in positioned:
                    other_box = box_metrics(other_label)
                    if not other_box or other_label.get("page") != label_line.get("page"):
                        continue
                    ox1, _, _, _, _, ocy = other_box
                    if (
                        ox1 > lx2
                        and abs(ocy - lcy) <= 28
                        and matches_label(str(other_label.get("text", "")), all_labels)
                    ):
                        right_boundaries.append(ox1)
            right_boundary = min(right_boundaries) if right_boundaries else float("inf")
            for candidate in positioned:
                if candidate is label_line or candidate.get("page") != label_line.get("page"):
                    continue
                candidate_text = str(candidate.get("text", "")).strip()
                if not candidate_text or matches_label(candidate_text, all_labels):
                    continue
                candidate_box = box_metrics(candidate)
                if not candidate_box:
                    continue
                cx1, cy1, cx2, cy2, ccx, ccy = candidate_box
                candidate_height = max(1.0, cy2 - cy1)
                if direction == "right":
                    row_tolerance = max(18.0, (label_height + candidate_height) * 0.65)
                    if cx1 < lx2 - 4 or cx1 >= right_boundary or abs(ccy - lcy) > row_tolerance:
                        continue
                    candidates.append(((abs(ccy - lcy), cx1 - lx2), candidate_text, label_line, candidate))
                else:
                    column_tolerance = max(85.0, (lx2 - lx1) * 1.4)
                    vertical_gap = cy1 - ly2
                    if vertical_gap < -3 or vertical_gap > 260 or abs(ccx - lcx) > column_tolerance:
                        continue
                    candidates.append(((vertical_gap, abs(ccx - lcx)), candidate_text, label_line, candidate))
        if not candidates:
            return ""
        best = min(candidates, key=lambda item: item[0])
        if not multiline or direction != "right":
            return normalize_value(best[1])

        label_line, best_line = best[2], best[3]
        label_box, best_box = box_metrics(label_line), box_metrics(best_line)
        if not label_box or not best_box:
            return best[1]
        _, _, lx2, _, _, lcy = label_box
        bx1, _, _, _, _, _ = best_box
        right_label_xs = []
        for line in positioned:
            metrics = box_metrics(line)
            if not metrics or line.get("page") != label_line.get("page"):
                continue
            x1, _, _, _, _, cy = metrics
            if x1 > lx2 and abs(cy - lcy) <= 28 and matches_label(str(line.get("text", "")), all_labels):
                right_label_xs.append(x1)
        right_boundary = min(right_label_xs) if right_label_xs else float("inf")
        cell_lines = []
        for line in positioned:
            metrics = box_metrics(line)
            if not metrics or line.get("page") != label_line.get("page"):
                continue
            x1, y1, x2, _, _, cy = metrics
            candidate_text = str(line.get("text", "")).strip()
            if (
                candidate_text
                and not matches_label(candidate_text, all_labels)
                and x1 >= lx2 - 4
                and x1 < right_boundary
                and abs(x1 - bx1) <= 50
                and abs(cy - lcy) <= 26
            ):
                cell_lines.append((y1, x1, candidate_text))
        cell_lines.sort()
        combined = ""
        for _, _, part in cell_lines:
            separator = " " if combined and combined[-1].isascii() and part[0].isascii() else ""
            combined += separator + part
        return normalize_value(combined or best[1])

    def value_for(labels: list[str], direction: str = "right", multiline: bool = False) -> str:
        spatial_value = spatial_value_for(labels, direction, multiline)
        if spatial_value:
            return spatial_value
        for label in labels:
            match = re.search(
                rf"(?:^|\n)\s*(?:{label})\s*[：:]\s*([^\n]+)", text, re.IGNORECASE
            )
            if match:
                return normalize_value(match.group(1))
        return ""

    def date_for(labels: list[str]) -> str | None:
        value = value_for(labels)
        match = re.search(r"(20\d{2})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?", value)
        if not match:
            return None
        try:
            return datetime(*map(int, match.groups())).date().isoformat()
        except ValueError:
            return None

    def amount_for(labels: list[str]) -> float | None:
        value = value_for(labels)
        match = re.search(r"(?:NT\$|TWD|\$)?\s*([\d.,]+)", value)
        if not match:
            return None
        number = match.group(1)
        try:
            if re.fullmatch(r"\d{1,3}(?:[,.]\d{3})+", number):
                return float(number.replace(",", "").replace(".", ""))
            return float(number.replace(",", ""))
        except ValueError:
            return None

    project_name = value_for(field_labels["project_name"], multiline=True)
    project_name = re.sub(r"規[划劃制]設計", "規劃設計", project_name)

    return {
        "customer_name": value_for(field_labels["customer_name"]),
        "quotation_number": value_for(field_labels["quotation_number"]),
        "customer_company": value_for(field_labels["customer_company"]),
        "quotation_date": date_for(field_labels["quotation_date"]),
        "contact_person": value_for(field_labels["contact_person"]),
        "project_department": value_for(field_labels["project_department"]),
        "contact_phone": value_for(field_labels["contact_phone"]),
        "salesperson": value_for(field_labels["salesperson"]),
        "project_name": project_name,
        "phone": value_for(field_labels["phone"]),
        "sales_contact": value_for(field_labels["sales_contact"]),
        "quotation_status": value_for(field_labels["quotation_status"]),
        "subtotal": amount_for(field_labels["subtotal"]),
        "tax_amount": amount_for(field_labels["tax_amount"]),
        "total_with_tax": amount_for(field_labels["total_with_tax"]),
        "discounted_total_with_tax": amount_for(field_labels["discounted_total_with_tax"]),
        "payment_terms": value_for(field_labels["payment_terms"]),
        "quotation_valid_until": value_for(field_labels["quotation_valid_until"]),
        "notes": value_for(field_labels["notes"]),
        "customer_approval": value_for(field_labels["customer_approval"], "below"),
        "sales_approval": value_for(field_labels["sales_approval"], "below"),
        "manager_approval": value_for(field_labels["manager_approval"], "below"),
        "currency": "TWD",
        "line_count": len(lines),
    }
