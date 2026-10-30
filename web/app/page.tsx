"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui";

type Voice = {
  voice_id: string;
  language: string;
  accent: string;
  engine: string;
  status: "loaded" | "unavailable";
  description: string;
};

type HistoryEntry = {
  text: string;
  voice_id: string;
  preset: string;
  chars: number;
  latency_ms: string;
  at: string;
};

const HISTORY_KEY = "xploclone-history-v1";
const MAX_HISTORY = 50;
const MAX_CHARS = 5000;

const FALLBACK_VOICES: Voice[] = [
  {
    voice_id: "mubashir-en-gb",
    language: "en-GB",
    accent: "GB",
    engine: "chatterbox-turbo",
    status: "unavailable",
    description: "Mubashir Ali, English, British accent.",
  },
  {
    voice_id: "mubashir-en-us",
    language: "en-US",
    accent: "US",
    engine: "chatterbox-turbo",
    status: "unavailable",
    description: "Mubashir Ali, English, US accent.",
  },
];

const SAMPLES: { id: string; label: string; text: string }[] = [
  {
    id: "greeting",
    label: "Greeting",
    text: "Hello, thank you for speaking with me today. I hope you are doing well, and I am glad we could find a time to talk.",
  },
  {
    id: "recruitment",
    label: "Recruitment call",
    text: "Hi, this is Mubashir calling about the care assistant role in Kingsbury. The shift is Monday to Friday, nine to five, and the pay is fourteen pounds fifty per hour. Would you like me to book you in for an interview this week?",
  },
  {
    id: "longform",
    label: "Long-form test",
    text: "Good morning. Today I want to talk about how we prepare for a job interview. First, read the job description carefully, and write down three examples from your own work that match it. Second, practise saying them out loud, slowly, in short sentences. And third, arrive early, dress smartly, and bring a printed copy of your CV.",
  },
];

// Human-voice presets (api/prosody.py). Natural is the recommended
// starting point — the skill's flat-voice fix (exaggeration 0.7,
// CFG 0.3). Turbo 0.1.7 ignores exaggeration/CFG, so the audible
// variation comes from temperature/top_p — the UI says so instead of
// implying otherwise.
const PRESETS = [
  { id: "natural", label: "Natural", hint: "Most human variation — recommended" },
  { id: "warm", label: "Warm", hint: "Softer, friendlier" },
  { id: "firm", label: "Firm", hint: "Steadier, more formal" },
  { id: "default", label: "Default", hint: "Balanced" },
] as const;
type PresetId = (typeof PRESETS)[number]["id"];

type Knobs = { exaggeration: number; cfgWeight: number; temperature: number; topP: number; repetitionPenalty: number };
const PRESET_DEFAULTS: Record<PresetId, Knobs> = {
  natural: { exaggeration: 0.7, cfgWeight: 0.3, temperature: 0.9, topP: 0.95, repetitionPenalty: 1.2 },
  warm: { exaggeration: 0.6, cfgWeight: 0.4, temperature: 0.85, topP: 0.95, repetitionPenalty: 1.2 },
  firm: { exaggeration: 0.4, cfgWeight: 0.6, temperature: 0.75, topP: 0.9, repetitionPenalty: 1.3 },
  default: { exaggeration: 0.5, cfgWeight: 0.5, temperature: 0.8, topP: 0.95, repetitionPenalty: 1.2 },
};

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

