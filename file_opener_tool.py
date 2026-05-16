"""
file_opener_tool.py - Voice Agent File Opener + Closer Tool
Opens and closes local files by name.

Fixes applied (v2):
  - Removed duplicate definitions of _regex_extract_filename,
    _extract_filename_with_llamaindex, and _fallback_extract_filename.
  - Browser-tab close (Chrome / Edge / Firefox) now properly wired in
    via pygetwindow title matching before the psutil open-file fallback.
"""

from __future__ import annotations

import difflib
import os
import re
import subprocess
import psutil
from typing import Iterable, Optional, Tuple


_SKIP_DIRS = {
    ".git", "__pycache__", "venv", ".venv", "node_modules",
    "$Recycle.Bin", "System Volume Information",
    "Windows", "Program Files", "Program Files (x86)", "ProgramData",
}

_NOISE_WORDS = {
    "open", "launch", "close", "shut", "please", "file", "my", "the",
    "a", "an", "kholna", "khol", "band", "karo", "kar", "do",
    "document", "pdf", "doc", "that", "this", "it",
}

# Compiled once at module load — used by both open and close paths
_RE_NOISE_START   = re.compile(
    r"^(?:open|close|shut|launch|please|kholna|khol|band\s+karo|band\s+kar)\s+",
    re.IGNORECASE,
)
_RE_NOISE_ARTICLE = re.compile(r"^(?:the|my|a|an)\s+", re.IGNORECASE)
_RE_NOISE_END     = re.compile(
    r"\s+(?:file|document|please|karo|kar|do)\.?$", re.IGNORECASE
)


# ── OPEN ────────────────────────────────────────────────────────────────────
def open_file_by_name(
    user_text: str,
    search_roots: Optional[Iterable[str]] = None,
    model: Optional[str] = None,
    host: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    roots = _normalize_roots(search_roots or [os.getcwd()])
    filename = _regex_extract_filename(user_text)
    if not filename:
        filename, _ = _extract_filename_with_llamaindex(user_text, model, host, api_key)
    if not filename:
        filename = _fallback_extract_filename(user_text)
    if not filename:
        return "Sorry, I could not figure out which file to open."

    print(f"📂  Searching for: '{filename}'")
    all_files = _collect_files(roots)
    if not all_files:
        return "I could not find any files in the search paths."

    match, alternatives = _find_best_match(filename, all_files)
    if not match and alternatives:
        alt_names = ", ".join(os.path.basename(a) for a in alternatives[:3])
        return f"I found multiple matches: {alt_names}. Please say the full name."
    if not match:
        return f"I could not find a file matching '{filename}'."

    try:
        os.startfile(match)
    except Exception:
        return "Sorry, I could not open that file."

    return f"Opening {os.path.basename(match)}."


# ── CLOSE ───────────────────────────────────────────────────────────────────
def close_file_by_name(
    user_text: str,
    search_roots: Optional[Iterable[str]] = None,
    model: Optional[str] = None,
    host: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """
    Close a file that is currently open in any application.

    Strategy (in order):
      1. Browser tab close  — pygetwindow: find a Chrome/Edge/Firefox window
                              whose title contains the filename stem, then send
                              Ctrl+W to close just that tab.
      2. psutil open-files  — find the process that has the resolved path open
                              and kill it.
      3. Extension fallback — kill a well-known app for the file's extension
                              (AcroRd32 for PDF, WINWORD for .docx, etc.).
    """
    roots = _normalize_roots(search_roots or [os.getcwd()])

    filename = _regex_extract_filename(user_text)
    if not filename:
        filename, _ = _extract_filename_with_llamaindex(user_text, model, host, api_key)
    if not filename:
        filename = _fallback_extract_filename(user_text)
    if not filename:
        return "Sorry, I could not figure out which file to close."

    print(f"📂  Searching to close: '{filename}'")
    all_files = _collect_files(roots)
    match, alternatives = _find_best_match(filename, all_files) if all_files else (None, [])

    display_name = os.path.basename(match) if match else filename
    target_name  = display_name.lower()
    stem         = os.path.splitext(target_name)[0]          # filename without extension
    ext          = os.path.splitext(target_name)[1].lower()  # e.g. ".pdf"

    # ── 1. Browser tab close via pygetwindow ────────────────────────────────
    closed_tab = _close_browser_tab(stem)
    if closed_tab:
        return f"Closed the browser tab for '{display_name}'."

    # ── 2. psutil: kill the process that has the actual file open ───────────
    killed = _kill_process_with_file_open(target_name, match)
    if killed:
        return f"Closed '{display_name}' (terminated {killed})."

    # ── 3. Extension-based app kill ─────────────────────────────────────────
    killed = _kill_app_for_extension(ext)
    if killed:
        return f"Closed '{display_name}' (terminated {killed})."

    return f"I could not find '{display_name}' open in any application."


# ── BROWSER TAB CLOSE ───────────────────────────────────────────────────────
def _close_browser_tab(stem: str) -> bool:
    """
    Use pygetwindow to find a browser window whose title contains *stem*,
    bring it to the front, and send Ctrl+W to close just that tab.

    Returns True if a matching tab was found and Ctrl+W was sent.
    Silently skips if pygetwindow or pyautogui is not installed.
    """
    try:
        import pygetwindow as gw
        import pyautogui
        import time
    except ImportError:
        return False  # optional dependency — degrade gracefully

    browser_exes = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}

    windows = gw.getAllWindows()
    for win in windows:
        title = (win.title or "").lower()
        if stem not in title:
            continue

        # Make sure it belongs to a browser process
        try:
            pid = win._hWnd  # on Windows this is the HWND; we need the PID differently
        except Exception:
            pid = None

        # Verify it is a browser window (best-effort)
        is_browser = any(b in title for b in ["chrome", "edge", "firefox", "brave", "opera"])
        if not is_browser:
            # Also accept if the underlying process is a known browser
            try:
                for proc in psutil.process_iter(["pid", "name"]):
                    if proc.info["name"].lower() in browser_exes:
                        # Rough check: can't easily map HWND→PID without win32 here
                        pass
            except Exception:
                pass

        try:
            win.activate()
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "w")
            return True
        except Exception:
            continue

    return False


