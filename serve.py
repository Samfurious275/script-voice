#!/usr/bin/env python3
"""Web page for the script-to-voiceover tool.

  ./serve.sh            macOS / Linux
  serve.bat             Windows

Paste a script, pick a voice, get an MP3 and matching subtitles back — and a
straight read on what is weak about the script before you record it.

  ./serve.sh --share --password hunter2     publish a link other people can use
"""

import argparse
import tempfile
from pathlib import Path

import gradio as gr

import narrate

DEFAULT_LOCALE = "en-US"
DEFAULT_VOICE = "en-US-AriaNeural"
LEVELS = {"high": "Fix first", "medium": "Worth fixing", "low": "Minor"}


def _catalog():
    try:
        return narrate.voice_catalog()
    except Exception:
        # Offline on first run: fall back to a handful so the page still opens.
        return {"en-US": [{"name": "en-US-AriaNeural",
                           "label": "en-US-AriaNeural  (Female, Aria)"}],
                "es-MX": [{"name": "es-MX-JorgeNeural",
                           "label": "es-MX-JorgeNeural  (Male, Jorge)"}]}


CATALOG = _catalog()
LOCALE_CHOICES = sorted(
    ((narrate.locale_name(loc), loc) for loc in CATALOG),
    key=lambda pair: (not pair[1].startswith("en"), pair[0]))


def voices_for(locale):
    return [(v["label"], v["name"]) for v in CATALOG.get(locale, [])]


def on_language(locale):
    choices = voices_for(locale)
    value = choices[0][1] if choices else None
    return gr.Dropdown(choices=choices, value=value)


def render_report(findings, s):
    if not s:
        return "_Paste a script and press **Check the script**._"

    mins, secs = divmod(int(s["seconds"]), 60)
    head = [
        f"**{s['words']} words · {s['sentences']} sentences · "
        f"about {mins}:{secs:02d} spoken**",
        "",
        f"Reading ease {s['flesch']:.0f}" if s["flesch"] is not None else "",
        "",
    ]

    if not findings:
        head.append("Nothing is working against you. This reads well aloud.")
        return "\n".join(x for x in head if x is not None)

    body = []
    for f in findings:
        body.append(f"### {LEVELS[f['level']]} — {f['title']}")
        body.append(f["detail"])
        if f["fix"]:
            body.append(f"**Do this:** {f['fix']}")
        body.append("")
    return "\n".join(head + body)


def check(script, target):
    findings, s = narrate.analyse(script, target_seconds=target or None)
    return render_report(findings, s)


def generate(script, voice, rate, pitch, target, progress=gr.Progress()):
    if not (script or "").strip():
        raise gr.Error("Paste a script first.")
    if not voice:
        raise gr.Error("Pick a voice first.")

    progress(0.2, desc="Reading the script")
    report = check(script, target)

    progress(0.5, desc=f"Speaking it as {voice}")
    out = Path(tempfile.mkdtemp(prefix="voice-"))
    try:
        mp3, srt = narrate.speak(script, voice, out, rate=int(rate), pitch=int(pitch))
    except Exception as e:
        raise gr.Error(f"The voice service refused that: {e}")

    progress(1.0, desc="Done")
    return str(mp3), str(srt), report


def rewrite(script, model, target):
    if not (script or "").strip():
        raise gr.Error("Paste a script first.")
    out = narrate.ollama_rewrite(script, model=model,
                                 target_seconds=target or None)
    if out is None:
        raise gr.Error(
            "Could not reach Ollama. Start it with `ollama serve`, and pull a "
            f"model with `ollama pull {model}`.")
    return out


