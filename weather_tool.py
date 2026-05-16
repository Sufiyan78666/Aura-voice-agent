"""
weather_tool.py — Voice Agent Weather Tool
Uses Open-Meteo API (FREE, no API key needed) + Nominatim geocoding
Compatible with: faster-whisper STT | Ollama gemma3 LLM | pyttsx3 TTS
"""   

import requests

# ── WMO weather code descriptions ──────────────────────────────────────────
WMO_CODES = {
    0: "clear sky",
    1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "icy fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "slight showers", 81: "moderate showers", 82: "violent showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm",
}


def get_coordinates(city: str) -> tuple[float, float, str]:
    """Convert city name → (latitude, longitude, display_name) using Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": city, "format": "json", "limit": 1}
    headers = {"User-Agent": "VoiceAgent/1.0"}
    resp = requests.get(url, params=params, headers=headers, timeout=5)
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ValueError(f"City '{city}' not found.")
    r = results[0]
    return float(r["lat"]), float(r["lon"]), r["display_name"].split(",")[0]


def get_weather(city: str) -> str:
    """
    Fetch current weather for a city and return a TTS-friendly string.

    Usage:
        response = get_weather("Mumbai")
        speak(response)   # pass to your pyttsx3 TTS
    """
    try:
        lat, lon, name = get_coordinates(city)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "wind_speed_10m",
                "weathercode",
            ],
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        }
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()["current"]

        temp        = round(data["temperature_2m"])
        feels_like  = round(data["apparent_temperature"])
        humidity    = data["relative_humidity_2m"]
        wind        = round(data["wind_speed_10m"])
        condition   = WMO_CODES.get(data["weathercode"], "unknown conditions")

        return (
            f"The weather in {name} is {condition}. "
            f"Temperature is {temp} degrees Celsius, feels like {feels_like}. "
            f"Humidity is {humidity} percent, wind speed {wind} kilometres per hour."
        )

    except ValueError as e:
        return str(e)
    except requests.RequestException:
        return "Sorry, I couldn't reach the weather service. Please check your internet connection."


# ── Integration with your voice agent ──────────────────────────────────────
#
#   Detect intent in your LLM/agent loop, then call:
#
#       from weather_tool import get_weather
#
#       # When user says "what's the weather in Delhi" or "weather Mumbai"
#       city = extract_city_from_utterance(user_text)   # your NLU/LLM step
#       response = get_weather(city)
#       engine.say(response)   # pyttsx3
#       engine.runAndWait()
#
# ───────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Quick test
    cities = ["Mumbai", "Delhi", "London"]
    for city in cities:
        print(f"\n[{city}]")
        print(get_weather(city))