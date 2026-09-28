# script-voice

Paste a script, pick a voice, get a voiceover back — plus a straight read on what
is weak about the script before you record it.

- **322 voices** across 142 languages, from Microsoft's free Edge neural voices
- **Matching subtitles** (`.srt`) with timings taken from the voice itself
- **Script feedback** that names the problem and tells you what to do about it
- Optional **rewrite** by a local model, if you have [Ollama](https://ollama.com)

Free. No account, no API key, no limits. The only step that touches the network
is the voice itself; everything else runs on your machine.

---

## Setup

You need **Python 3.9 or newer** — any current version is fine.

### macOS and Linux

```bash
git clone <your-repo-url> script-voice
cd script-voice
chmod +x serve.sh
./serve.sh
```

### Windows

Install Python from [python.org/downloads](https://www.python.org/downloads/),
ticking **"Add python.exe to PATH"** in the installer. Then:

```bat
git clone <your-repo-url> script-voice
cd script-voice
serve.bat
```

You can also just double-click `serve.bat`.

Either way, the first run sets up an environment (about a minute) and then your
browser opens at **http://127.0.0.1:7861**. Every run after that starts in
seconds.

---

## Using it

1. **Paste your script** into the big box.
2. **Pick a language**, then a **voice**. Both boxes are searchable — type
   `es-MX` or `Aria` to filter.
3. **Speed** and **pitch** if you want them; 0 is the natural voice.
4. **Target length** — set it to the runtime you are aiming for (30–60s suits a
   reel) and the check tells you how many words to cut or add. Leave it at 0 to
   skip that.
5. **Generate voiceover** gives you the MP3, the subtitles and the feedback.
   **Check the script** gives you just the feedback, instantly and offline.

The audio takes a couple of seconds. There is no queue and no wait.

---

## What the script check looks for

It reads your script the way a listener hears it — once, in order, with no way to
go back over a sentence. Findings are ordered worst first.

| It flags | Because |
| --- | --- |
| A throat-clearing opening | "Hello everyone, welcome back" — nobody stays for an introduction |
| An opening over ~18 words | The hook has to land before they decide to keep listening |
| Sentences over 25 words | Too long to say in one breath |
| Every sentence the same length | Reads as a drone when spoken |
| Filler phrases | "very", "really", "basically" — syllables without meaning |
| Passive voice | Hides who did what, and takes longer to say |
| Never saying "you" | Scripts aimed at one person hold attention better |
| `-ly` adverb pile-ups | Usually propping up a weak verb |
| Reading ease under 50 | A reader can re-read a sentence; a listener cannot |
| A word repeated four or more times | Reads as a small vocabulary |
| Length off your target | Tells you how many words to cut or add |

Every finding says what to do, not just what is wrong.

### Rewriting with Ollama (optional)

If [Ollama](https://ollama.com) is running, the panel at the bottom asks a local
model to rewrite the script. It is free, offline, and never replaces your text —
you get a draft beside the original.

```bash
ollama pull llama3.1:8b
```

**Use a general-purpose model.** Code-tuned models (`qwen2.5-coder`,
`deepseek-coder`) are pulled far more often but are weak at prose — in testing,
one left the "Hello everyone" opening untouched and tacked an exclamation on the
end. The dropdown sorts general models first and warns you if only code models
are installed.

Without Ollama, everything else still works. The panel just says so.

---

## Sharing the page

```bash
./serve.sh --share --password choose-something-hard
```

```bat
serve.bat --share --password choose-something-hard
```

This prints a public `https://...gradio.live` link anyone can open. The terminal
also prints the login:

```
  The page will ask you to log in:
      username   voice
      password   choose-something-hard
```

**Send the link, the username and the password together.** The page opens on a
login box, so the link alone gets them "Incorrect Credentials" with no idea why.
The username is `voice` unless you change it with `--user`.

Gradio expires these links after up to a week, best effort. The link also dies
the moment you stop the server, and starting again makes a new one — so there is
nothing to revoke.

Always set a password. Without one, anyone with the link can use your machine.

### Stopping it

`Ctrl+C` in the terminal, or close the window.

---

## Options

```bash
./serve.sh --port 7870          # if 7861 is taken
./serve.sh --host 0.0.0.0       # reachable from your own network
./serve.sh --user sam --password hunter2
./serve.sh --help
```

---

## If something goes wrong

**"The voice service refused that"**
Edge's speech service was unreachable or rejected the text. Check your internet.
Very long scripts occasionally fail — split them in half.

**The voice list is tiny**
The catalog is fetched once and cached in `.voices.json`. If the first run was
offline you get a two-voice fallback. Delete `.voices.json` and restart.

**Port already in use**
`./serve.sh --port 7870`

**The Ollama panel says it is not running**
Start it with `ollama serve`, then reload the page. The panel is built at
startup, so it will not appear until you restart.

---

## Notes

- Audio and subtitles are written to a temporary folder and offered as downloads.
  Save them somewhere before you close the tab.
- Estimated runtime assumes 150 words per minute, which is about what these
  voices do at speed 0. Raising the speed slider shortens the real audio without
  changing the estimate.
- Subtitle timings come from the speech service, so they match what was actually
  said rather than being guessed from word counts.
