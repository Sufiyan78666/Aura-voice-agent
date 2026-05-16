# hinglish_stt.py
# Hindi + English (Hinglish) Speech to Text
# Uses faster-whisper — 100% free, 100% offline

# ── Windows fix — must be FIRST ──────────────────────────────
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from faster_whisper import WhisperModel
import sounddevice as sd
import soundfile as sf
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
MODEL_SIZE   = "small"   # "small" / "medium" / "large-v3"
DEVICE       = "cpu"      # Force CPU to avoid CUDA dependency
COMPUTE_TYPE = "int8"     # int8 is recommended for CPU
SAMPLE_RATE  = 16000
RECORD_SECS  = 5

# ─────────────────────────────────────────────
# LOAD MODEL
# ─────────────────────────────────────────────
print(f"Loading Whisper '{MODEL_SIZE}' model...")
print("(First run downloads the model — takes a minute, then cached)")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("Model loaded! Ready to listen.\n")


# ─────────────────────────────────────────────
# FUNCTION 1: Record from mic
# ─────────────────────────────────────────────
def record_audio(seconds=RECORD_SECS):
    print(f"🎙  Speak now! Recording for {seconds} seconds...")
    print("    (Say anything in Hindi, English, or mix both)")
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    print("Recording done!\n")
    return audio.flatten()


# ─────────────────────────────────────────────
# FUNCTION 2: Save audio to temp file
# ─────────────────────────────────────────────
def save_audio(audio_array, filename="temp_audio.wav"):
    sf.write(filename, audio_array, SAMPLE_RATE)
    return filename


# ─────────────────────────────────────────────
# FUNCTION 3: Transcribe audio → text
# ─────────────────────────────────────────────
def transcribe_hinglish(audio_file):
    segments, info = model.transcribe(
        audio_file,
        language=None,       # auto-detect Hindi or English
        task="transcribe",   # keep original language
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )
    full_text = " ".join([seg.text for seg in segments]).strip()
    detected_lang = info.language
    confidence = round(info.language_probability * 100, 1)
    return full_text, detected_lang, confidence


# ─────────────────────────────────────────────
# FUNCTION 4: BONUS — smart routing by language
# ─────────────────────────────────────────────
def smart_transcribe(audio_file):
    text, lang, confidence = transcribe_hinglish(audio_file)

    if lang == "hi":
        lang_display  = "Hindi 🇮🇳"
        system_prompt = "Aap ek helpful assistant hain. Hamesha Hindi mein jawab dijiye."

    elif lang == "en":
        lang_display  = "English 🇬🇧"
        system_prompt = "You are a helpful assistant. Always reply in English."

    else:
        lang_display  = f"Hinglish / {lang}"
        system_prompt = (
            "You are a helpful assistant for Indian users. "
            "The user speaks Hinglish — a mix of Hindi and English. "
            "Reply naturally in the same Hinglish mix."
        )

    return text, lang_display, confidence, system_prompt


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  Hinglish Voice Transcriber")
    print("  Hindi + English — fully offline")
    print("=" * 50)
    print("Press Ctrl+C to stop\n")

    turn = 1

    while True:
        try:
            print(f"─── Turn {turn} " + "─" * 32)

            # Step 1: record
            audio = record_audio()

            # Step 2: save
            audio_file = save_audio(audio)

            # Step 3: smart transcribe ✅ FIXED — now calls bonus function
            text, lang_display, confidence, system_prompt = smart_transcribe(audio_file)

            # Step 4: clean up
            os.remove(audio_file)

            # Step 5: show results
            print("─" * 40)
            if text:
                print(f"Language  : {lang_display} ({confidence}% confident)")
                print(f"Transcript: {text}")
                print(f"Prompt    : {system_prompt}")
            else:
                print("(No speech detected — try speaking louder)")
            print("─" * 40)
            print()

            turn += 1
            again = input("Press Enter to record again, or 'q' to quit: ")
            if again.lower() == 'q':
                print("\nAlvida! Goodbye!")
                break
            print()

        except KeyboardInterrupt:
            print("\n\nStopped. Goodbye!")
            break


if __name__ == "__main__":
    main()