def build_ui():
    models = narrate.ollama_models()

    with gr.Blocks(title="Script to voiceover") as demo:
        gr.Markdown(
            "# Script &rarr; voiceover\n"
            "Paste a script, pick a voice, get an MP3 and matching subtitles. "
            "The script is also checked for the things that lose listeners — a "
            "slow opening, sentences too long to say in one breath, filler.\n\n"
            "Free, no account, no API key."
        )
        with gr.Row():
            with gr.Column(scale=3):
                script = gr.Textbox(
                    label="Your script", lines=16,
                    placeholder="Paste the script here.\n\nWrite it the way you "
                                "would say it out loud, not the way you would "
                                "write it down.")
                with gr.Row():
                    language = gr.Dropdown(
                        LOCALE_CHOICES, value=DEFAULT_LOCALE, label="Language",
                        filterable=True)
                    voice = gr.Dropdown(
                        voices_for(DEFAULT_LOCALE), value=DEFAULT_VOICE,
                        label="Voice", filterable=True)
                with gr.Row():
                    rate = gr.Slider(-50, 50, value=0, step=5,
                                     label="Speed (%)")
                    pitch = gr.Slider(-50, 50, value=0, step=5,
                                      label="Pitch (Hz)")
                target = gr.Slider(
                    0, 180, value=0, step=5, label="Target length (seconds)",
                    info="Leave at 0 to skip the length check. 30-60 suits a reel.")
                with gr.Row():
                    go = gr.Button("Generate voiceover", variant="primary")
                    look = gr.Button("Check the script")
            with gr.Column(scale=2):
                audio = gr.Audio(label="Voiceover", type="filepath")
                subs = gr.File(label="Subtitles (.srt)")
                report = gr.Markdown(
                    "_Paste a script and press **Check the script**._")

        with gr.Accordion("Rewrite it with a local model (Ollama)", open=False):
            if models:
                note = ("Ollama is running. This rewrites the script to open "
                        "harder and read better aloud, keeping your facts. It "
                        "replaces nothing automatically — you get a draft to "
                        "compare.")
                if all(narrate.is_code_model(m) for m in models):
                    note += ("\n\n**Only code-tuned models are installed.** They "
                             "are weak at rewriting prose and tend to leave a "
                             "flabby opening alone. For much better drafts: "
                             "`ollama pull llama3.1:8b`.")
                gr.Markdown(note)
                with gr.Row():
                    model = gr.Dropdown(
                        models, value=models[0], label="Model",
                        info="General-purpose models do this far better than "
                             "code models")
                    rw = gr.Button("Rewrite", variant="secondary")
                rewritten = gr.Textbox(label="Suggested rewrite", lines=12,
                                       show_label=True)
                rw.click(rewrite, inputs=[script, model, target],
                         outputs=[rewritten])
            else:
                gr.Markdown(
                    "Ollama is not running, so this is off. It is optional and "
                    "free: install it from [ollama.com](https://ollama.com), then "
                    "`ollama pull llama3.1:8b` and restart this page. Everything "
                    "else works without it.")

        language.change(on_language, inputs=[language], outputs=[voice])
        go.click(generate, inputs=[script, voice, rate, pitch, target],
                 outputs=[audio, subs, report])
        look.click(check, inputs=[script, target], outputs=[report])
    return demo


def main():
    p = argparse.ArgumentParser(
        description="Serve the script-to-voiceover page on this machine.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--share", action="store_true",
                   help="also publish a public gradio.live link (up to a week)")
    p.add_argument("--password", default=None,
                   help="require this password; strongly advised with --share")
    p.add_argument("--user", default="voice",
                   help="username that goes with --password")
    p.add_argument("--host", default="127.0.0.1",
                   help="0.0.0.0 to allow other machines on your network")
    p.add_argument("--port", type=int, default=7861)
    a = p.parse_args()

    if a.share and not a.password:
        print("  ! --share puts this on the public internet with no password.\n"
              "    Add --password to lock it.\n")

    print(f"\n  Starting on http://{a.host}:{a.port}")
    if a.password:
        print("\n  The page will ask you to log in:")
        print(f"      username   {a.user}")
        print(f"      password   {a.password}\n")
    print("  Your browser should open by itself. Press Ctrl+C here to stop.\n")

    build_ui().queue(max_size=16).launch(
        server_name=a.host, server_port=a.port, share=a.share,
        auth=(a.user, a.password) if a.password else None,
        inbrowser=True)


if __name__ == "__main__":
    main()
