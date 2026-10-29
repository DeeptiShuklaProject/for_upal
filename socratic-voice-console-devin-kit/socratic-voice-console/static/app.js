const $ = (id) => document.getElementById(id);

const elements = {
  form: $("questionForm"),
  question: $("questionInput"),
  send: $("sendButton"),
  transcript: $("transcript"),
  thinking: $("thinking"),
  clear: $("clearButton"),
  error: $("errorBanner"),
  knowledge: $("knowledgeSelect"),
  knowledgeDescription: $("knowledgeDescription"),
  answerProvider: $("answerProvider"),
  ttsProvider: $("ttsProvider"),
  providerNote: $("providerNote"),
  activePersona: $("activePersona"),
  engineBadge: $("engineBadge"),
  mic: $("micButton"),
  micLabel: $("micLabel"),
  audio: $("audioPlayer"),
  stopAudio: $("stopAudioButton"),
  voiceMode: $("voiceModeLabel"),
  canvas: $("spectrumCanvas"),
};

const state = {
  config: null,
  busy: false,
  recording: false,
  submitAfterRecording: false,
  recognition: null,
  micSupported: false,
  audioUrl: null,
  audioContext: null,
  analyser: null,
  animationFrame: null,
  canvasContext: elements.canvas.getContext("2d"),
  devicePixelRatio: Math.min(window.devicePixelRatio || 1, 2),
  reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  welcome: elements.transcript.firstElementChild.cloneNode(true),
  activeController: null,
  requestSerial: 0,
  speechGeneration: 0,
  speechQueueTimer: null,
  voices: [],
};

const FALLBACK_PERSONAS = {
  margaret: { name: "Dr. Margaret Holloway", browser_voice_names: ["Samantha", "Zira", "Female"] },
  christopher: { name: "Dr. Christopher Brooks", browser_voice_names: ["Daniel", "David", "Male"] },
};

function selectedPersonaId() {
  return document.querySelector('input[name="persona"]:checked')?.value || "margaret";
}

function personaFor(id) {
  return state.config?.personas.find((persona) => persona.id === id) || FALLBACK_PERSONAS[id];
}

function selectedPersona() {
  return personaFor(selectedPersonaId());
}

function showError(message) {
  elements.error.textContent = message;
  elements.error.hidden = false;
}

function clearError() {
  elements.error.hidden = true;
  elements.error.textContent = "";
}

function setBusy(busy) {
  state.busy = busy;
  elements.send.disabled = busy;
  elements.question.readOnly = busy;
  elements.mic.disabled = !state.micSupported || (busy && !state.recording);
  elements.send.querySelector("span").textContent = busy ? "Consulting…" : "Ask professor";
  elements.transcript.setAttribute("aria-busy", String(busy));
}

function scrollTranscript() {
  requestAnimationFrame(() => {
    elements.transcript.scrollTop = elements.transcript.scrollHeight;
  });
}

function makeMessageHeader(author, meta) {
  const header = document.createElement("header");
  header.className = "message-header";
  const authorElement = document.createElement("span");
  authorElement.className = "message-author";
  authorElement.textContent = author;
  const metaElement = document.createElement("span");
  metaElement.className = "message-meta";
  metaElement.textContent = meta;
  header.append(authorElement, metaElement);
  return header;
}

function appendStudent(question) {
  const article = document.createElement("article");
  article.className = "message message-student";
  article.appendChild(makeMessageHeader("You", "Student question"));
  const paragraph = document.createElement("p");
  paragraph.textContent = question;
  article.appendChild(paragraph);
  elements.transcript.appendChild(article);
  scrollTranscript();
}

function appendSystemError(message) {
  const article = document.createElement("article");
  article.className = "message message-error";
  article.appendChild(makeMessageHeader("Console", "Request interrupted"));
  const paragraph = document.createElement("p");
  paragraph.textContent = message;
  article.appendChild(paragraph);
  elements.transcript.appendChild(article);
  scrollTranscript();
}

