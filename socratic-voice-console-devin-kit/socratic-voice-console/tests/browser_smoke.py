"""Browser regression checks. Run with the app on localhost:8000.

Install: pip install -r requirements-browser.txt
Run:    python tests/browser_smoke.py
"""

from __future__ import annotations

import base64
import io
import json
import math
import os
import struct
import wave
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
ARTIFACT_DIR = Path(os.getenv("BROWSER_ARTIFACT_DIR", "/tmp/professor-browser-checks"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def response_payload(answer="Grounded answer.", **overrides):
    payload = {
        "request_id": "browser-check",
        "educator_name": "Dr. Margaret Holloway",
        "answer_text": answer,
        "answer_engine": "offline",
        "tts_engine": "browser",
        "audio_base64": None,
        "audio_mime_type": None,
        "sources": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def wav_base64(seconds=3):
    sample_rate = 16000
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(sample_rate * seconds):
            value = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.extend(struct.pack("<h", value))
        wav.writeframes(frames)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def wait_for_value(page, expression, timeout_ms=10000):
    attempts = max(1, timeout_ms // 100)
    for _ in range(attempts):
        if page.evaluate(expression):
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"Timed out waiting for: {expression}")


def watch(page, errors):
    page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
    page.on(
        "console",
        lambda message: (
            errors.append(f"console: {message.text}")
            if message.type == "error"
            else None
        ),
    )
    page.on(
        "response",
        lambda response: (
            errors.append(f"http {response.status}: {response.url}")
            if response.status >= 400
            else None
        ),
    )


def primary_flow(browser, errors):
    page = browser.new_page(viewport={"width": 375, "height": 812})
    watch(page, errors)
    page.goto(BASE_URL, wait_until="networkidle")
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    page.get_by_role("button", name="CAP theorem", exact=True).click()
    page.get_by_role("button", name="Ask professor").click()
    page.locator(".message-professor").nth(1).wait_for()
    assert "Brewer" in page.locator(".message-professor").nth(1).inner_text()
    page.locator(".sources summary").click()
    assert "doc_cap" in page.locator(".source-list").inner_text()
    page.locator("#questionInput").focus()
    assert (
        page.locator("#questionInput").evaluate(
            "el => getComputedStyle(el).outlineStyle"
        )
        == "solid"
    )
    page.screenshot(path=str(ARTIFACT_DIR / "mobile-primary.png"), full_page=True)
    page.close()
    return "mobile primary flow, sources, overflow, and focus ring"


def clear_cancels_delayed_request(browser, errors):
    page = browser.new_page()
    watch(page, errors)
    payload = json.dumps(response_payload("Late response must not appear."))
    page.add_init_script(
        f"""
        const nativeFetch = window.fetch.bind(window);
        window.fetch = async (url, options = {{}}) => {{
          if (url === '/api/ask') {{
            await new Promise((resolve, reject) => {{
              const timer = setTimeout(resolve, 600);
              options.signal?.addEventListener('abort', () => {{
                clearTimeout(timer);
                reject(new DOMException('Aborted', 'AbortError'));
              }});
            }});
            return new Response(JSON.stringify({payload}), {{status: 200, headers: {{'Content-Type': 'application/json'}}}});
          }}
          return nativeFetch(url, options);
        }};
        """
    )
    page.goto(BASE_URL, wait_until="networkidle")
    page.locator("#questionInput").fill("Explain the CAP theorem")
    page.get_by_role("button", name="Ask professor").click()
    page.wait_for_timeout(80)
    page.get_by_role("button", name="Clear session").click()
    page.wait_for_timeout(800)
    assert page.locator(".message").count() == 1
    assert "Orientation" in page.locator(".message").inner_text()
    assert "Late response" not in page.locator("#transcript").inner_text()
    assert page.locator("#sendButton").is_enabled()
    assert page.locator("#thinking").is_hidden()
    page.close()
    return "clear aborts delayed request and blocks stale answer"


def recognition_preserves_segments_and_single_submit(browser, errors):
    page = browser.new_page()
    watch(page, errors)
    page.add_init_script(
        """
        window.askCalls = 0;
        const nativeFetch = window.fetch.bind(window);
        window.fetch = (url, options) => {
          if (url === '/api/ask') window.askCalls += 1;
          return nativeFetch(url, options);
        };
        class FakeRecognition {
          constructor() { window.fakeRecognition = this; }
          start() { this.onstart?.(); }
          stop() { this.onend?.(); }
        }
        window.SpeechRecognition = FakeRecognition;
        window.emitRecognition = () => {
          const first = [{transcript: 'Explain'}];
          first.isFinal = true;
          const second = [{transcript: 'the CAP theorem'}];
          second.isFinal = false;
          window.fakeRecognition.onresult({resultIndex: 1, results: [first, second]});
        };
        """
    )
    page.goto(BASE_URL, wait_until="networkidle")
    page.get_by_role("button", name="Speak").click()
    page.evaluate("window.emitRecognition()")
    assert page.locator("#questionInput").input_value() == "Explain the CAP theorem"
    page.get_by_role("button", name="Ask professor").click()
    page.locator(".message-professor").nth(1).wait_for()
    assert page.evaluate("window.askCalls") == 1
    assert page.locator(".message-student").count() == 1
    page.close()
    return "recognition keeps all segments and submits once"


def browser_speech_chunks_and_ignores_stale_events(browser, errors):
    page = browser.new_page()
    watch(page, errors)
    long_answer = "The CAP theorem describes a distributed-system tradeoff. " * 22
    payload = json.dumps(response_payload(long_answer))
    page.add_init_script(
        f"""
        const mockPayload = {payload};
        const nativeFetch = window.fetch.bind(window);
        window.fetch = async (url, options = {{}}) => {{
          if (url === '/api/ask') {{
            await new Promise(resolve => setTimeout(resolve, 200));
            return new Response(JSON.stringify(mockPayload), {{status: 200, headers: {{'Content-Type': 'application/json'}}}});
          }}
          return nativeFetch(url, options);
        }};
        class FakeUtterance {{ constructor(text) {{ this.text = text; }} }}
        const synth = {{
          voices: [{{name: 'Samantha', lang: 'en-US'}}, {{name: 'Daniel', lang: 'en-GB'}}],
          utterances: [], current: null, speaking: false,
          getVoices() {{ return this.voices; }},
          addEventListener() {{}},
          cancel() {{
            const old = this.current;
            this.current = null;
            this.speaking = false;
            old?.onerror?.({{error: 'canceled'}});
          }},
          speak(utterance) {{
            this.utterances.push(utterance);
            this.current = utterance;
            this.speaking = true;
            utterance.onstart?.();
          }},
          finish() {{
            const old = this.current;
            this.current = null;
            this.speaking = false;
            old?.onend?.();
          }}
        }};
        window.fakeSynth = synth;
        Object.defineProperty(window, 'speechSynthesis', {{value: synth, configurable: true}});
        Object.defineProperty(window, 'SpeechSynthesisUtterance', {{value: FakeUtterance, configurable: true}});
        """
    )
    page.goto(BASE_URL, wait_until="networkidle")
    page.locator("#questionInput").fill("CAP")
    page.get_by_role("button", name="Ask professor").click()
    page.locator("label").filter(has_text="Dr. Christopher Brooks").click()
    wait_for_value(page, "window.fakeSynth.utterances.length > 0")
    assert page.evaluate("window.fakeSynth.utterances[0].voice.name") == "Samantha"
    for _ in range(4):
        page.evaluate("window.fakeSynth.finish()")
        page.wait_for_timeout(30)
    assert page.evaluate("window.fakeSynth.utterances.length") > 1
    page.get_by_role("button", name="Clear session").click()
    page.wait_for_timeout(60)
    assert (
        page.locator("#voiceModeLabel").inner_text()
        == "Waiting for a professor response."
    )
    page.close()
    return "speech is chunked, persona-stable, and stale callbacks are ignored"


def spectrum_survives_resize_and_reset_releases_audio(browser, errors):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    watch(page, errors)
    payload = json.dumps(
        response_payload(
            "Server audio response.",
            tts_engine="voicebox",
            audio_base64=wav_base64(),
            audio_mime_type="audio/wav",
        )
    )
    page.add_init_script(
        f"""
        const mockPayload = {payload};
        const nativeFetch = window.fetch.bind(window);
        window.fetch = (url, options = {{}}) => {{
          if (url === '/api/ask') {{
            return Promise.resolve(new Response(JSON.stringify(mockPayload), {{status: 200, headers: {{'Content-Type': 'application/json'}}}}));
          }}
          return nativeFetch(url, options);
        }};
        window.rafCount = 0;
        const nativeRaf = window.requestAnimationFrame.bind(window);
        window.requestAnimationFrame = callback => {{
          window.rafCount += 1;
          return nativeRaf(callback);
        }};
        """
    )
    page.goto(BASE_URL, wait_until="networkidle")
    page.locator("#questionInput").fill("CAP")
    page.get_by_role("button", name="Ask professor").click()
    wait_for_value(page, "document.getElementById('audioPlayer').paused === false")
    page.wait_for_timeout(200)
    before = page.evaluate("window.rafCount")
    page.set_viewport_size({"width": 1200, "height": 860})
    page.wait_for_timeout(300)
    after = page.evaluate("window.rafCount")
    assert after > before + 2, (before, after)
    page.get_by_role("button", name="Clear session").click()
    assert page.locator("#audioPlayer").evaluate("el => el.getAttribute('src')") is None
    page.close()
    return "live spectrum survives resize and reset releases audio source"


def main():
    errors = []
    checks = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for check in (
            primary_flow,
            clear_cancels_delayed_request,
            recognition_preserves_segments_and_single_submit,
            browser_speech_chunks_and_ignores_stale_events,
            spectrum_survives_resize_and_reset_releases_audio,
        ):
            checks.append(check(browser, errors))
        browser.close()
    assert not errors, errors
    print(
        json.dumps({"checks": checks, "console_and_network_errors": errors}, indent=2)
    )


if __name__ == "__main__":
    main()
