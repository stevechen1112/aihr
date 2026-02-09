"""驗證文檔解析引擎升級是否正確"""
import sys
sys.path.insert(0, ".")

from app.services.document_parser import (
    DocumentParser, TextChunker,
    SUPPORTED_FORMATS, LLAMAPARSE_FORMATS,
    _ensure_llamaparse,
)

print("=== 支援格式 ===")
for ext, fmt in sorted(SUPPORTED_FORMATS.items()):
    lp = "LlamaParse" if fmt in LLAMAPARSE_FORMATS else "Native"
    print(f"  {ext:8s} -> {fmt:10s}  [{lp}]")

print()
print(f"總計: {len(SUPPORTED_FORMATS)} 種副檔名")
print(f"LlamaParse 優先: {len(LLAMAPARSE_FORMATS)} 種格式")

# 驗證各解析器方法存在
checks = [
    ("parse_url", "網頁 URL 擷取"),
    ("_parse_pptx", "PPTX 解析"),
    ("_parse_ppt", "PPT 解析"),
    ("_parse_with_llamaparse", "LlamaParse 高品質解析"),
    ("_parse_pdf", "PDF 解析"),
    ("_parse_docx", "DOCX 解析"),
    ("_parse_excel", "Excel 解析"),
    ("_parse_image", "圖片 OCR"),
    ("_parse_html", "HTML 解析"),
    ("_parse_csv", "CSV 解析"),
    ("_parse_json", "JSON 解析"),
    ("_parse_rtf", "RTF 解析"),
    ("_parse_markdown", "Markdown 解析"),
    ("_parse_txt", "TXT 解析"),
    ("_parse_doc", "DOC 舊格式"),
]

print()
print("=== 解析器方法驗證 ===")
all_ok = True
for method, desc in checks:
    exists = hasattr(DocumentParser, method)
    status = "OK" if exists else "MISSING"
    print(f"  {status:7s} {desc:20s} ({method})")
    if not exists:
        all_ok = False

# 驗證 Celery tasks
print()
print("=== Celery Tasks 驗證 ===")
from app.tasks.document_tasks import process_document_task, process_url_task
print(f"  OK      process_document_task")
print(f"  OK      process_url_task (新增)")

# 驗證 config
print()
print("=== Config 驗證 ===")
from app.config import settings
print(f"  LLAMAPARSE_API_KEY: {'(已設定)' if settings.LLAMAPARSE_API_KEY else '(未設定 - 將使用內建解析器)'}")
print(f"  LLAMAPARSE_ENABLED: {settings.LLAMAPARSE_ENABLED}")
print(f"  VOYAGE_MODEL: {settings.VOYAGE_MODEL}")

# 驗證依賴
print()
print("=== 依賴檢查 ===")
deps = {
    "pptx": "python-pptx (PPT 解析)",
    "trafilatura": "trafilatura (網頁擷取)",
    "nest_asyncio": "nest_asyncio (async 支援)",
    "pdfplumber": "pdfplumber (表格)",
    "tiktoken": "tiktoken (Token 計算)",
    "openpyxl": "openpyxl (Excel)",
    "chardet": "chardet (編碼偵測)",
}
for mod, desc in deps.items():
    try:
        __import__(mod)
        print(f"  OK      {desc}")
    except ImportError:
        print(f"  MISS    {desc}")

# LlamaParse 延遲載入測試
print()
print("=== LlamaParse 延遲載入 ===")
lp_ok = _ensure_llamaparse()
print(f"  {'OK' if lp_ok else 'MISS'}      LlamaParse (延遲載入)")

print()
if all_ok:
    print("=== ALL CHECKS PASSED ===")
else:
    print("=== SOME CHECKS FAILED ===")
    sys.exit(1)