function appendSources(container, sources) {
  if (!sources.length) return;
  const details = document.createElement("details");
  details.className = "sources";
  const summary = document.createElement("summary");
  summary.textContent = `${sources.length} retrieved source${sources.length === 1 ? "" : "s"}`;
  details.appendChild(summary);
  const list = document.createElement("ul");
  list.className = "source-list";
  for (const source of sources) {
    const item = document.createElement("li");
    const topic = document.createElement("span");
    topic.className = "source-topic";
    topic.textContent = source.topic;
    const origin = document.createElement("span");
    origin.className = "source-origin";
    origin.textContent = `${source.id} · ${source.source}`;
    const excerpt = document.createElement("span");
    excerpt.className = "source-excerpt";
    excerpt.textContent = source.excerpt;
    item.append(topic, origin, excerpt);
    list.appendChild(item);
  }
  details.appendChild(list);
  container.appendChild(details);
}

function appendProfessor(data) {
  const article = document.createElement("article");
  article.className = "message message-professor";
  article.appendChild(makeMessageHeader(data.educator_name, `Request ${data.request_id}`));
  for (const block of data.answer_text.split(/\n{2,}/).filter(Boolean)) {
    const paragraph = document.createElement("p");
    paragraph.textContent = block.trim();
    article.appendChild(paragraph);
  }
  appendSources(article, data.sources);
  if (data.warnings.length) {
    const warnings = document.createElement("div");
    warnings.className = "warning-list";
    for (const warning of data.warnings) {
      const paragraph = document.createElement("p");
      paragraph.textContent = warning;
      warnings.appendChild(paragraph);
    }
    article.appendChild(warnings);
  }
  elements.transcript.appendChild(article);
  elements.engineBadge.textContent = `${data.answer_engine} · ${data.tts_engine}`;
  scrollTranscript();
}

function updateKnowledgeDescription() {
  const id = elements.knowledge.value;
  if (id === "all") {
    elements.knowledgeDescription.textContent = "Search all three local modules and return the strongest matching sources.";
    return;
  }
  const module = state.config?.knowledge.find((item) => item.id === id);
  elements.knowledgeDescription.textContent = module?.summary || "Search only the selected local module.";
}

function updatePersona() {
  elements.activePersona.textContent = selectedPersona().name;
}

function populateKnowledge(modules) {
  const current = elements.knowledge.value;
  elements.knowledge.replaceChildren();
  const all = new Option("All course notes", "all");
  elements.knowledge.add(all);
  for (const module of modules) {
    elements.knowledge.add(new Option(module.topic, module.id));
  }
  elements.knowledge.value = modules.some((item) => item.id === current) ? current : "all";
  updateKnowledgeDescription();
}

function populateProviders(select, providers) {
  const current = select.value;
  select.replaceChildren();
  for (const provider of providers) {
    const option = new Option(
      provider.configured ? provider.label : `${provider.label} — setup required`,
      provider.id,
    );
    option.disabled = !provider.configured;
    option.title = provider.detail;
    select.add(option);
  }
  const desired = [...select.options].find((option) => option.value === current && !option.disabled);
  select.value = desired ? current : "auto";
}

async function loadConfiguration() {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) throw new Error("Configuration unavailable");
    state.config = await response.json();
    populateKnowledge(state.config.knowledge);
    populateProviders(elements.answerProvider, state.config.answer_providers);
    populateProviders(elements.ttsProvider, state.config.tts_providers);
    const configuredVoices = state.config.tts_providers
      .filter((provider) => provider.configured && !["auto", "browser"].includes(provider.id))
      .map((provider) => provider.label);
    elements.providerNote.textContent = configuredVoices.length
      ? `Server voice ready: ${configuredVoices.join(", ")}. Browser speech remains the fallback.`
      : "Offline answers and browser speech are ready. Add server credentials or local voice profiles to enable more engines.";
    updatePersona();
  } catch {
    elements.providerNote.textContent = "Provider status could not be loaded. Offline defaults remain selected.";
  }
}

function resizeCanvas() {
  cancelAnimationFrame(state.animationFrame);
  state.animationFrame = null;
  const rect = elements.canvas.getBoundingClientRect();
  state.devicePixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  elements.canvas.width = Math.max(1, Math.round(rect.width * state.devicePixelRatio));
  elements.canvas.height = Math.max(1, Math.round(rect.height * state.devicePixelRatio));
  state.canvasContext.setTransform(state.devicePixelRatio, 0, 0, state.devicePixelRatio, 0, 0);
  if (!elements.audio.paused && state.analyser) {
    drawLiveSpectrum();
  } else {
    drawIdleSpectrum();
  }
}