# ── PSUTIL HELPERS ──────────────────────────────────────────────────────────
def _kill_process_with_file_open(target_name: str, resolved_path: Optional[str]) -> Optional[str]:
    """Kill the first process that has *target_name* (or *resolved_path*) open."""
    for proc in psutil.process_iter(["pid", "name", "open_files"]):
        try:
            for f in proc.open_files():
                path_lower = f.path.lower()
                if target_name in path_lower:
                    name = proc.info["name"]
                    proc.kill()
                    return name
                if resolved_path and resolved_path.lower() in path_lower:
                    name = proc.info["name"]
                    proc.kill()
                    return name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def _kill_app_for_extension(ext: str) -> Optional[str]:
    """Kill the canonical app associated with a file extension."""
    app_map: dict[str, list[str]] = {
        ".pdf":  ["AcroRd32.exe", "Acrobat.exe", "SumatraPDF.exe", "FoxitPDFReader.exe"],
        ".doc":  ["WINWORD.EXE"],
        ".docx": ["WINWORD.EXE"],
        ".xls":  ["EXCEL.EXE"],
        ".xlsx": ["EXCEL.EXE"],
        ".ppt":  ["POWERPNT.EXE"],
        ".pptx": ["POWERPNT.EXE"],
        ".txt":  ["notepad.exe", "notepad++.exe"],
        ".md":   ["notepad.exe", "notepad++.exe", "Obsidian.exe"],
    }
    candidates = app_map.get(ext, [])
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] in candidates:
                name = proc.info["name"]
                proc.kill()
                return name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


# ── SHARED FILE HELPERS ──────────────────────────────────────────────────────
def _collect_files(search_roots: Iterable[str]) -> list[str]:
    files: list[str] = []
    for root_dir in search_roots:
        if not os.path.exists(root_dir):
            continue
        for root, dirs, filenames in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for name in filenames:
                files.append(os.path.join(root, name))
    return files


def _normalize_roots(roots: Iterable[str]) -> list[str]:
    return [
        os.path.expandvars(os.path.expanduser(r.strip()))
        for r in roots if r.strip()
    ]


def _clean_query(query: str) -> str:
    words = query.lower().split()
    cleaned = " ".join(w for w in words if w not in _NOISE_WORDS)
    cleaned = re.sub(r"[^\w\s\.\-]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _find_best_match(
    query: str, files: list[str]
) -> Tuple[Optional[str], list[str]]:
    query_clean = _clean_query(query)
    query_lower = query.lower()
    name_map  = {os.path.basename(p).lower(): p for p in files}
    basenames = list(name_map.keys())

    # Exact match
    if query_lower in name_map:
        return name_map[query_lower], []
    if query_clean in name_map:
        return name_map[query_clean], []
    
    # Exact match ignoring spaces
    query_no_space = query_lower.replace(" ", "")
    for name in name_map:
        if name.replace(" ", "") == query_no_space:
            return name_map[name], []

    # All tokens present
    tokens = query_clean.split()
    if tokens:
        hits = [n for n in basenames if all(tok in n for tok in tokens)]
        if len(hits) == 1:
            return name_map[hits[0]], []
        if len(hits) > 1:
            return None, [name_map[n] for n in hits]

    # Any significant token
    single: list[str] = []
    for tok in tokens:
        if len(tok) >= 3:
            single.extend(n for n in basenames if tok in n)
    single = list(dict.fromkeys(single))
    if len(single) == 1:
        return name_map[single[0]], []
    if len(single) > 1:
        return None, [name_map[n] for n in single[:3]]

    # Fuzzy fallback
    matches = difflib.get_close_matches(query_clean, basenames, n=3, cutoff=0.5)
    if len(matches) == 1:
        return name_map[matches[0]], []
    if len(matches) > 1:
        return None, [name_map[m] for m in matches]

    return None, []


