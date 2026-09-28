#!/usr/bin/env python3
"""Turn a written script into a voiceover, and tell you whether the script is any good.

Two separate jobs:

  speak()    - script -> mp3, plus an .srt whose timings come from the voice
               itself, so captions line up with the words that were actually said.
  analyse()  - reads the script the way a listener hears it and reports what is
               working against you: a weak opening, sentences too long to say in
               one breath, filler, no direct address, a wall of same-length lines.

Both are free and need no account. The voice comes from Microsoft's Edge neural
voices, which is the only step that touches the network. The analysis is plain
arithmetic on your text and runs offline.
"""

import asyncio
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".voices.json"

# Roughly what an Edge voice says per minute at +0%. Used to turn a word count
# into a runtime you can trust before you generate anything.
WORDS_PER_MINUTE = 150


# ---------------------------------------------------------------- voices


async def _fetch_voices():
    import edge_tts
    return await edge_tts.list_voices()


def voice_catalog(refresh=False):
    """Every Edge voice, grouped by language. Cached, because it is a network call."""
    if CACHE.exists() and not refresh:
        try:
            return json.loads(CACHE.read_text())
        except ValueError:
            pass

    voices = asyncio.run(_fetch_voices())
    catalog = {}
    for v in voices:
        label = f"{v['FriendlyName'].replace('Microsoft ', '').split(' - ')[0]}"
        catalog.setdefault(v["Locale"], []).append({
            "name": v["ShortName"],
            "gender": v["Gender"],
            "label": f"{v['ShortName']}  ({v['Gender']}, {label})",
        })
    for locale in catalog:
        catalog[locale].sort(key=lambda x: x["name"])
    CACHE.write_text(json.dumps(catalog, indent=1))
    return catalog


def locale_name(locale):
    """en-US -> 'English (United States)', falling back to the raw code."""
    try:
        import locale as _l  # noqa: F401  (only for the side effect of existing)
    except ImportError:
        pass
    lang, _, region = locale.partition("-")
    return f"{LANGUAGES.get(lang, lang)} ({REGIONS.get(region, region)})"


LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "pl": "Polish",
    "ru": "Russian", "ar": "Arabic", "hi": "Hindi", "ur": "Urdu",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "tr": "Turkish",
    "id": "Indonesian", "vi": "Vietnamese", "th": "Thai", "sv": "Swedish",
    "da": "Danish", "nb": "Norwegian", "fi": "Finnish", "cs": "Czech",
    "el": "Greek", "he": "Hebrew", "hu": "Hungarian", "ro": "Romanian",
    "uk": "Ukrainian", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "ml": "Malayalam", "mr": "Marathi", "gu": "Gujarati", "fa": "Persian",
}
REGIONS = {
    "US": "United States", "GB": "United Kingdom", "AU": "Australia",
    "CA": "Canada", "IN": "India", "IE": "Ireland", "NZ": "New Zealand",
    "ZA": "South Africa", "ES": "Spain", "MX": "Mexico", "AR": "Argentina",
    "CO": "Colombia", "BR": "Brazil", "PT": "Portugal", "FR": "France",
    "DE": "Germany", "IT": "Italy", "NL": "Netherlands", "PK": "Pakistan",
    "SA": "Saudi Arabia", "EG": "Egypt", "CN": "China", "TW": "Taiwan",
    "HK": "Hong Kong", "JP": "Japan", "KR": "Korea", "RU": "Russia",
}


# ---------------------------------------------------------------- speaking


async def _speak(text, voice, rate, pitch, volume, mp3, srt):
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
    sub = edge_tts.SubMaker()
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"].endswith("Boundary"):
                # Which one arrives depends on the voice: some emit WordBoundary,
                # others SentenceBoundary. Feeding whichever comes keeps the
                # subtitles working across all of them.
                sub.feed(chunk)
    Path(srt).write_text(sub.get_srt(), encoding="utf-8")