function GenerateInner() {
  const searchParams = useSearchParams();
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voicesState, setVoicesState] = useState<"loading" | "ok" | "error">("loading");
  const [voiceId, setVoiceId] = useState("mubashir-en-gb");
  const [preset, setPreset] = useState<PresetId>("natural");
  const [knobs, setKnobs] = useState<Knobs>(PRESET_DEFAULTS.natural);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [text, setText] = useState("Hello, thank you for speaking with me today.");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioMeta, setAudioMeta] = useState<{ size: number; latency: string; preset: string; watermark: string } | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);
  const [copiedText, setCopiedText] = useState(false);
  const topRef = useRef<HTMLDivElement>(null);

  const loadVoices = useCallback(async () => {
    setVoicesState("loading");
    setError("");
    try {
      const res = await fetch("/api/voices");
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const d = await res.json();
      const list = (d.voices ?? []) as Voice[];
      setVoices(list.length > 0 ? list : FALLBACK_VOICES);
      setVoicesState("ok");
    } catch {
      setVoices(FALLBACK_VOICES);
      setVoicesState("error");
      setError("Could not reach the API. Voice status is unknown — check the Health page, then retry.");
    }
  }, []);

  useEffect(() => {
    void loadVoices();
    try {
      const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]") as HistoryEntry[];
      setHistory(Array.isArray(saved) ? saved.slice(0, MAX_HISTORY) : []);
    } catch {
      setHistory([]);
    }
  }, [loadVoices]);

  // Voices page links here with ?voice=mubashir-en-us to pre-select a voice.
  useEffect(() => {
    const v = searchParams.get("voice");
    if (v === "mubashir-en-us" || v === "mubashir-en-gb") setVoiceId(v);
  }, [searchParams]);

  function showToast(msg: string) {
    setToast(msg);
    window.setTimeout(() => setToast(""), 2500);
  }

  function pickPreset(id: PresetId) {
    setPreset(id);
    setKnobs(PRESET_DEFAULTS[id]);
  }

  const isCustom =
    knobs.exaggeration !== PRESET_DEFAULTS[preset].exaggeration ||
    knobs.cfgWeight !== PRESET_DEFAULTS[preset].cfgWeight ||
    knobs.temperature !== PRESET_DEFAULTS[preset].temperature ||
    knobs.topP !== PRESET_DEFAULTS[preset].topP ||
    knobs.repetitionPenalty !== PRESET_DEFAULTS[preset].repetitionPenalty;

  function resetKnobs() {
    setKnobs(PRESET_DEFAULTS[preset]);
    showToast(`Prosody reset to the ${preset} preset.`);
  }

  async function copyText() {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedText(true);
      window.setTimeout(() => setCopiedText(false), 2000);
    } catch {
      setError("Copy failed — your browser blocked clipboard access. Select the text manually.");
    }
  }

  function loadHistoryEntry(h: HistoryEntry) {
    setText(h.text.slice(0, MAX_CHARS));
    if (h.voice_id === "mubashir-en-us" || h.voice_id === "mubashir-en-gb") setVoiceId(h.voice_id);
    if (h.preset === "natural" || h.preset === "warm" || h.preset === "firm" || h.preset === "default") {
      pickPreset(h.preset);
    }
    setError("");
    setStatus("");
    showToast("Loaded from history — press Generate to re-create it.");
    topRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  function removeHistoryEntry(index: number) {
    setHistory((prev) => {
      const next = prev.filter((_, i) => i !== index);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
      return next;
    });
  }

  function clearHistory() {
    if (!confirmClear) {
      setConfirmClear(true);
      window.setTimeout(() => setConfirmClear(false), 4000);
      return;
    }
    localStorage.removeItem(HISTORY_KEY);
    setHistory([]);
    setConfirmClear(false);
    showToast("History cleared.");
  }

  async function generate() {
    if (text.trim().length === 0 || busy) return;
    setError("");
    setStatus("");
    setBusy(true);
    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          voice_id: voiceId,
          text,
          preset,
          exaggeration: knobs.exaggeration,
          cfg_weight: knobs.cfgWeight,
          temperature: knobs.temperature,
          top_p: knobs.topP,
          repetition_penalty: knobs.repetitionPenalty,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = body?.detail;
        const message =
          typeof detail === "string" ? detail : detail?.message ?? `Request failed (${res.status})`;
        setError(message);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl((old) => {
        if (old) URL.revokeObjectURL(old);
        return url;
      });
      const latency = res.headers.get("X-XploClone-Latency-Ms") ?? "?";
      const returnedPreset = res.headers.get("X-XploClone-Preset") ?? preset;
      const watermark = res.headers.get("X-Watermark") ?? "perth-unverified";
      setAudioMeta({ size: blob.size, latency, preset: returnedPreset, watermark });
      setStatus(`Generated in ${latency} ms · ${text.length} chars · ${voiceId} · ${returnedPreset}`);
      const entry: HistoryEntry = {
        text,
        voice_id: voiceId,
        preset: returnedPreset,
        chars: text.length,
        latency_ms: latency,
        at: new Date().toISOString(),
      };
      setHistory((prev) => {
        const next = [entry, ...prev].slice(0, MAX_HISTORY);
        try {
          localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
        } catch {
          // Storage full / private mode: history is best-effort, generation is not.
        }
        return next;
      });
    } catch {
      setError("Network error — is the API server running? Check the Health page.");
    } finally {
      setBusy(false);
    }
  }

  const selected = voices.find((v) => v.voice_id === voiceId);
  const urdu = voices.find((v) => v.voice_id === "mubashir-ur");
  const voiceUnavailable = selected?.status !== "loaded";
  const canGenerate = !busy && text.trim().length > 0 && !voiceUnavailable;

  return (
    <main ref={topRef} className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Generate audio</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Mubashir Ali&apos;s voice only. English (US / British) in Phase 1. Urdu is in
            research — no engine yet.
          </p>
        </div>
        <Badge tone={voicesState === "error" ? "red" : "green"}>
          {voicesState === "loading"
            ? "Checking voices…"
            : voicesState === "error"
              ? "API unreachable"
              : `${voices.filter((v) => v.status === "loaded").length} of ${voices.length} voices ready`}
        </Badge>
      </div>

      {error && (
        <div role="alert" className="fade-in mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => void loadVoices()}
            className="rounded-lg bg-red-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-800"
          >
            Retry
          </button>
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        {/* Main column: text, generate, result, history */}
        <div className="min-w-0 space-y-6">
          <section aria-labelledby="text-heading" className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="text-heading" className="text-base font-semibold">
                <label htmlFor="text">Your text</label>
              </h2>
              <span className="text-xs text-zinc-500" aria-live="polite">
                {text.length} / {MAX_CHARS} characters
              </span>
            </div>
            <textarea
              id="text"
              value={text}
              onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
              rows={7}
              placeholder="Type or paste the text to speak…"
              className="mt-3 w-full rounded-xl border border-zinc-300 bg-white p-3 text-sm leading-relaxed focus:border-indigo-500"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="mr-1 self-center text-xs font-medium text-zinc-500">Try a sample:</span>
              {SAMPLES.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    setText(s.text);
                    setError("");
                    showToast(`Loaded the ${s.label.toLowerCase()} sample.`);
                  }}
                  className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
                >
                  {s.label}
                </button>
              ))}
              <span className="flex-1" />
              <button
                type="button"
                onClick={() => void copyText()}
                disabled={text.length === 0}
                className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {copiedText ? "✓ Copied" : "Copy text"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setText("");
                  setError("");
                }}
                disabled={text.length === 0}
                className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Clear text
              </button>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-zinc-500">
              Short sentences, one idea per sentence, sound the most human. Commas give
              short pauses, full stops longer ones. Tags{" "}
              <code className="rounded bg-zinc-100 px-1">[laugh]</code>{" "}
              <code className="rounded bg-zinc-100 px-1">[sigh]</code>{" "}
              <code className="rounded bg-zinc-100 px-1">[chuckle]</code> are the only ones
              that pass through — anything else is stripped.
            </p>
          </section>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => void generate()}
              disabled={!canGenerate}
              title={
                voiceUnavailable
                  ? "This voice is unavailable — no reference recording on the server yet."
                  : text.trim().length === 0
                    ? "Enter some text first."
                    : "Generate audio"
              }
              className="w-full rounded-xl bg-zinc-900 px-6 py-3 text-sm font-semibold text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
            >
              {busy ? "Generating…" : "Generate audio"}
            </button>
            {voiceUnavailable && (
              <p className="text-sm text-amber-700">
                This voice is unavailable — no reference recording on the server yet.
                Record the set in <code className="rounded bg-amber-100 px-1">docs/recording-scripts/</code> to enable it.
              </p>
            )}
          </div>

          {status && <p className="text-sm text-zinc-600">{status}</p>}

          {audioUrl && audioMeta && (
            <section aria-label="Generated audio" className="fade-in rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-base font-semibold">Result</h2>
                <div className="flex flex-wrap gap-2">
                  <Badge tone="green">WAV · {formatBytes(audioMeta.size)}</Badge>
                  <Badge tone="grey">Watermark: {audioMeta.watermark}</Badge>
                </div>
              </div>
              <audio controls src={audioUrl} className="mt-4 w-full" />
              <div className="mt-4 flex flex-wrap gap-2">
                <a
                  href={audioUrl}
                  download={`xploclone-${voiceId}-${new Date().toISOString().slice(0, 10)}.wav`}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Download WAV
                </a>
                <button
                  type="button"
                  onClick={() => void generate()}
                  disabled={busy}
                  className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-40"
                >
                  Re-generate
                </button>
              </div>
              <p className="mt-3 text-xs text-zinc-500">
                Generated in {audioMeta.latency} ms · preset {audioMeta.preset}
                {isCustom ? " (custom knobs)" : ""} · {voiceId}
              </p>
            </section>
          )}

          <section aria-labelledby="history-heading" className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="history-heading" className="text-base font-semibold">
                History <span className="text-sm font-normal text-zinc-500">(last {MAX_HISTORY}, this browser only)</span>
              </h2>
              {history.length > 0 && (
                <button
                  type="button"
                  onClick={clearHistory}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                    confirmClear
                      ? "border-red-300 bg-red-50 text-red-700 hover:bg-red-100"
                      : "border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50"
                  }`}
                >
                  {confirmClear ? "Click again to confirm clear" : "Clear history"}
                </button>
              )}
            </div>
            {history.length === 0 ? (
              <p className="mt-3 text-sm text-zinc-500">
                No generations yet. Your last {MAX_HISTORY} generations will appear here —
                click <strong>Load</strong> on any entry to put its text, voice and preset
                back into the form.
              </p>
            ) : (
              <ul className="mt-4 space-y-3">
                {history.map((h, i) => (
                  <li key={`${h.at}-${i}`} className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-medium">
                        {h.voice_id} · {h.preset ?? "default"} · {h.chars} chars · {h.latency_ms} ms
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => loadHistoryEntry(h)}
                          className="rounded-lg border border-zinc-300 bg-white px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
                        >
                          Load
                        </button>
                        <button
                          type="button"
                          onClick={() => removeHistoryEntry(i)}
                          aria-label={`Delete history entry from ${new Date(h.at).toLocaleString()}`}
                          className="rounded-lg border border-zinc-300 bg-white px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-red-50 hover:text-red-700"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    <div className="mt-1 text-zinc-600">{h.text.slice(0, 120)}{h.text.length > 120 ? "…" : ""}</div>
                    <div className="mt-1 text-xs text-zinc-400">{new Date(h.at).toLocaleString()}</div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        {/* Sidebar: voice + preset + advanced prosody */}
        <aside className="space-y-6">
          <section aria-labelledby="voice-heading" className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
            <h2 id="voice-heading" className="text-base font-semibold">Voice</h2>
            <p className="mt-1 text-xs text-zinc-500">Only your voice, in two English accents.</p>
            <div className="mt-4 space-y-2" role="group" aria-label="Choose a voice">
              {voices
                .filter((v) => v.voice_id !== "mubashir-ur")
                .map((v) => {
                  const active = voiceId === v.voice_id;
                  const loaded = v.status === "loaded";
                  return (
                    <button
                      key={v.voice_id}
                      type="button"
                      onClick={() => setVoiceId(v.voice_id)}
                      disabled={!loaded}
                      aria-pressed={active}
                      title={loaded ? v.description : "Unavailable — no reference recording on the server yet."}
                      className={`flex w-full items-center justify-between gap-2 rounded-xl border p-3 text-left text-sm transition-colors ${
                        active
                          ? "border-zinc-900 bg-zinc-900 text-white"
                          : "border-zinc-300 bg-white hover:bg-zinc-50"
                      } disabled:cursor-not-allowed disabled:opacity-50`}
                    >
                      <span>
                        <span className="block font-medium">
                          {v.language === "en-US" ? "🇺🇸 English (US)" : "🇬🇧 English (British)"}
                        </span>
                        <span className={`block text-xs ${active ? "text-zinc-300" : "text-zinc-500"}`}>
                          {v.voice_id}
                        </span>
                      </span>
                      <Badge tone={loaded ? "green" : "amber"}>{loaded ? "Ready" : "Unavailable"}</Badge>
                    </button>
                  );
                })}
              {voices.length === 0 && (
                <p className="text-sm text-zinc-500">Loading voices…</p>
              )}
              {urdu && (
                <div className="flex w-full items-center justify-between gap-2 rounded-xl border border-zinc-200 bg-zinc-100 p-3 text-sm text-zinc-500">
                  <span>
                    <span className="block font-medium">🇵🇰 Urdu</span>
                    <span className="block text-xs">mubashir-ur · in research, no engine yet</span>
                  </span>
                  <Badge tone="grey">In research</Badge>
                </div>
              )}
            </div>
            {voicesState === "error" && (
              <button
                type="button"
                onClick={() => void loadVoices()}
                className="mt-3 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
              >
                Retry loading voices
              </button>
            )}
          </section>

          <section aria-labelledby="preset-heading" className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <h2 id="preset-heading" className="text-base font-semibold">Style preset</h2>
              {isCustom && <Badge tone="indigo">Custom</Badge>}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2" role="group" aria-label="Choose a style preset">
              {PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => pickPreset(p.id)}
                  title={p.hint}
                  aria-pressed={preset === p.id && !isCustom}
                  className={`rounded-xl border p-3 text-left text-sm transition-colors ${
                    preset === p.id && !isCustom
                      ? "border-zinc-900 bg-zinc-900 text-white"
                      : "border-zinc-300 bg-white hover:bg-zinc-50"
                  }`}
                >
                  <span className="block font-medium">{p.label}</span>
                  <span className={`block text-xs ${preset === p.id && !isCustom ? "text-zinc-300" : "text-zinc-500"}`}>
                    {p.hint}
                  </span>
                </button>
              ))}
            </div>
            <p className="mt-3 text-xs leading-relaxed text-zinc-500">
              Natural is the recommended starting point. Higher exaggeration = more human
              variation, lower CFG = less anchored to the reference. Note: Chatterbox
              Turbo 0.1.7 ignores exaggeration/CFG, so presets vary the voice through
              sampling (temperature/top-p) — change one knob at a time and re-listen
              to the same script.
            </p>
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              aria-expanded={showAdvanced}
              aria-controls="advanced-prosody"
              className="mt-4 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
            >
              {showAdvanced ? "Hide advanced prosody ↑" : "Advanced prosody…"}
            </button>
            {showAdvanced && (
              <div id="advanced-prosody" className="mt-4 space-y-5 border-t border-zinc-100 pt-4">
                <div>
                  <label className="block text-sm font-medium" htmlFor="exaggeration">
                    Exaggeration — {knobs.exaggeration.toFixed(2)}
                  </label>
                  <input
                    id="exaggeration"
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={knobs.exaggeration}
                    onChange={(e) => setKnobs((k) => ({ ...k, exaggeration: Number(e.target.value) }))}
                    className="mt-2 w-full"
                  />
                  <p className="text-xs text-zinc-500">Preset default: {PRESET_DEFAULTS[preset].exaggeration.toFixed(2)} · no audible effect on Turbo 0.1.7</p>
                </div>
                <div>
                  <label className="block text-sm font-medium" htmlFor="cfg">
                    CFG weight — {knobs.cfgWeight.toFixed(2)}
                  </label>
                  <input
                    id="cfg"
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={knobs.cfgWeight}
                    onChange={(e) => setKnobs((k) => ({ ...k, cfgWeight: Number(e.target.value) }))}
                    className="mt-2 w-full"
                  />
                  <p className="text-xs text-zinc-500">Preset default: {PRESET_DEFAULTS[preset].cfgWeight.toFixed(2)} · no audible effect on Turbo 0.1.7</p>
                </div>
                <div>
                  <label className="block text-sm font-medium" htmlFor="temperature">
                    Temperature — {knobs.temperature.toFixed(2)}
                  </label>
                  <input
                    id="temperature"
                    type="range"
                    min={0.1}
                    max={1.5}
                    step={0.05}
                    value={knobs.temperature}
                    onChange={(e) => setKnobs((k) => ({ ...k, temperature: Number(e.target.value) }))}
                    className="mt-2 w-full"
                  />
                  <p className="text-xs text-zinc-500">Preset default: {PRESET_DEFAULTS[preset].temperature.toFixed(2)} · this one Turbo honours — raise if still flat, lower if unstable</p>
                </div>
                <div>
                  <label className="block text-sm font-medium" htmlFor="top-p">
                    Top-p — {knobs.topP.toFixed(2)}
                  </label>
                  <input
                    id="top-p"
                    type="range"
                    min={0.05}
                    max={1}
                    step={0.05}
                    value={knobs.topP}
                    onChange={(e) => setKnobs((k) => ({ ...k, topP: Number(e.target.value) }))}
                    className="mt-2 w-full"
                  />
                  <p className="text-xs text-zinc-500">Preset default: {PRESET_DEFAULTS[preset].topP.toFixed(2)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium" htmlFor="rep-penalty">
                    Repetition penalty — {knobs.repetitionPenalty.toFixed(2)}
                  </label>
                  <input
                    id="rep-penalty"
                    type="range"
                    min={1}
                    max={2}
                    step={0.05}
                    value={knobs.repetitionPenalty}
                    onChange={(e) => setKnobs((k) => ({ ...k, repetitionPenalty: Number(e.target.value) }))}
                    className="mt-2 w-full"
                  />
                  <p className="text-xs text-zinc-500">Preset default: {PRESET_DEFAULTS[preset].repetitionPenalty.toFixed(2)}</p>
                </div>
                <button
                  type="button"
                  onClick={resetKnobs}
                  className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
                >
                  Reset to {preset} preset
                </button>
                <p className="text-xs text-zinc-500">
                  These knobs are recorded with every generation. Exaggeration/CFG take
                  effect only if the engine is ever swapped for the full Chatterbox
                  model.
                </p>
              </div>
            )}
          </section>

          <section aria-labelledby="limits-heading" className="rounded-2xl border border-zinc-200 bg-white p-5 text-sm shadow-sm">
            <h2 id="limits-heading" className="text-base font-semibold">What this UI cannot do yet</h2>
            <ul className="mt-3 list-disc space-y-1.5 pl-5 text-zinc-600">
              <li>Urdu generation — gated research spike, no engine yet.</li>
              <li>Live-call streaming — Phase 3 (WebSocket, Xplogent).</li>
              <li>MP3 output — WAV / PCM16 only in Phase 1.</li>
              <li>Adding a voice — your voice only, by design.</li>
            </ul>
          </section>
        </aside>
      </div>

      {toast && (
        <div role="status" className="toast-in fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-full bg-zinc-900 px-4 py-2 text-sm font-medium text-white shadow-lg">
          {toast}
        </div>
      )}
    </main>
  );
}

export default function GeneratePage() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-6xl px-4 py-10"><p className="text-sm text-zinc-500">Loading Generate…</p></main>}>
      <GenerateInner />
    </Suspense>
  );
}