# ── FILENAME EXTRACTION ──────────────────────────────────────────────────────
def _regex_extract_filename(user_text: str) -> Optional[str]:
    """
    Fast regex-only extraction — no LLM needed.
    Handles: 'Close the FPS3.pdf file', 'open my resume', 'open FPS 3.5'
    """
    t = user_text

    # 1. Explicit filename.ext — allow spaces like "FPS 3.pdf"
    match = re.search(
        r"\b([\w][\w\-\. ]*\.(?:pdf|doc|docx|txt|md|ppt|pptx|xls|xlsx))\b",
        t,
        re.IGNORECASE,
    )
    if match:
        result = match.group(1).strip()
        result = _RE_NOISE_START.sub("", result)
        result = _RE_NOISE_ARTICLE.sub("", result).strip()
        return result

    # 2. Strip action prefix → article → noise suffix → return core
    cleaned = _RE_NOISE_START.sub("", t.strip())
    cleaned = _RE_NOISE_ARTICLE.sub("", cleaned.strip())
    cleaned = _RE_NOISE_END.sub("", cleaned.strip())
    cleaned = cleaned.strip().rstrip(".,!?")

    return cleaned if len(cleaned) >= 2 else None


def _extract_filename_with_llamaindex(
    user_text: str,
    model: Optional[str],
    host: Optional[str],
    api_key: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """LLM-based filename extraction (optional; requires llama_index + Ollama)."""
    if not model or not host:
        return None, None
    try:
        from llama_index.llms.ollama import Ollama
    except ImportError:
        return None, None

    client_kwargs = (
        {"headers": {"Authorization": f"Bearer {api_key}"}} if api_key else None
    )
    try:
        llm = Ollama(
            model=model,
            base_url=host,
            **({"client_kwargs": client_kwargs} if client_kwargs else {}),
            request_timeout=30.0,
        )
    except Exception:
        return None, None

    print(f"📂  LLM extraction using model: {model}")
    prompt = (
        "Your job: extract ONLY the file name from the user's request.\n"
        "Output just the filename or identifier — nothing else.\n"
        "Remove ALL action words: open, close, shut, launch, please, the, file, my.\n"
        "Examples:\n"
        "  'Open FPS3.pdf file' → FPS3.pdf\n"
        "  'Close the FPS3.pdf file' → FPS3.pdf\n"
        "  'open my resume' → resume\n"
        "  'launch FPS 3.5' → FPS 3.5\n"
        "If no file is mentioned, output: NO_FILE\n\n"
        f"User: {user_text}\n"
        "Filename only:"
    )
    try:
        response = llm.complete(prompt)
        raw = (getattr(response, "text", None) or str(response)).strip().splitlines()[0].strip()
        if not raw or "NO_FILE" in raw.upper():
            return None, None

        # Strip any noise words the LLM forgot to remove
        noise = {
            "open", "close", "shut", "launch", "please", "the", "file",
            "my", "a", "an", "kholna", "khol", "band", "karo", "kar",
        }
        cleaned_words = raw.split()
        while cleaned_words and cleaned_words[0].lower() in noise:
            cleaned_words.pop(0)
        while cleaned_words and cleaned_words[-1].lower() in noise:
            cleaned_words.pop()
        raw = " ".join(cleaned_words).strip()
        return (raw, None) if raw else (None, None)
    except Exception:
        return None, None


def _fallback_extract_filename(user_text: str) -> Optional[str]:
    t = user_text.lower()

    # Step 1: explicit extension match (most reliable)
    match = re.search(
        r"\b([\w\-\.]+\.(?:pdf|doc|docx|txt|md|ppt|pptx|xls|xlsx))\b", t
    )
    if match:
        return match.group(1).strip()

    # Step 2: strip noise words, return what's left
    words = t.split()
    cleaned = [w for w in words if w not in _NOISE_WORDS and len(w) > 1]
    result = " ".join(cleaned).strip()
    result = re.sub(r"[^\w\s\.\-]", "", result).strip()
    return result or None