function drawBars(values) {
  const context = state.canvasContext;
  const width = elements.canvas.width / state.devicePixelRatio;
  const height = elements.canvas.height / state.devicePixelRatio;
  context.clearRect(0, 0, width, height);
  const count = 48;
  const gap = 4;
  const barWidth = Math.max(2, (width - gap * (count - 1)) / count);
  context.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#d4ff00";
  for (let index = 0; index < count; index += 1) {
    const value = Math.max(0.04, Math.min(1, values[index] ?? 0.04));
    const barHeight = Math.max(3, value * (height - 12));
    const x = index * (barWidth + gap);
    const y = (height - barHeight) / 2;
    context.globalAlpha = 0.35 + value * 0.65;
    context.fillRect(x, y, barWidth, barHeight);
  }
  context.globalAlpha = 1;
}

function drawIdleSpectrum() {
  cancelAnimationFrame(state.animationFrame);
  state.animationFrame = null;
  const values = Array.from({ length: 48 }, (_, index) => 0.06 + (Math.sin(index * 1.63) + 1) * 0.035);
  drawBars(values);
}

function drawLiveSpectrum() {
  if (!state.analyser) return;
  const frequencies = new Uint8Array(state.analyser.frequencyBinCount);
  state.analyser.getByteFrequencyData(frequencies);
  const values = Array.from({ length: 48 }, (_, index) => {
    const start = Math.floor((index / 48) * frequencies.length);
    const end = Math.max(start + 1, Math.floor(((index + 1) / 48) * frequencies.length));
    let total = 0;
    for (let cursor = start; cursor < end; cursor += 1) total += frequencies[cursor];
    return total / (end - start) / 255;
  });
  drawBars(values);
  if (!state.reducedMotion && !elements.audio.paused) {
    state.animationFrame = requestAnimationFrame(drawLiveSpectrum);
  }
}

async function prepareAudioGraph() {
  if (!state.audioContext) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    state.audioContext = new AudioContextClass();
    const source = state.audioContext.createMediaElementSource(elements.audio);
    state.analyser = state.audioContext.createAnalyser();
    state.analyser.fftSize = 256;
    state.analyser.smoothingTimeConstant = 0.78;
    source.connect(state.analyser);
    state.analyser.connect(state.audioContext.destination);
  }
  if (state.audioContext.state === "suspended") await state.audioContext.resume();
}

function stopPlayback() {
  state.speechGeneration += 1;
  clearTimeout(state.speechQueueTimer);
  state.speechQueueTimer = null;
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  if (!elements.audio.paused) {
    elements.audio.pause();
    elements.audio.currentTime = 0;
  }
  drawIdleSpectrum();
}

function releaseAudioSource() {
  if (state.audioUrl) {
    URL.revokeObjectURL(state.audioUrl);
    state.audioUrl = null;
  }
  elements.audio.removeAttribute("src");
  elements.audio.load();
  elements.audio.hidden = true;
}

function base64ToBlob(base64, mimeType) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new Blob([bytes], { type: mimeType });
}

async function playServerAudio(data) {
  stopPlayback();
  const generation = state.speechGeneration;
  releaseAudioSource();
  const blob = base64ToBlob(data.audio_base64, data.audio_mime_type || "audio/wav");
  state.audioUrl = URL.createObjectURL(blob);
  elements.audio.src = state.audioUrl;
  elements.audio.hidden = false;
  elements.voiceMode.textContent = `${data.tts_engine} audio ready.`;
  try {
    await elements.audio.play();
  } catch {
    if (generation === state.speechGeneration) {
      elements.voiceMode.textContent = "Audio is ready — press play to hear the response.";
    }
  }
}

function refreshBrowserVoices() {
  state.voices = window.speechSynthesis?.getVoices() || [];
}

function browserVoiceFor(persona) {
  if (!state.voices.length) refreshBrowserVoices();
  const preferences = persona.browser_voice_names || [];
  for (const preference of preferences) {
    const match = state.voices.find((voice) => voice.name.toLowerCase().includes(preference.toLowerCase()));
    if (match) return match;
  }
  return state.voices.find((voice) => voice.lang.startsWith("en")) || state.voices[0] || null;
}

