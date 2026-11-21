
from pathlib import Path
import fitz  # PyMuPDF

ROOT = Path(r"C:\Users\pete\source\repos\cewe2pdf\tests")
MIN_PAGES = 28

for pdfPath in sorted(ROOT.rglob("*.pdf")):
    try:
        with fitz.open(pdfPath) as pdf:
            pageCount = pdf.page_count

        if pageCount < MIN_PAGES:
            print(f"{pageCount:3} pages  {pdfPath}")

    except Exception as e:
        print(f"ERROR: {pdfPath} ({e})")
