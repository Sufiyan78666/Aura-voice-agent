"""
check_rag_docs.py — Run this in your voice_agent folder to diagnose
what text is actually being extracted from your rag_docs files.
"""
import os
from pathlib import Path

RAG_DOCS_DIR = os.environ.get("RAG_DOCS_DIR", "./rag_docs")

def check_pdf(path):
    try:
        import fitz
        doc = fitz.open(str(path))
        total_text = ""
        for page in doc:
            total_text += page.get_text()
        doc.close()
        clean = total_text.strip()
        if not clean:
            print(f"  ⚠️  SCANNED PDF — no text layer found. Needs OCR!")
        elif len(clean) < 50:
            print(f"  ⚠️  Very little text ({len(clean)} chars): {repr(clean)}")
        else:
            # Show first 300 chars
            preview = clean[:300].replace("\n", " ")
            print(f"  ✅ Text found ({len(clean)} chars). Preview: {repr(preview)}")
    except ImportError:
        print("  ⚠️  pymupdf not installed. Run: pip install pymupdf")
    except Exception as e:
        print(f"  ❌ Error reading PDF: {e}")

def check_docx(path):
    try:
        import docx2txt
        text = docx2txt.process(str(path)).strip()
        if not text:
            print(f"  ⚠️  No text extracted from DOCX!")
        else:
            preview = text[:300].replace("\n", " ")
            print(f"  ✅ Text found ({len(text)} chars). Preview: {repr(preview)}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def check_txt(path):
    for enc in ["utf-8", "utf-16", "latin-1", "cp1252"]:
        try:
            text = path.read_text(encoding=enc).strip()
            preview = text[:300].replace("\n", " ")
            print(f"  ✅ Text ({enc}, {len(text)} chars). Preview: {repr(preview)}")
            return
        except Exception:
            continue
    print(f"  ❌ Could not read with any common encoding.")

docs = list(Path(RAG_DOCS_DIR).rglob("*"))
docs = [f for f in docs if f.is_file() and "extracted_images" not in f.parts]

if not docs:
    print(f"No files found in {RAG_DOCS_DIR}")
else:
    print(f"Found {len(docs)} file(s) in {RAG_DOCS_DIR}\n")
    for f in docs:
        ext = f.suffix.lower()
        print(f"📄 {f.name} ({ext})")
        if ext == ".pdf":
            check_pdf(f)
        elif ext in (".docx", ".doc"):
            check_docx(f)
        elif ext in (".txt", ".md"):
            check_txt(f)
        else:
            print(f"  ℹ️  Skipping {ext} file")
        print()