function speechChunks(text, maxLength = 240) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) return [];
  const sentences = normalized.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [normalized];
  const chunks = [];
  let current = "";
  for (let sentence of sentences) {
    sentence = sentence.trim();
    while (sentence.length > maxLength) {
      if (current) {
        chunks.push(current);
        current = "";
      }
      let cut = sentence.lastIndexOf(" ", maxLength);
      if (cut < maxLength * 0.5) cut = maxLength;
      chunks.push(sentence.slice(0, cut).trim());
      sentence = sentence.slice(cut).trim();
    }
    const candidate = `${current} ${sentence}`.trim();
    if (current && candidate.length > maxLength) {
      chunks.push(current);
      current = sentence;
    } else {
      current = candidate;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

function speakInBrowser(text, personaId = selectedPersonaId()) {
  elements.audio.hidden = true;
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
    elements.voiceMode.textContent = "Browser speech is unavailable on this device; the text answer is ready.";
    drawIdleSpectrum();
    return;
  }
  stopPlayback();
  const generation = state.speechGeneration;
  const persona = personaFor(personaId);
  const chunks = speechChunks(text);
  if (!chunks.length) return;

  const speakNext = (index) => {
    if (generation !== state.speechGeneration) return;
    if (index >= chunks.length) {
      elements.voiceMode.textContent = "Browser speech finished.";
      drawIdleSpectrum();
      return;
    }
    const utterance = new SpeechSynthesisUtterance(chunks[index]);
    const voice = browserVoiceFor(persona);
    if (voice) utterance.voice = voice;
    utterance.lang = voice?.lang || "en-US";
    utterance.rate = personaId === "margaret" ? 0.96 : 0.91;
    utterance.onstart = () => {
      if (generation === state.speechGeneration) {
        elements.voiceMode.textContent = `Speaking with browser voice (${index + 1}/${chunks.length}); spectrum samples are not exposed by this API.`;
      }
    };
    utterance.onend = () => {
      if (generation === state.speechGeneration) {
        state.speechQueueTimer = setTimeout(() => speakNext(index + 1), 0);
      }
    };
    utterance.onerror = () => {
      if (generation === state.speechGeneration) {
        elements.voiceMode.textContent = "Browser speech stopped; the text answer remains available.";
        drawIdleSpectrum();
      }
    };
    window.speechSynthesis.speak(utterance);
  };

  state.speechQueueTimer = setTimeout(() => speakNext(0), 0);
}

function updateRecordingUI() {
  elements.mic.setAttribute("aria-pressed", String(state.recording));
  elements.micLabel.textContent = state.recording ? "Listening…" : "Speak";
}

function setupSpeechRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    state.micSupported = false;
    elements.mic.disabled = true;
    elements.mic.title = "Speech recognition is not supported in this browser. Type your question instead.";
    return;
  }
  state.micSupported = true;
  const recognition = new Recognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-US";
  recognition.onstart = () => {
    state.recording = true;
    state.submitAfterRecording = false;
    clearError();
    updateRecordingUI();
  };
  recognition.onresult = (event) => {
    let transcript = "";
    let final = false;
    for (let index = 0; index < event.results.length; index += 1) {
      transcript += `${event.results[index][0].transcript} `;
      final ||= event.results[index].isFinal;
    }
    elements.question.value = transcript.trim();
    state.submitAfterRecording = final;
  };
  recognition.onerror = (event) => {
    const messages = {
      "not-allowed": "Microphone access was not granted. Type your question instead.",
      "no-speech": "No speech was detected. Try again or type your question.",
      "audio-capture": "No usable microphone was found. Type your question instead.",
    };
    showError(messages[event.error] || "Speech recognition stopped. Type your question or try again.");
  };
  recognition.onend = () => {
    const shouldSubmit = state.submitAfterRecording;
    state.submitAfterRecording = false;
    state.recording = false;
    updateRecordingUI();
    setBusy(state.busy);
    if (shouldSubmit && elements.question.value.trim() && !state.busy) {
      elements.form.requestSubmit();
    }
  };
  state.recognition = recognition;
}

function toggleRecording() {
  if (!state.recognition || (state.busy && !state.recording)) return;
  stopPlayback();
  if (state.recording) {
    state.recognition.stop();
  } else {
    try {
      state.recognition.start();
    } catch {
      showError("The microphone is already starting. Wait a moment and try again.");
    }
  }
}

