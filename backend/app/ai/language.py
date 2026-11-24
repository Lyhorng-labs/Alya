import re
from typing import Literal
Language = Literal["en", "zh", "ja"]

def detect_text_language(text: str) -> Language | None:
    text = text.strip()

    if not text:
        return None

    normalized = text.lower()

    # Explicit language-switch instructions.
    commands = [
        (
            r"\b(speak|talk|reply|respond|answer|use|switch to)"
            r"\s+(in\s+)?english\b",
            "en",
        ),
        (
            r"\b(speak|talk|reply|respond|answer|use|switch to)"
            r"\s+(in\s+)?(chinese|mandarin)\b",
            "zh",
        ),
        (
            r"\b(speak|talk|reply|respond|answer|use|switch to)"
            r"\s+(in\s+)?japanese\b",
            "ja",
        ),
    ]

    for pattern, language in commands:
        if re.search(pattern, normalized):
            return language

    # Japanese Hiragana and Katakana.
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"

    # Chinese characters, when Japanese kana is absent.
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"

    # Common romanized Japanese.
    compact = re.sub(r"[^a-z]", "", normalized)

    japanese_phrases = {
        "konnichiwa",
        "konbanwa",
        "ohayo",
        "ohayou",
        "arigato",
        "arigatou",
        "sumimasen",
        "sayonara",
        "daijoubu",
        "genki",
        "hai",
        "iie",
    }

    if compact in japanese_phrases:
        return "ja"

    # Common romanized Mandarin.
    chinese_phrases = {
        "nihao",
        "nihaoma",
        "xiexie",
        "zaijian",
        "zaoshanghao",
        "buhaoyisi",
    }

    if compact in chinese_phrases:
        return "zh"

    # English or other Latin-script text defaults to English.
    if re.search(r"[a-z]", normalized):
        return "en"

    return None


def resolve_turn_language(
    history: list[dict[str, str]],
    requested_language: str,
) -> Language:

    # Respect an explicitly selected language.
    if requested_language in ("en", "zh", "ja"):
        return requested_language

    # Check the newest user messages first.
    for message in reversed(history):

        if message["role"] != "user":
            continue

        detected = detect_text_language(
            message["content"]
        )

        if detected:
            return detected
    return "en"