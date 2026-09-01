from app.services.ocr import suggest_fields


def test_suggest_fields_for_traditional_chinese_order():
    text = """報價單號：SO-2026-0001
客戶名稱：星河科技股份有限公司
報價日期：2026/08/31
含稅總計：NT$ 128,500.00"""
    result = suggest_fields(text)
    assert result["quotation_number"] == "SO-2026-0001"
    assert result["customer_name"] == "星河科技股份有限公司"
    assert result["quotation_date"] == "2026-08-31"
    assert result["total_with_tax"] == 128500.0


def test_suggest_fields_uses_right_and_below_spatial_values():
    def line(text, x1, y1, x2, y2):
        return {
            "text": text,
            "confidence": 0.99,
            "page": 1,
            "box": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
        }

    lines = [
        line("客戶名稱", 104, 339, 179, 361),
        line("XYX股份有限公司", 384, 343, 542, 360),
        line("報價單號/Case 編號", 667, 343, 834, 360),
        line("--", 958, 343, 978, 360),
        line("客户單位", 104, 396, 179, 417),
        line("客户", 391, 398, 430, 417),
        line("報價日期", 665, 396, 740, 417),
        line("2025/11/19", 958, 398, 1055, 417),
        line("HCOM5G場域規划設計與施", 388, 568, 634, 582),
        line("專案名稱", 105, 582, 178, 600),
        line("電話", 665, 580, 707, 603),
        line("0911-40230888", 947, 582, 1089, 602),
        line("工", 383, 597, 410, 618),
        line("5%税额", 103, 834, 179, 855),
        line("132,011", 382, 833, 465, 855),
        line("含税優惠僧格", 671, 840, 775, 850),
        line("6,150,000", 1043, 830, 1205, 864),
        line("客戶確認", 238, 1293, 322, 1317),
        line("業務確認", 613, 1292, 697, 1316),
        line("主管核准", 986, 1292, 1071, 1317),
        line("簽章／日期", 235, 1395, 325, 1419),
        line("簽章/日期", 609, 1395, 700, 1419),
        line("簽章/日期", 984, 1397, 1072, 1418),
    ]
    result = suggest_fields("\n".join(item["text"] for item in lines), lines)
    assert result["customer_name"] == "XYX股份有限公司"
    assert result["quotation_number"] == "--"
    assert result["customer_company"] == "客戶"
    assert result["quotation_date"] == "2025-11-19"
    assert result["project_name"] == "HCOM5G場域規劃設計與施工"
    assert result["tax_amount"] == 132011.0
    assert result["discounted_total_with_tax"] == 6150000.0
    assert result["customer_approval"] == "簽章／日期"
    assert result["sales_approval"] == "簽章/日期"
    assert result["manager_approval"] == "簽章/日期"


def test_amount_dot_thousands_and_blank_approval_do_not_capture_footer():
    def line(text, x1, y1, x2, y2):
        return {
            "text": text,
            "confidence": 0.99,
            "page": 1,
            "box": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
        }

    lines = [
        line("未稅總計", 104, 706, 184, 727),
        line("340.220", 316, 709, 397, 727),
        line("客戶確認", 239, 1217, 320, 1238),
        line("業務確認", 613, 1216, 696, 1240),
        line("主管核准", 986, 1216, 1071, 1241),
        line("本訂單依提供之結構化資料製作。", 537, 1753, 766, 1773),
    ]
    result = suggest_fields("\n".join(item["text"] for item in lines), lines)
    assert result["subtotal"] == 340220.0
    assert result["customer_approval"] == ""
    assert result["sales_approval"] == ""
    assert result["manager_approval"] == ""


def test_low_resolution_screenshot_label_variants_and_row_boundaries():
    def line(text, x1, y1, x2, y2):
        return {
            "text": text,
            "confidence": 0.9,
            "page": 1,
            "box": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
        }

    lines = [
        line("訂單", 37, 27, 112, 66),
        line("訂單日期", 749, 24, 804, 40),
        line("2025/11/19", 710, 47, 802, 65),
        line("客户名稱", 29, 179, 96, 197),
        line("Shawn 股份有限公司", 158, 180, 287, 198),
        line("報價單號/Case號", 428, 180, 559, 198),
        line("19232151", 580, 180, 646, 198),
        line("客户单位", 29, 218, 96, 236),
        line("客户", 158, 218, 193, 236),
        line("0911-331-123", 158, 291, 245, 308),
        line("專案名稱", 29, 326, 96, 344),
        line("HCOM 5G 場域規制設計與施工", 158, 327, 371, 345),
        line("業務窗口", 29, 363, 96, 381),
        line("Petter", 158, 365, 199, 382),
        line("報價軍狀態", 429, 364, 499, 382),
        line("已確認", 580, 364, 631, 382),
        line("含税計", 29, 440, 96, 458),
        line("357,231", 158, 440, 220, 458),
    ]
    result = suggest_fields("\n".join(item["text"] for item in lines), lines)

    assert result["customer_name"] == "Shawn 股份有限公司"
    assert result["quotation_number"] == "19232151"
    assert result["customer_company"] == "客戶"
    assert result["project_name"] == "HCOM 5G 場域規劃設計與施工"
    assert result["sales_contact"] == "Petter"
    assert result["quotation_status"] == "已確認"
    assert result["total_with_tax"] == 357231.0


def test_plain_order_title_is_not_treated_as_order_number_label():
    def line(text, x1, y1, x2, y2):
        return {
            "text": text,
            "confidence": 0.99,
            "page": 1,
            "box": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
        }

    lines = [
        line("訂單", 30, 25, 110, 65),
        line("2025/11/19", 710, 47, 802, 65),
    ]
    result = suggest_fields("\n".join(item["text"] for item in lines), lines)
    assert result["quotation_number"] == ""