async function askProfessor(payload, signal) {
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok) {
    let message = `The knowledge server returned HTTP ${response.status}.`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch { /* Keep the status-based message. */ }
    throw new Error(message);
  }
  return response.json();
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy) return;
  const question = elements.question.value.trim();
  if (!question) {
    showError("Enter a question before sending.");
    elements.question.focus();
    return;
  }
  const personaId = selectedPersonaId();
  const payload = {
    question,
    persona_id: personaId,
    knowledge_id: elements.knowledge.value,
    answer_provider: elements.answerProvider.value,
    tts_provider: elements.ttsProvider.value,
  };
  if (state.recording) {
    state.submitAfterRecording = false;
    state.recognition?.stop();
  }
  clearError();
  stopPlayback();
  const requestSerial = ++state.requestSerial;
  state.activeController?.abort();
  const controller = new AbortController();
  state.activeController = controller;
  appendStudent(question);
  elements.question.value = "";
  elements.thinking.hidden = false;
  setBusy(true);
  try {
    const data = await askProfessor(payload, controller.signal);
    if (requestSerial !== state.requestSerial) return;
    appendProfessor(data);
    if (data.audio_base64) {
      await playServerAudio(data);
    } else {
      speakInBrowser(data.answer_text, personaId);
    }
  } catch (error) {
    if (error?.name === "AbortError" || requestSerial !== state.requestSerial) return;
    const message = error.message || "The knowledge server could not be reached.";
    showError(message);
    appendSystemError("Your question could not be answered in this request. Check the server and try again.");
    elements.question.value = question;
  } finally {
    if (requestSerial === state.requestSerial) {
      state.activeController = null;
      elements.thinking.hidden = true;
      setBusy(false);
      scrollTranscript();
    }
  }
});

elements.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
});
elements.question.addEventListener("input", clearError);
elements.knowledge.addEventListener("change", updateKnowledgeDescription);
document.querySelectorAll('input[name="persona"]').forEach((radio) => radio.addEventListener("change", updatePersona));
document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    elements.question.value = button.dataset.question;
    clearError();
    elements.question.focus();
  });
});

elements.mic.addEventListener("click", toggleRecording);
elements.clear.addEventListener("click", () => {
  state.requestSerial += 1;
  state.activeController?.abort();
  state.activeController = null;
  state.submitAfterRecording = false;
  if (state.recording) state.recognition?.stop();
  stopPlayback();
  releaseAudioSource();
  setBusy(false);
  elements.thinking.hidden = true;
  const welcome = state.welcome.cloneNode(true);
  welcome.querySelector(".message-author").textContent = selectedPersona().name;
  elements.transcript.replaceChildren(welcome);
  elements.question.value = "";
  elements.engineBadge.textContent = "Ready";
  elements.voiceMode.textContent = "Waiting for a professor response.";
  clearError();
  elements.question.focus();
});
elements.stopAudio.addEventListener("click", () => {
  const wasActive = !elements.audio.paused || window.speechSynthesis?.speaking;
  stopPlayback();
  elements.voiceMode.textContent = wasActive ? "Audio stopped." : "No audio is currently playing.";
});
elements.audio.addEventListener("play", async () => {
  const generation = state.speechGeneration;
  try {
    await prepareAudioGraph();
    if (generation !== state.speechGeneration || elements.audio.paused) return;
    elements.voiceMode.textContent = "Playing server-generated audio.";
    drawLiveSpectrum();
  } catch {
    if (generation === state.speechGeneration && !elements.audio.paused) {
      elements.voiceMode.textContent = "Playing audio; the spectrum is unavailable in this browser.";
    }
  }
});
elements.audio.addEventListener("pause", drawIdleSpectrum);
elements.audio.addEventListener("ended", () => {
  elements.voiceMode.textContent = "Audio playback finished.";
  drawIdleSpectrum();
});
window.addEventListener("resize", resizeCanvas);
window.addEventListener("beforeunload", () => {
  state.activeController?.abort();
  state.speechGeneration += 1;
  clearTimeout(state.speechQueueTimer);
  if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
  if (window.speechSynthesis) window.speechSynthesis.cancel();
});

if (window.speechSynthesis) {
  refreshBrowserVoices();
  if (typeof window.speechSynthesis.addEventListener === "function") {
    window.speechSynthesis.addEventListener("voiceschanged", refreshBrowserVoices);
  } else {
    window.speechSynthesis.onvoiceschanged = refreshBrowserVoices;
  }
}
setupSpeechRecognition();
resizeCanvas();
updateKnowledgeDescription();
loadConfiguration();
