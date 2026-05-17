#!/bin/bash
apt-get update -qq && apt-get install -y tesseract-ocr ghostscript unpaper 2>/dev/null || true
pip install -r requirements.txt