def speak(text, voice, out_dir, rate=0, pitch=0, volume=0, stem="voiceover"):
    """Render the script. Returns (mp3, srt).

    rate/pitch/volume are plain numbers here and become the strings Edge wants,
    so callers never have to remember the '+0%' / '+0Hz' spelling.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Nothing to say - the script is empty.")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3, srt = out_dir / f"{stem}.mp3", out_dir / f"{stem}.srt"
    asyncio.run(_speak(text, voice,
                       f"{rate:+d}%", f"{pitch:+d}Hz", f"{volume:+d}%", mp3, srt))
    return mp3, srt


# ---------------------------------------------------------------- analysis


SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])[\"')\]]*\s+")
WORD = re.compile(r"[A-Za-z'’-]+")

FILLERS = [
    "very", "really", "just", "actually", "basically", "literally", "simply",
    "quite", "rather", "somewhat", "definitely", "certainly", "obviously",
    "kind of", "sort of", "a lot of", "in order to", "the fact that",
    "needless to say", "at the end of the day", "it is important to note",
]
WEAK_OPENERS = [
    "hello", "hi ", "hey ", "welcome", "in this video", "today i", "today we",
    "in today's video", "what's up", "before we begin", "before we start",
    "let me tell you", "i want to talk about", "so basically",
]
PASSIVE = re.compile(
    r"\b(is|are|was|were|be|been|being)\s+(\w+ed|born|done|made|given|taken|"
    r"seen|known|shown|written|held|kept|told|found|left|brought|sent|built|"
    r"put|set|caught|lost|won)\b", re.I)
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "for",
    "with", "at", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "it", "its", "this", "that", "these", "those", "he", "she", "they", "we",
    "you", "your", "i", "my", "his", "her", "their", "our", "not", "no", "so",
    "then", "than", "there", "here", "what", "when", "how", "all", "can", "will",
    "would", "into", "out", "up", "down", "about", "just", "him", "them", "had",
    "has", "have", "do", "does", "did", "one", "more", "who", "which", "also",
}


def syllables(word):
    word = word.lower().strip("'’-")
    if not word:
        return 0
    count, prev_vowel = 0, False
    for ch in word:
        vowel = ch in "aeiouy"
        if vowel and not prev_vowel:
            count += 1
        prev_vowel = vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def sentences_of(text):
    return [s.strip() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def stats(text, wpm=WORDS_PER_MINUTE):
    words = WORD.findall(text)
    sents = sentences_of(text)
    lengths = [len(WORD.findall(s)) for s in sents] or [0]
    syl = sum(syllables(w) for w in words)

    flesch = None
    if words and sents:
        flesch = (206.835 - 1.015 * (len(words) / len(sents))
                  - 84.6 * (syl / len(words)))

    return {
        "words": len(words),
        "sentences": len(sents),
        "seconds": len(words) / wpm * 60 if words else 0.0,
        "avg_sentence": statistics.mean(lengths),
        "longest_sentence": max(lengths),
        "variety": statistics.pstdev(lengths) if len(lengths) > 1 else 0.0,
        "flesch": flesch,
        "you": len(re.findall(r"\b(you|your|you're|yours)\b", text, re.I)),
        "questions": text.count("?"),
        "numbers": len(re.findall(r"\b\d+\b", text)),
        "adverbs": len([w for w in words if w.lower().endswith("ly") and len(w) > 4]),
        "passive": len(PASSIVE.findall(text)),
    }


def _finding(level, title, detail, fix=None):
    return {"level": level, "title": title, "detail": detail, "fix": fix}


def analyse(text, wpm=WORDS_PER_MINUTE, target_seconds=None):
    """Read the script the way a listener will and report what fights against it.

    Ordered worst first. Every finding says what is wrong and what to do, because
    'reading level 42' on its own has never improved a script.
    """
    text = (text or "").strip()
    if not text:
        return [], {}

    s = stats(text, wpm)
    sents = sentences_of(text)
    lower = text.lower()
    out = []

    # --- the opening. Nothing else matters if they leave during it.
    hook = sents[0] if sents else ""
    hook_words = len(WORD.findall(hook))
    weak = next((w for w in WEAK_OPENERS if lower.startswith(w)), None)
    if weak:
        out.append(_finding(
            "high", "The first line is throat-clearing",
            f"It opens with “{weak.strip()}…”. Nobody stays for an "
            "introduction; they stay for the thing you are introducing.",
            "Cut it and start on the most surprising fact in the script."))
    elif hook_words > 18:
        out.append(_finding(
            "high", f"The opening sentence is {hook_words} words",
            "A hook has to land before anyone decides to keep listening, and "
            "long sentences bury the point at the end.",
            "Get it under about 12 words, or split it in two."))
    elif hook and not re.search(r"[?\d]", hook) and not re.search(
            r"\b(you|your)\b", hook, re.I):
        out.append(_finding(
            "medium", "The opening does not pull anyone in",
            "It has no question, no number and does not address the listener.",
            "Open with a question, a concrete number, or the word “you”."))

    # --- sentences you cannot say in one breath
    long_ones = [(len(WORD.findall(x)), x) for x in sents if len(WORD.findall(x)) > 25]
    if long_ones:
        n, worst = max(long_ones)
        out.append(_finding(
            "high" if len(long_ones) > 2 else "medium",
            f"{len(long_ones)} sentence{'s' if len(long_ones) > 1 else ''} "
            "too long to say in one breath",
            f"The worst is {n} words. Spoken, that runs about "
            f"{n / wpm * 60:.0f} seconds without a natural pause.",
            f"Split it. First few words: “{' '.join(worst.split()[:9])}…”"))

    # --- monotony
    if s["sentences"] >= 5 and s["variety"] < 3.5:
        out.append(_finding(
            "medium", "Every sentence is about the same length",
            f"They average {s['avg_sentence']:.0f} words with very little "
            "variation, which reads as a drone when spoken aloud.",
            "Drop in a three-word sentence. Like this. It resets attention."))

    # --- filler
    found = [f for f in FILLERS if re.search(rf"\b{re.escape(f)}\b", lower)]
    if found:
        out.append(_finding(
            "medium" if len(found) > 2 else "low",
            f"{len(found)} filler phrase{'s' if len(found) > 1 else ''} to cut",
            "These add syllables without adding meaning: "
            + ", ".join(f"“{f}”" for f in found[:6]) + ".",
            "Delete them. The sentence almost always survives untouched."))

    # --- passive voice
    if s["passive"] >= 2:
        out.append(_finding(
            "medium", f"{s['passive']} passive constructions",
            "Passive voice hides who did what, and takes longer to say.",
            "“The door was opened by her” → “She opened the door.”"))

    # --- direct address
    if s["words"] > 60 and s["you"] == 0:
        out.append(_finding(
            "medium", "The listener is never addressed",
            "The script never says “you”. Scripts that speak to one "
            "person hold attention better than scripts that describe a situation.",
            "Rewrite one or two lines to point straight at the listener."))

    # --- adverb pile-up
    if s["words"] and s["adverbs"] / s["words"] > 0.04:
        out.append(_finding(
            "low", f"{s['adverbs']} “-ly” adverbs",
            "Adverbs usually prop up a weak verb rather than adding anything.",
            "“ran quickly” → “sprinted”."))

    # --- reading level
    if s["flesch"] is not None and s["flesch"] < 50:
        out.append(_finding(
            "medium", f"Reading ease {s['flesch']:.0f} — hard to follow by ear",
            "A reader can go back over a sentence. A listener cannot. Anything "
            "below about 50 is heavy going when spoken.",
            "Shorter sentences and plainer words; aim for 60 or above."))

    # --- repetition
    counts = {}
    for w in WORD.findall(lower):
        if len(w) > 3 and w not in STOPWORDS:
            counts[w] = counts.get(w, 0) + 1
    repeated = [(c, w) for w, c in counts.items() if c >= 4]
    if repeated:
        repeated.sort(reverse=True)
        c, w = repeated[0]
        out.append(_finding(
            "low", f"“{w}” appears {c} times",
            "Repetition that is not deliberate reads as a small vocabulary.",
            "Vary it, or cut the sentences that repeat the point."))

    # --- length against a target
    if target_seconds:
        over = s["seconds"] - target_seconds
        if abs(over) > target_seconds * 0.15:
            direction = "over" if over > 0 else "under"
            words_off = abs(over) / 60 * wpm
            out.append(_finding(
                "high" if over > 0 else "low",
                f"About {abs(over):.0f}s {direction} your {target_seconds:.0f}s target",
                f"This reads as roughly {s['seconds']:.0f} seconds at {wpm} words "
                "per minute.",
                f"{'Cut' if over > 0 else 'Add'} about {words_off:.0f} words."))

    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda f: order[f["level"]])
    return out, s


# ---------------------------------------------------------------- optional rewrite


def ollama_rewrite(text, model="llama3.1:8b", host="http://localhost:11434",
                   target_seconds=None):
    """Ask a local Ollama model to punch the script up. Free, offline, optional.

    Returns None if Ollama is not running or the model is not pulled, so the
    caller can carry on with the analysis alone rather than failing.
    """
    import urllib.error
    import urllib.request

    text = (text or "").strip()
    if len(text.split()) < 10:
        return None

    length = ""
    if target_seconds:
        length = (f" Keep it close to {int(target_seconds / 60 * WORDS_PER_MINUTE)} "
                  "words so it fits the runtime.")

    prompt = (
        "Rewrite this voiceover script so it holds attention when read aloud.\n\n"
        f"SCRIPT:\n{text[:6000]}\n\n"
        "Open on the single most surprising thing in it. Speak directly to the "
        "listener. Short sentences, varied length, plain words, active voice. "
        "Keep every fact that is already there and invent nothing."
        f"{length} Reply with the rewritten script only — no preamble, no "
        "headings, no bullet points, no quotation marks.")

    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.7},
    }).encode()
    req = urllib.request.Request(f"{host.rstrip('/')}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            out = json.loads(r.read()).get("response", "")
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None

    out = re.sub(r"^\s*(here'?s?|sure|okay)[^\n:]*:\s*", "", out.strip(), flags=re.I)
    out = re.sub(r"^[\"'*#\s]+|[\"'*\s]+$", "", out)
    return out or None


# Rewriting prose is a general-language job. Code-tuned models are pulled far
# more often than instruct models and do noticeably worse at it -- they tend to
# leave the weak opening in place and tack a flourish on the end -- so sink them
# below anything general-purpose rather than letting the first model win.
CODE_MODEL = re.compile(r"coder|code|starcoder|deepseek-c|sqlcoder", re.I)


def ollama_models(host="http://localhost:11434"):
    """What is actually pulled locally, best-suited first."""
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=3) as r:
            names = [m["name"] for m in json.loads(r.read()).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return []
    return sorted(names, key=lambda n: (bool(CODE_MODEL.search(n)), n))


def is_code_model(name):
    return bool(CODE_MODEL.search(name or ""))
