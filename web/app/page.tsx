"use client";

import { useEffect, useRef, useState } from "react";

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

// Human-voice presets (api/prosody.py). Defaults: Natural is the
// recommended starting point — it is the skill's flat-voice fix
// (exaggeration 0.7, CFG 0.3). Turbo 0.1.7 ignores exaggeration/CFG,
// so the audible variation comes from temperature/top_p — the UI
// says so next to the sliders instead of implying otherwise.
const PRESETS = [
  { id: "natural", label: "Natural", hint: "most human variation" },
  { id: "warm", label: "Warm", hint: "softer, friendlier" },
  { id: "firm", label: "Firm", hint: "steadier, more formal" },
  { id: "default", label: "Default", hint: "balanced" },
] as const;
type PresetId = (typeof PRESETS)[number]["id"];

const PRESET_DEFAULTS: Record<PresetId, { exaggeration: number; cfgWeight: number }> = {
  natural: { exaggeration: 0.7, cfgWeight: 0.3 },
  warm: { exaggeration: 0.6, cfgWeight: 0.4 },
  firm: { exaggeration: 0.4, cfgWeight: 0.6 },
  default: { exaggeration: 0.5, cfgWeight: 0.5 },
};

export default function GeneratePage() {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voiceId, setVoiceId] = useState("mubashir-en-gb");
  const [preset, setPreset] = useState<PresetId>("natural");
  const [showAdvanced, setShowAdvanced] = useState(false);
  // Advanced sliders: explicit knobs override the preset. Defaults
  // track the selected preset (see PRESET_DEFAULTS below).
  const [exaggeration, setExaggeration] = useState(0.7);
  const [cfgWeight, setCfgWeight] = useState(0.3);
  const [text, setText] = useState("Hello, thank you for speaking with me today.");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    fetch("/api/voices")
      .then((r) => r.json())
      .then((d) => setVoices(d.voices ?? []))
      .catch(() => setError("Could not reach the API. Is the API server running?"));
    try {
      const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]") as HistoryEntry[];
      setHistory(Array.isArray(saved) ? saved.slice(0, MAX_HISTORY) : []);
    } catch {
      setHistory([]);
    }
  }, []);

  function pickPreset(id: PresetId) {
    setPreset(id);
    setExaggeration(PRESET_DEFAULTS[id].exaggeration);
    setCfgWeight(PRESET_DEFAULTS[id].cfgWeight);
  }

  async function generate() {
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
          exaggeration,
          cfg_weight: cfgWeight,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = body?.detail;
        const message =
          typeof detail === "string" ? detail : detail?.message ?? `Request failed (${res.status})`;
        // Urdu with no engine is a 503, not a bug — say so plainly.
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
      setStatus(`Generated in ${latency} ms · ${text.length} chars · ${voiceId} · ${returnedPreset}`);
      const entry: HistoryEntry = {
        text: text.slice(0, 120),
        voice_id: voiceId,
        preset: returnedPreset,
        chars: text.length,
        latency_ms: latency,
        at: new Date().toISOString(),
      };
      setHistory((prev) => {
        const next = [entry, ...prev].slice(0, MAX_HISTORY);
        localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
        return next;
      });
    } catch {
      setError("Network error — is the API server running?");
    } finally {
      setBusy(false);
    }
  }

  const selected = voices.find((v) => v.voice_id === voiceId);
  const urdu = voices.find((v) => v.voice_id === "mubashir-ur");

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">XploClone — Generate</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Mubashir Ali&apos;s voice only. English (US / British) in Phase 1.
        {urdu ? " Urdu is in research — no engine yet." : ""}
      </p>

      <label className="mt-6 block text-sm font-medium">Voice</label>
      <div className="mt-2 flex flex-wrap gap-2">
        {voices
          .filter((v) => v.voice_id !== "mubashir-ur")
          .map((v) => (
            <button
              key={v.voice_id}
              onClick={() => setVoiceId(v.voice_id)}
              disabled={v.status !== "loaded"}
              className={`rounded-full border px-4 py-2 text-sm ${
                voiceId === v.voice_id
                  ? "border-zinc-900 bg-zinc-900 text-white"
                  : "border-zinc-300 bg-white"
              } disabled:cursor-not-allowed disabled:opacity-40`}
            >
              {v.language === "en-US" ? "🇺🇸 English (US)" : "🇬🇧 English (British)"}
              {v.status !== "loaded" ? " — unavailable" : ""}
            </button>
          ))}
        {urdu && (
          <span className="rounded-full border border-zinc-200 bg-zinc-100 px-4 py-2 text-sm text-zinc-500">
            🇵🇰 Urdu — in research
          </span>
        )}
      </div>
      {selected?.status !== "loaded" && (
        <p className="mt-2 text-sm text-amber-700">
          This voice is unavailable — no reference recording on the server yet.
          Record the 20-minute set (docs/recording-scripts/) to enable it.
        </p>
      )}

      <label className="mt-6 block text-sm font-medium">Style preset</label>
      <div className="mt-2 flex flex-wrap gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.id}
            onClick={() => pickPreset(p.id)}
            title={p.hint}
            className={`rounded-full border px-4 py-2 text-sm ${
              preset === p.id
                ? "border-zinc-900 bg-zinc-900 text-white"
                : "border-zinc-300 bg-white"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>
      <p className="mt-1 text-xs text-zinc-500">
        Natural is the recommended starting point. Higher exaggeration = more human
        variation, lower CFG = less anchored to the reference. Note: Chatterbox
        Turbo 0.1.7 ignores exaggeration/CFG, so presets vary the voice through
        sampling (temperature/top-p) — change one knob at a time and re-listen
        to the same script.
      </p>

      <button
        onClick={() => setShowAdvanced((v) => !v)}
        className="mt-3 text-sm font-medium underline"
      >
        {showAdvanced ? "Hide advanced prosody" : "Advanced prosody…"}
      </button>
      {showAdvanced && (
        <div className="mt-3 space-y-4 rounded-lg border border-zinc-200 bg-white p-4">
          <div>
            <label className="block text-sm font-medium" htmlFor="exaggeration">
              Exaggeration — {exaggeration.toFixed(2)} (default {PRESET_DEFAULTS[preset].exaggeration.toFixed(2)})
            </label>
            <input
              id="exaggeration"
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={exaggeration}
              onChange={(e) => setExaggeration(Number(e.target.value))}
              className="mt-1 w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium" htmlFor="cfg">
              CFG weight — {cfgWeight.toFixed(2)} (default {PRESET_DEFAULTS[preset].cfgWeight.toFixed(2)})
            </label>
            <input
              id="cfg"
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={cfgWeight}
              onChange={(e) => setCfgWeight(Number(e.target.value))}
              className="mt-1 w-full"
            />
          </div>
          <p className="text-xs text-zinc-500">
            These two knobs are recorded with every generation but have no audible
            effect on Turbo 0.1.7 (the engine ignores them). They take effect if
            the engine is ever swapped for the full Chatterbox model. The preset
            itself works today through sampling variation.
          </p>
        </div>
      )}

      <label className="mt-6 block text-sm font-medium" htmlFor="text">
        Text (max 5,000 characters)
      </label>
      <textarea
        id="text"
        value={text}
        onChange={(e) => setText(e.target.value.slice(0, 5000))}
        rows={6}
        className="mt-2 w-full rounded-lg border border-zinc-300 bg-white p-3 text-sm"
      />
      <p className="mt-1 text-right text-xs text-zinc-500">{text.length} / 5000</p>

      <button
        onClick={generate}
        disabled={busy || text.trim().length === 0}
        className="mt-4 rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
      >
        {busy ? "Generating…" : "Generate audio"}
      </button>

      {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {status && <p className="mt-4 text-sm text-zinc-600">{status}</p>}
      {audioUrl && (
        <div className="mt-4 rounded-lg border border-zinc-200 bg-white p-4">
          <audio ref={audioRef} controls src={audioUrl} className="w-full" />
          <a href={audioUrl} download={`xploclone-${voiceId}.wav`} className="mt-2 inline-block text-sm font-medium underline">
            Download WAV
          </a>
        </div>
      )}

      <h2 className="mt-10 text-lg font-semibold">History (last {MAX_HISTORY}, this browser only)</h2>
      {history.length === 0 ? (
        <p className="mt-2 text-sm text-zinc-500">No generations yet.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {history.map((h, i) => (
            <li key={i} className="rounded-lg border border-zinc-200 bg-white p-3 text-sm">
              <div className="font-medium">{h.voice_id} · {h.preset ?? "default"} · {h.chars} chars · {h.latency_ms} ms</div>
              <div className="text-zinc-600">{h.text}</div>
              <div className="text-xs text-zinc-400">{new Date(h.at).toLocaleString()}</div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
