/**
 * MotoPulse™ Cockpit - AI Vehicle Acoustic & Vibration Telemetry UI
 * 
 * High-performance 60 FPS Canvas Telemetry visualizers:
 * 1. Dual-Microphone Oscilloscope (#scopeCanvas): 4cm baseline acoustic gradient (Left Cyan, Right Emerald)
 * 2. 50cm Acoustic Perimeter Radar (#radarCanvas): Circular sweep, proximity detection, lock states
 * 3. Piezo Seismograph (#seismoCanvas): Rolling mechanical vibration time-series chart & knock alerts
 * 4. Live Acoustic Ear & 32-Band Spectrum (#spectrumCanvas): Auto-listening, zero-recording ephemeral stream
 * 5. MotoPulse™ AI Predictive Prognostics Horizon Engine: 8-class continuous probabilities, RUL (km/hrs), health stages
 * 6. Resilient WebSocket client (ws://localhost:8765) with auto-reconnection & lifelike simulation fallback
 *
 * Co-authored-by: ishannvn <ishannvn@users.noreply.github.com>
 */

(function () {
  'use strict';

  // --- Core 9 Automotive Defect Prognostic Definitions ---
  const CORE9_CLASSES = [
    { key: "normal_idle", label: "Normal Engine Idle", icon: "🟢", desc: "Optimal Baseline Harmonics", color: "green" },
    { key: "valve_ticking", label: "Valve Lifter Clearance", icon: "🟡", desc: "Hydraulic Lifter Play", color: "orange" },
    { key: "bearing_wear", label: "Bearing Shell Fatigue", icon: "🟠", desc: "Auxiliary / Rod Friction", color: "orange" },
    { key: "engine_knocking", label: "Detonation / Knock Shock", icon: "🔴", desc: "Pre-ignition Detonation", color: "red" },
    { key: "belt_slippage", label: "Accessory Belt Slip", icon: "🟠", desc: "Elastomer Glaze & Creep", color: "orange" },
    { key: "exhaust_leak", label: "Exhaust Manifold Leak", icon: "🟠", desc: "Flange Pressure Blowby", color: "orange" },
    { key: "misfire", label: "Cylinder Misfire", icon: "🔴", desc: "Combustion Quench Event", color: "red" },
    { key: "turbo_flutter", label: "Turbo Surge / Flutter", icon: "🟣", desc: "Diverter Valve Stiction", color: "orange" },
    { key: "brake_grinding", label: "Brake Pad / Rotor Wear", icon: "🛑", desc: "Rotor Friction Grinding", color: "red" }
  ];

  // --- Global Telemetry State ---
  const state = {
    // WebSocket & hardware connection
    ws: null,
    wsConnected: false,
    reconnectTimer: null,
    lastPacketTime: 0,
    isSimulating: true,

    // Telemetry values
    mic1Peak: 0,
    mic2Peak: 0,
    gradPct: 0,
    piezoAmp: 0,
    piezoRaw: 2710,
    piezoBaseline: 2710,
    piezoPeakHold: 0,
    isNear: false,
    nearHoldFrames: 0,
    knockDetected: false,
    knockHoldFrames: 0,
    distanceCm: 120,

    // Target values for smooth interpolation
    targetMic1: 180,
    targetMic2: 175,
    targetGrad: 3,
    targetPiezoAmp: 12,
    targetDistance: 120,

    // Waveform buffers for Oscilloscope (128 samples each)
    waveLeft: new Float32Array(128),
    waveRight: new Float32Array(128),
    wavePhase: 0,

    // Rolling history for Seismograph (250 points)
    seismoHistory: new Float32Array(250).fill(2710),
    seismoIdx: 0,

    // Radar scan state
    radarAngle: 0,
    radarTargets: [], // Array of { angle, distRatio, intensity, isNear, age }

    // Performance & FPS counter
    frameCount: 0,
    fps: 60,
    lastFpsUpdate: performance.now(),

    // Live Acoustic Ear & Web Audio API
    audioCtx: null,
    audioGain: null,
    isAudioListening: true,
    audioVolume: 0.75,
    audioNextTime: 0,
    audioDbDecay: -42.0,

    // 32-Band Spectrum Monitor
    spectrum32: new Float32Array(32).fill(0.04),
    spectrumPeaks: new Float32Array(32).fill(0.04),

    // Predictive Prognostics Model State
    prediction: null,
    lastPredTime: 0,

    // Diagnostic Session State (5 - 15s Fixed Prediction Lock)
    diagDuration: 10,
    diagState: 'STREAMING',
    diagProgress: 0,
    smoothedProbs: {}
  };

  // --- DOM References ---
  const dom = {
    espStatus: document.getElementById('esp-status'),
    pillEsp: document.getElementById('pill-esp'),
    fpsBadge: document.getElementById('fps-badge'),

    // Diagnostic Session Controller
    btnDiag5s: document.getElementById('btn-diag-5s'),
    btnDiag10s: document.getElementById('btn-diag-10s'),
    btnDiag15s: document.getElementById('btn-diag-15s'),
    btnStartDiag: document.getElementById('btn-start-diag'),
    btnDiagIcon: document.getElementById('btn-diag-icon'),
    btnDiagText: document.getElementById('btn-diag-text'),
    btnResetDiag: document.getElementById('btn-reset-diag'),
    diagTimerStatus: document.getElementById('diag-timer-status'),
    diagTimerCountdown: document.getElementById('diag-timer-countdown'),
    diagFill: document.getElementById('diag-fill'),
    diagLockBadge: document.getElementById('diag-lock-badge'),
    lockIcon: document.getElementById('lock-icon'),
    lockText: document.getElementById('lock-text'),

    // Oscilloscope
    scopeCanvas: document.getElementById('scopeCanvas'),
    valMic1: document.getElementById('val-mic1'),
    valMic2: document.getElementById('val-mic2'),
    valGrad: document.getElementById('val-grad'),
    vuMic1: document.getElementById('vu-mic1'),
    vuMic2: document.getElementById('vu-mic2'),

    // Perimeter Radar
    radarCanvas: document.getElementById('radarCanvas'),
    gateBadge: document.getElementById('gate-badge'),
    radarStateBox: document.getElementById('radar-state-box'),
    gateStateIcon: document.getElementById('gate-state-icon'),
    gateStateTitle: document.getElementById('gate-state-title'),
    gateStateDesc: document.getElementById('gate-state-desc'),
    perimeterFill: document.getElementById('perimeter-fill'),

    // Piezo Seismograph
    seismoCanvas: document.getElementById('seismoCanvas'),
    knockAlertBox: document.getElementById('knock-alert-box'),
    piezoBase: document.getElementById('piezo-base'),
    piezoAmp: document.getElementById('piezo-amp'),
    piezoPeak: document.getElementById('piezo-peak'),
    vibeBadge: document.getElementById('vibe-badge'),

    // Live Acoustic Ear Monitor
    spectrumCanvas: document.getElementById('spectrumCanvas'),
    btnEarListen: document.getElementById('btn-ear-listen'),
    earIcon: document.getElementById('ear-icon'),
    earListenText: document.getElementById('ear-listen-text'),
    earVolume: document.getElementById('ear-volume'),
    volPct: document.getElementById('vol-pct'),
    earDbLevel: document.getElementById('ear-db-level'),

    // Continual Learner Panel
    learnerEnginePill: document.getElementById('learner-engine-pill'),
    learnerStatusPill: document.getElementById('learner-status-pill'),
    chipRegimes: [
      document.getElementById('chip-regime-0'),
      document.getElementById('chip-regime-1'),
      document.getElementById('chip-regime-2')
    ],
    learnerFrames: document.getElementById('learner-frames'),
    learnerGuard: document.getElementById('learner-guard'),
    learnerNvs: document.getElementById('learner-nvs'),
    zMeterBar: document.getElementById('z-meter-bar'),
    zMeterVal: document.getElementById('z-meter-val'),
    btnToggleEngine: document.getElementById('btn-toggle-engine'),
    btnInjectDefect: document.getElementById('btn-inject-defect'),
    btnResetLearner: document.getElementById('btn-reset-learner'),

    // AI Predictive Prognostics Horizon Engine
    predHealthBadge: document.getElementById('pred-health-badge'),
    healthHeroBanner: document.getElementById('health-hero-banner'),
    healthHeroIcon: document.getElementById('health-hero-icon'),
    healthHeroBadge: document.getElementById('health-hero-badge'),
    healthHeroTitle: document.getElementById('health-hero-title'),
    healthHeroSub: document.getElementById('health-hero-sub'),
    problemCard: document.getElementById('problem-card'),
    problemTitle: document.getElementById('problem-title'),
    problemSub: document.getElementById('problem-sub'),
    rulKm: document.getElementById('rul-km'),
    rulHours: document.getElementById('rul-hours'),
    healthScore: document.getElementById('health-score'),
    predRiskBadge: document.getElementById('pred-risk-badge'),
    progStageName: document.getElementById('prog-stage-name'),
    stageSteps: [
      document.getElementById('stage-step-0'),
      document.getElementById('stage-step-1'),
      document.getElementById('stage-step-2'),
      document.getElementById('stage-step-3')
    ],
    rxTrend: document.getElementById('rx-trend'),
    rxBody: document.getElementById('rx-body'),
    probDistribution: document.getElementById('prob-distribution'),
    primaryDiagnosis: document.getElementById('primary-diagnosis')
  };

  // --- Canvas Contexts ---
  let scopeCtx = null;
  let radarCtx = null;
  let seismoCtx = null;
  let spectrumCtx = null;

  function initCanvases() {
    if (dom.scopeCanvas) scopeCtx = dom.scopeCanvas.getContext('2d');
    if (dom.radarCanvas) radarCtx = dom.radarCanvas.getContext('2d');
    if (dom.seismoCanvas) seismoCtx = dom.seismoCanvas.getContext('2d');
    if (dom.spectrumCanvas) spectrumCtx = dom.spectrumCanvas.getContext('2d');
  }

  // --- WebSocket Telemetry Stream (ws://localhost:8765) ---
  function getWebSocketUrl() {
    const host = window.location.hostname || 'localhost';
    const port = '8765';
    return `ws://${host}:${port}`;
  }

  function connectWebSocket() {
    if (state.ws && (state.ws.readyState === WebSocket.CONNECTING || state.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    const wsUrl = getWebSocketUrl();
    try {
      state.ws = new WebSocket(wsUrl);

      state.ws.onopen = function () {
        console.log('[MotoPulse WS] Connected to live hardware stream:', wsUrl);
        state.wsConnected = true;
        state.isSimulating = false;
        if (dom.espStatus) dom.espStatus.textContent = 'ONLINE (USB-CDC)';
        if (dom.pillEsp) {
          dom.pillEsp.classList.add('active');
          dom.pillEsp.style.borderColor = 'rgba(0, 240, 255, 0.4)';
        }
      };

      state.ws.onmessage = function (event) {
        state.lastPacketTime = performance.now();
        state.isSimulating = false;
        handleIncomingPacket(event.data);
      };

      state.ws.onclose = function () {
        handleDisconnect();
      };

      state.ws.onerror = function () {
        handleDisconnect();
      };
    } catch (e) {
      handleDisconnect();
    }
  }

  function handleDisconnect() {
    state.wsConnected = false;
    state.isSimulating = true;
    if (dom.espStatus) dom.espStatus.textContent = 'AUTO-RECONNECTING...';
    if (dom.pillEsp) {
      dom.pillEsp.style.borderColor = 'rgba(255, 153, 0, 0.4)';
    }

    if (!state.reconnectTimer) {
      state.reconnectTimer = setTimeout(function () {
        state.reconnectTimer = null;
        connectWebSocket();
      }, 1800);
    }
  }

  // --- Incoming Packet Parser ---
  // Supports both compact MicroPython format:
  // "PKT:<p2p_l>:<p2p_r>:<piezo_p2p>:<piezo_raw>:<grad_pct>:<status>:<wave_chunk_base64>"
  // and JSON broadcasts: { p2p_l, p2p_r, piezo_p2p, piezo_raw, grad_pct, status, wave_l, wave_r, ... }
  function handleIncomingPacket(data) {
    if (!data) return;

    let pkt = null;

    if (typeof data === 'string' && data.startsWith('PKT:')) {
      const parts = data.slice(4).split(':');
      if (parts.length >= 5) {
        const p2p_l = parseInt(parts[0], 10) || 0;
        const p2p_r = parseInt(parts[1], 10) || 0;
        const piezo_p2p = parseInt(parts[2], 10) || 0;
        const piezo_raw = parseInt(parts[3], 10) || 2710;
        const grad_pct = parseInt(parts[4], 10) || 0;
        const status = parts[5] || 'ARMED';
        const wave_b64 = parts[6] || '';

        pkt = {
          p2p_l,
          p2p_r,
          piezo_p2p,
          piezo_raw,
          grad_pct,
          status,
          is_near: status.toUpperCase() === 'NEAR' || (Math.max(p2p_l, p2p_r) >= 1400 && grad_pct >= 10),
          knock: piezo_p2p > 220 || Math.abs(piezo_raw - state.piezoBaseline) > 220
        };

        if (wave_b64) {
          try {
            const rawBin = atob(wave_b64);
            const len = Math.min(64, rawBin.length);
            for (let i = 0; i < len; i++) {
              const val = (rawBin.charCodeAt(i) - 128) / 128.0;
              state.waveLeft[i * 2] = val;
              state.waveRight[i * 2] = val * (1.0 - (grad_pct / 120.0));
            }
          } catch (e) {}
        }
      }
    } else if (typeof data === 'string') {
      try {
        pkt = JSON.parse(data);
      } catch (e) {
        // Not JSON
      }
    } else if (typeof data === 'object') {
      pkt = data;
    }

    if (pkt) {
      applyTelemetryPacket(pkt);
    }
  }

  function applyTelemetryPacket(pkt) {
    const mic1 = pkt.p2p_l ?? pkt.mic1 ?? pkt.mic1_peak ?? pkt.left ?? 0;
    const mic2 = pkt.p2p_r ?? pkt.mic2 ?? pkt.mic2_peak ?? pkt.right ?? 0;
    const piezoP2p = pkt.piezo_p2p ?? pkt.piezo_amp ?? pkt.vibe ?? 0;
    const piezoRaw = pkt.piezo_raw ?? pkt.piezo_base ?? 2710;

    let grad = pkt.grad_pct ?? pkt.gradient;
    if (grad === undefined) {
      const maxMic = Math.max(mic1, mic2);
      grad = maxMic > 0 ? Math.round((Math.abs(mic1 - mic2) * 100) / maxMic) : 0;
    }

    const status = (pkt.status || '').toUpperCase();
    const isNear = pkt.is_near !== undefined
      ? Boolean(pkt.is_near)
      : (status === 'NEAR' || (Math.max(mic1, mic2) >= 1400 && grad >= 10));

    const isKnock = pkt.knock !== undefined
      ? Boolean(pkt.knock)
      : (piezoP2p > 220 || Math.abs(piezoRaw - state.piezoBaseline) > 220);

    // Update targets for smooth interpolation
    state.targetMic1 = mic1;
    state.targetMic2 = mic2;
    state.targetGrad = grad;
    state.targetPiezoAmp = piezoP2p;
    state.piezoRaw = piezoRaw;

    if (isNear) {
      state.isNear = true;
      state.nearHoldFrames = 45; // Hold near-field trigger on UI for ~750ms
      state.targetDistance = Math.max(10, Math.min(48, Math.round(50 - (grad * 0.9))));
      registerRadarTarget(state.targetDistance, grad, mic1 > mic2);
    }

    if (isKnock) {
      triggerKnockAlert();
    }

    // Damped wave arrays with exponential low-pass filter to eliminate high-frequency visual jitter
    if (Array.isArray(pkt.wave_l) && pkt.wave_l.length > 0) {
      const count = Math.min(128, pkt.wave_l.length);
      for (let i = 0; i < count; i++) {
        state.waveLeft[i] = state.waveLeft[i] * 0.45 + pkt.wave_l[i] * 0.55;
      }
    }
    if (Array.isArray(pkt.wave_r) && pkt.wave_r.length > 0) {
      const count = Math.min(128, pkt.wave_r.length);
      for (let i = 0; i < count; i++) {
        state.waveRight[i] = state.waveRight[i] * 0.45 + pkt.wave_r[i] * 0.55;
      }
    }

    // Diagnostic Session Telemetry Update (5 - 15s Fixed Prediction Lock)
    if (pkt.diagnostic_session) {
      updateDiagnosticSessionUI(pkt.diagnostic_session);
    }

    // Continual Learner Telemetry Update
    if (pkt.learner) {
      updateContinualLearnerUI(pkt.learner);
    }

    // Live continuous vehicle acoustic ear stream (Privacy-safe: zero recording saved)
    if (Array.isArray(pkt.audio_pcm) && pkt.audio_pcm.length > 0) {
      queueLivePcmAudio(pkt.audio_pcm);
    } else if (Array.isArray(pkt.wave_l) && pkt.wave_l.length > 0) {
      queueLivePcmAudio(pkt.wave_l);
    }

    // 32-Band Log-Mel Spectrum Stream
    if (Array.isArray(pkt.spectrum_32) && pkt.spectrum_32.length === 32) {
      updateSpectrumData(pkt.spectrum_32);
    } else if (pkt.prediction && Array.isArray(pkt.prediction.spectrum_32)) {
      updateSpectrumData(pkt.prediction.spectrum_32);
    }

    // AI Predictive Prognostics Engine
    if (pkt.prediction) {
      state.prediction = pkt.prediction;
      updatePredictivePrognosticsUI(pkt.prediction);
    }
  }

  // --- Knock Alert Trigger ---
  function triggerKnockAlert() {
    state.knockDetected = true;
    state.knockHoldFrames = 50; // ~850ms

    if (dom.knockAlertBox) {
      dom.knockAlertBox.style.display = 'flex';
    }
    if (dom.vibeBadge) {
      dom.vibeBadge.textContent = '💥 MECHANICAL SHOCK / KNOCK DETECTED!';
      dom.vibeBadge.style.color = '#ff3366';
      dom.vibeBadge.style.borderColor = 'rgba(255, 51, 102, 0.6)';
      dom.vibeBadge.style.background = 'rgba(255, 51, 102, 0.2)';
    }

    // Record peak
    if (state.piezoAmp > state.piezoPeakHold) {
      state.piezoPeakHold = Math.round(state.piezoAmp);
    }
  }

  // --- Radar Sound Target Blip Registry ---
  function registerRadarTarget(distanceCm, gradPct, isLeftHeavy) {
    // Spatial bearing: Left mic louder -> negative bearing angle (-30° to -75°)
    // Right mic louder -> positive bearing angle (+30° to +75°)
    const baseAngle = isLeftHeavy ? -Math.PI * 0.35 : Math.PI * 0.35;
    const jitter = (Math.random() - 0.5) * 0.2;
    const angle = baseAngle + jitter;

    // Dist ratio: 0cm = 0.05, 50cm = 0.50, 100cm = 1.0
    const distRatio = Math.max(0.1, Math.min(0.48, distanceCm / 100.0));

    state.radarTargets.push({
      angle: angle,
      distRatio: distRatio,
      intensity: 1.0,
      isNear: true,
      age: 0
    });

    if (state.radarTargets.length > 8) {
      state.radarTargets.shift();
    }
  }

  // --- Fallback Realistic Simulator ---
  // Ensures the dashboard is visually striking, live, and engaging even before
  // or between hardware hardware packet bursts.
  function runFallbackSimulator(time) {
    const t = time * 0.001;

    // Background engine idle purr
    const idleNoise1 = Math.sin(t * 14) * 80 + Math.sin(t * 31) * 45 + (Math.random() - 0.5) * 40;
    const idleNoise2 = Math.sin(t * 14 + 0.1) * 78 + Math.sin(t * 31 + 0.2) * 44 + (Math.random() - 0.5) * 40;

    // Periodic near-field acoustic events (e.g. rev test or tapping every 6s)
    const cycle = (t % 7.0);
    let simMic1 = 320 + idleNoise1;
    let simMic2 = 310 + idleNoise2;
    let simGrad = 4;
    let simPiezo = 18 + Math.sin(t * 18) * 6;
    let simDist = 110;

    if (cycle > 2.2 && cycle < 3.8) {
      // 50cm Near-field acoustic event trigger!
      const burst = Math.sin((cycle - 2.2) * Math.PI / 1.6);
      simMic1 += burst * 1800;
      simMic2 += burst * 1350; // Steep amplitude delta across 4cm baseline!
      simGrad = Math.round(25 + burst * 12);
      simDist = Math.max(15, Math.round(50 - burst * 32));

      state.isNear = true;
      state.nearHoldFrames = 30;
      if (Math.random() < 0.25) {
        registerRadarTarget(simDist, simGrad, true);
      }
    }

    if (cycle > 5.5 && cycle < 5.8) {
      // Periodic mechanical knock shock
      simPiezo += 280;
      triggerKnockAlert();
    }

    state.targetMic1 = Math.max(80, Math.round(simMic1));
    state.targetMic2 = Math.max(80, Math.round(simMic2));
    state.targetGrad = Math.max(2, Math.round(simGrad));
    state.targetPiezoAmp = Math.max(8, Math.round(simPiezo));
    state.targetDistance = simDist;
    state.piezoRaw = Math.round(state.piezoBaseline + (Math.random() - 0.5) * simPiezo);

    // Synthesize 32-Band Log-Mel Spectrum for fallback preview
    const simSpec = new Float32Array(32);
    for (let b = 0; b < 32; b++) {
      const baseFreq = Math.exp(-b / 9.0) * 0.65;
      const wobble = Math.sin(t * (7 + b) + b) * 0.12 + Math.random() * 0.08;
      const nearPeak = (state.isNear && b < 14) ? 0.28 : 0;
      simSpec[b] = Math.max(0.04, Math.min(0.98, baseFreq + wobble + nearPeak));
    }
    updateSpectrumData(simSpec);

    // Synthesize subtle continuous engine idle audio for in-browser ear monitor
    if (state.isAudioListening && state.audioCtx && state.audioCtx.state === 'running') {
      const pcmSim = new Float32Array(64);
      for (let i = 0; i < 64; i++) {
        const phi = (t * 16000 + i) * (2 * Math.PI / 16000);
        pcmSim[i] = (Math.sin(phi * 28) * 0.22 + Math.sin(phi * 56) * 0.14 + (Math.random() - 0.5) * 0.06) * 0.35;
      }
      queueLivePcmAudio(pcmSim);
    }

    // Synthesize Predictive Prognostics Horizon
    if (!state.prediction || time - state.lastPredTime > 600) {
      state.lastPredTime = time;
      const isKnock = state.targetPiezoAmp > 180;
      updatePredictivePrognosticsUI({
        is_healthy: !isKnock,
        health_state: isKnock ? "BAD" : "GOOD",
        problem_identified: isKnock ? "Connecting Rod / Piston Detonation Knock" : "NONE (NORMAL OPERATION)",
        predicted_class: isKnock ? "engine_knocking" : "normal_idle",
        predicted_label: isKnock ? "Connecting Rod / Piston Detonation Knock" : "Normal Engine Idle (Optimal Acoustics)",
        confidence: isKnock ? 78.5 : 94.8,
        probabilities: {
          normal_idle: isKnock ? 8.2 : 94.8,
          engine_knocking: isKnock ? 78.5 : 1.2,
          bearing_wear: isKnock ? 6.1 : 1.1,
          valve_ticking: isKnock ? 2.8 : 0.9,
          belt_slippage: isKnock ? 1.5 : 0.7,
          exhaust_leak: isKnock ? 1.2 : 0.5,
          misfire: isKnock ? 1.0 : 0.4,
          turbo_flutter: isKnock ? 0.7 : 0.4
        },
        prognosis: {
          rul_km: isKnock ? 1200 : 18500,
          rul_hours: isKnock ? 28 : 450,
          risk_level: isKnock ? "CRITICAL" : "NOMINAL",
          risk_color: isKnock ? "red" : "green",
          degradation_stage: isKnock ? "Stage 3 (Imminent Connecting Rod / Wrist Pin Damage)" : "Stage 0 (Nominal Operation)",
          health_score: isKnock ? 24.0 : 98.5,
          trend: isKnock ? "ACCELERATING WEAR" : "STABLE",
          prescriptive_action: isKnock 
            ? "Detonation knock detected above 350 ADC threshold. Retard ignition timing by 3 degrees and verify fuel octane."
            : "Vehicle acoustic profile optimal. Healthy baseline confirmed across all 32 Log-Mel bands. Routine oil service recommended at OEM interval."
        }
      });
    }
  }

  // --- Smooth Telemetry Interpolation ---
  function updateTelemetryState(dt, time) {
    // If no recent WebSocket packets, run lifelike simulator
    if (state.isSimulating || (performance.now() - state.lastPacketTime > 2500)) {
      state.isSimulating = true;
      runFallbackSimulator(time);
    }

    // Exponential smoothing for buttery visualizers
    const alpha = Math.min(1.0, dt * 14);
    state.mic1Peak += (state.targetMic1 - state.mic1Peak) * alpha;
    state.mic2Peak += (state.targetMic2 - state.mic2Peak) * alpha;
    state.gradPct += (state.targetGrad - state.gradPct) * alpha;
    state.piezoAmp += (state.targetPiezoAmp - state.piezoAmp) * alpha;
    state.distanceCm += (state.targetDistance - state.distanceCm) * alpha;

    // Decay peak hold
    state.piezoPeakHold = Math.max(state.piezoAmp, state.piezoPeakHold * 0.992);

    // Near-field trigger countdown
    if (state.nearHoldFrames > 0) {
      state.nearHoldFrames--;
      state.isNear = true;
    } else {
      state.isNear = false;
    }

    // Knock alert countdown
    if (state.knockHoldFrames > 0) {
      state.knockHoldFrames--;
    } else if (state.knockDetected) {
      state.knockDetected = false;
      if (dom.knockAlertBox) dom.knockAlertBox.style.display = 'none';
      if (dom.vibeBadge) {
        if (state.piezoAmp > 35) {
          dom.vibeBadge.textContent = '⚡ VIBRATION ACTIVE';
          dom.vibeBadge.style.color = '#ff9900';
          dom.vibeBadge.style.borderColor = 'rgba(255, 153, 0, 0.4)';
          dom.vibeBadge.style.background = 'rgba(255, 153, 0, 0.15)';
        } else {
          dom.vibeBadge.textContent = 'RESTING / NORMAL';
          dom.vibeBadge.style.color = 'var(--text-muted)';
          dom.vibeBadge.style.borderColor = 'rgba(255, 255, 255, 0.1)';
          dom.vibeBadge.style.background = 'rgba(255, 255, 255, 0.05)';
        }
      }
    }

    // Push into Seismograph rolling buffer
    const seismoVal = state.piezoRaw;
    state.seismoHistory[state.seismoIdx] = seismoVal;
    state.seismoIdx = (state.seismoIdx + 1) % state.seismoHistory.length;

    // Advance synthetic wave phase if hardware is not providing raw PCM
    state.wavePhase += dt * 28;
    const freq1 = 4.2;
    const freq2 = 8.5;
    const ampNormL = Math.min(1.0, state.mic1Peak / 2600);
    const ampNormR = Math.min(1.0, state.mic2Peak / 2600);
    const gradPhaseShift = (state.gradPct / 100) * 1.2;

    for (let i = 0; i < 128; i++) {
      const xNorm = i / 128.0;
      const angle = xNorm * Math.PI * 4 + state.wavePhase;
      // Mic 1 (Left Channel)
      const baseWaveL = Math.sin(angle * freq1) * 0.65 + Math.sin(angle * freq2) * 0.35;
      state.waveLeft[i] = baseWaveL * ampNormL;

      // Mic 2 (Right Channel) with physical 4cm spatial phase & energy gradient
      const baseWaveR = Math.sin((angle - gradPhaseShift) * freq1) * 0.65 + Math.sin((angle - gradPhaseShift) * freq2) * 0.35;
      state.waveRight[i] = baseWaveR * ampNormR;
    }

    // Advance Radar sweep
    state.radarAngle = (state.radarAngle + dt * 2.2) % (Math.PI * 2);

    // Age radar blips
    for (let i = state.radarTargets.length - 1; i >= 0; i--) {
      const blip = state.radarTargets[i];
      blip.age += dt;
      blip.intensity = Math.max(0, 1.0 - (blip.age / 1.8));
      if (blip.intensity <= 0) {
        state.radarTargets.splice(i, 1);
      }
    }

    // Update DOM telemetry badges & meters
    updateTelemetryDoms();
  }

  // --- Update Non-Canvas DOM Badges & Meters ---
  function updateTelemetryDoms() {
    const m1 = Math.round(state.mic1Peak);
    const m2 = Math.round(state.mic2Peak);
    const grad = Math.round(state.gradPct);

    if (dom.valMic1) dom.valMic1.textContent = m1.toLocaleString();
    if (dom.valMic2) dom.valMic2.textContent = m2.toLocaleString();
    if (dom.valGrad) dom.valGrad.textContent = `${grad}%`;

    // VU Bars (clamped 0% - 100%)
    if (dom.vuMic1) {
      const pct1 = Math.min(100, Math.round((m1 / 3200) * 100));
      dom.vuMic1.style.width = `${pct1}%`;
    }
    if (dom.vuMic2) {
      const pct2 = Math.min(100, Math.round((m2 / 3200) * 100));
      dom.vuMic2.style.width = `${pct2}%`;
    }

    // Seismograph chips
    if (dom.piezoBase) dom.piezoBase.textContent = state.piezoBaseline;
    if (dom.piezoAmp) dom.piezoAmp.textContent = Math.round(state.piezoAmp);
    if (dom.piezoPeak) dom.piezoPeak.textContent = Math.round(state.piezoPeakHold);

    // Perimeter Radar state box & threshold meter
    if (state.isNear) {
      if (dom.radarStateBox) {
        dom.radarStateBox.classList.add('pass');
        dom.radarStateBox.classList.remove('reject');
      }
      if (dom.gateBadge) {
        dom.gateBadge.textContent = 'TRIGGERED (<50cm)';
        dom.gateBadge.style.background = 'rgba(0, 255, 136, 0.2)';
        dom.gateBadge.style.color = '#00ff88';
      }
      if (dom.gateStateIcon) dom.gateStateIcon.textContent = '🎯';
      if (dom.gateStateTitle) dom.gateStateTitle.textContent = 'NEAR-FIELD SOURCE DETECTED';
      if (dom.gateStateDesc) dom.gateStateDesc.textContent = `4cm array gradient: ${grad}% | Source locked within 50cm`;
    } else {
      if (dom.radarStateBox) {
        dom.radarStateBox.classList.remove('pass', 'reject');
      }
      if (dom.gateBadge) {
        dom.gateBadge.textContent = 'ARMED';
        dom.gateBadge.style.background = '';
        dom.gateBadge.style.color = '';
      }
      if (dom.gateStateIcon) dom.gateStateIcon.textContent = '🛡️';
      if (dom.gateStateTitle) dom.gateStateTitle.textContent = 'PERIMETER GUARDED';
      if (dom.gateStateDesc) dom.gateStateDesc.textContent = 'Listening within 50cm barrier... Far-field plane waves rejected';
    }

    // 0cm to >100cm perimeter fill bar
    if (dom.perimeterFill) {
      // 0cm = 100%, 50cm = 50%, >100cm = 5%
      const fillPct = Math.max(5, Math.min(98, Math.round(100 - (state.distanceCm * 0.9))));
      dom.perimeterFill.style.width = `${fillPct}%`;
      if (state.isNear) {
        dom.perimeterFill.style.background = 'linear-gradient(90deg, #00ff88, #00f0ff)';
        dom.perimeterFill.style.boxShadow = '0 0 10px rgba(0, 255, 136, 0.5)';
      } else {
        dom.perimeterFill.style.background = 'linear-gradient(90deg, #3a86ff, #00f0ff)';
        dom.perimeterFill.style.boxShadow = 'none';
      }
    }
  }

  // --- Visualizer 1: Dual-Microphone Oscilloscope (#scopeCanvas) ---
  // Left: Cyan (#00f0ff), Right: Emerald (#00ff88)
  // Demonstrates the 4cm baseline acoustic gradient & spatial phase offset
  function renderOscilloscope() {
    if (!scopeCtx || !dom.scopeCanvas) return;
    const ctx = scopeCtx;
    const w = dom.scopeCanvas.width;
    const h = dom.scopeCanvas.height;
    const cy = h / 2;

    // Clear dark cockpit canvas
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#04060a';
    ctx.fillRect(0, 0, w, h);

    // Oscilloscope reticle grid
    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.08)';

    // Vertical time division lines
    const vSteps = 10;
    for (let i = 1; i < vSteps; i++) {
      const vx = (w / vSteps) * i;
      ctx.beginPath();
      ctx.setLineDash([2, 4]);
      ctx.moveTo(vx, 0);
      ctx.lineTo(vx, h);
      ctx.stroke();
    }

    // Horizontal amplitude division lines
    const hDivs = [0.18, 0.35, 0.65, 0.82];
    for (let i = 0; i < hDivs.length; i++) {
      const hy = h * hDivs[i];
      ctx.beginPath();
      ctx.setLineDash([2, 4]);
      ctx.moveTo(0, hy);
      ctx.lineTo(w, hy);
      ctx.stroke();
    }

    // Center zero-voltage axis
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.28)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, cy);
    ctx.lineTo(w, cy);
    ctx.stroke();
    ctx.restore();

    const maxAmpPx = (h / 2) * 0.85;
    const len = state.waveLeft.length;

    // 4cm Acoustic Gradient Shaded Delta Area
    // Highlights the spatial difference between Left and Right microphone wavefronts
    if (state.gradPct > 8) {
      ctx.save();
      ctx.beginPath();
      for (let i = 0; i < len; i++) {
        const x = (w / (len - 1)) * i;
        const yL = cy - state.waveLeft[i] * maxAmpPx;
        if (i === 0) ctx.moveTo(x, yL);
        else ctx.lineTo(x, yL);
      }
      for (let i = len - 1; i >= 0; i--) {
        const x = (w / (len - 1)) * i;
        const yR = cy - state.waveRight[i] * maxAmpPx;
        ctx.lineTo(x, yR);
      }
      ctx.closePath();
      ctx.fillStyle = 'rgba(255, 214, 0, 0.12)';
      ctx.fill();
      ctx.restore();
    }

    // Left Channel (Mic 1 - Cyan #00f0ff)
    ctx.save();
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 2.2;
    ctx.shadowColor = '#00f0ff';
    ctx.shadowBlur = 10;
    ctx.beginPath();
    for (let i = 0; i < len; i++) {
      const x = (w / (len - 1)) * i;
      const y = cy - state.waveLeft[i] * maxAmpPx;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();

    // Right Channel (Mic 2 - Emerald Green #00ff88)
    ctx.save();
    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 2.2;
    ctx.shadowColor = '#00ff88';
    ctx.shadowBlur = 10;
    ctx.beginPath();
    for (let i = 0; i < len; i++) {
      const x = (w / (len - 1)) * i;
      const y = cy - state.waveRight[i] * maxAmpPx;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();

    // Corner Watermark Tags & Acoustic Specs
    ctx.save();
    ctx.font = '600 10px "JetBrains Mono", monospace';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.fillText('16 kHz STEREO I2S • 40mm PHYSICAL SEPARATION', 14, 20);

    ctx.fillStyle = '#00f0ff';
    ctx.fillText('MIC 1 (L)', 14, h - 14);

    ctx.fillStyle = '#00ff88';
    ctx.fillText('MIC 2 (R)', 84, h - 14);

    ctx.fillStyle = '#ffd600';
    ctx.fillText(`Δ GRADIENT: ${Math.round(state.gradPct)}%`, w - 150, h - 14);
    ctx.restore();
  }

  // --- Visualizer 2: 50cm Acoustic Perimeter Radar (#radarCanvas) ---
  // Circular sweeping radar with 50cm barrier, spatial blips, & lock animation
  function renderRadar() {
    if (!radarCtx || !dom.radarCanvas) return;
    const ctx = radarCtx;
    const w = dom.radarCanvas.width;
    const h = dom.radarCanvas.height;
    const cx = w / 2;
    const cy = h / 2 - 8;
    const maxR = Math.min(cx, cy) - 14;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#04060a';
    ctx.fillRect(0, 0, w, h);

    // Crosshairs
    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.beginPath();
    ctx.moveTo(cx - maxR, cy);
    ctx.lineTo(cx + maxR, cy);
    ctx.moveTo(cx, cy - maxR);
    ctx.lineTo(cx, cy + maxR);
    ctx.stroke();

    // 45 degree diagonals
    const diag = maxR * 0.7071;
    ctx.setLineDash([2, 4]);
    ctx.beginPath();
    ctx.moveTo(cx - diag, cy - diag);
    ctx.lineTo(cx + diag, cy + diag);
    ctx.moveTo(cx - diag, cy + diag);
    ctx.lineTo(cx + diag, cy - diag);
    ctx.stroke();
    ctx.restore();

    // Concentric Range Rings: 25cm, 50cm (Barrier), 75cm, 100cm
    const rings = [
      { r: maxR * 0.25, label: "25cm", highlight: false },
      { r: maxR * 0.50, label: "50cm BARRIER", highlight: true },
      { r: maxR * 0.75, label: "75cm", highlight: false },
      { r: maxR * 1.00, label: "100cm", highlight: false }
    ];

    for (let i = 0; i < rings.length; i++) {
      const ring = rings[i];
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, ring.r, 0, Math.PI * 2);

      if (ring.highlight) {
        // 50cm Barrier Ring: Glowing Cyan / Green boundary
        if (state.isNear) {
          ctx.strokeStyle = '#00ff88';
          ctx.shadowColor = '#00ff88';
          ctx.shadowBlur = 12;
          ctx.lineWidth = 2.2;
        } else {
          ctx.strokeStyle = '#00f0ff';
          ctx.shadowColor = '#00f0ff';
          ctx.shadowBlur = 6;
          ctx.lineWidth = 1.6;
        }
        ctx.setLineDash([4, 3]);
        ctx.stroke();

        // Label on the 50cm circle
        ctx.font = '700 9px "JetBrains Mono", monospace';
        ctx.fillStyle = state.isNear ? '#00ff88' : '#00f0ff';
        ctx.fillText(ring.label, cx + 6, cy - ring.r + 11);
      } else {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.setLineDash([2, 4]);
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.font = '500 8px "JetBrains Mono", monospace';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.25)';
        ctx.fillText(ring.label, cx + 4, cy - ring.r + 9);
      }
      ctx.restore();
    }

    // Rotating Radar Sweep Cone & Beam
    ctx.save();
    const sweepAngle = state.radarAngle;
    const sweepTrail = Math.PI * 0.35; // Trail width

    // Sweeping gradient cone
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxR);
    grad.addColorStop(0, 'rgba(0, 240, 255, 0.02)');
    grad.addColorStop(0.5, 'rgba(0, 240, 255, 0.10)');
    grad.addColorStop(1, 'rgba(0, 240, 255, 0.22)');

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, maxR, sweepAngle - sweepTrail, sweepAngle);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Bright leading sweep line
    ctx.strokeStyle = state.isNear ? '#00ff88' : '#00f0ff';
    ctx.shadowColor = state.isNear ? '#00ff88' : '#00f0ff';
    ctx.shadowBlur = 10;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(sweepAngle) * maxR, cy + Math.sin(sweepAngle) * maxR);
    ctx.stroke();
    ctx.restore();

    // Render Sound Source Blips with Decay & Expanding Rings
    for (let i = 0; i < state.radarTargets.length; i++) {
      const blip = state.radarTargets[i];
      const bx = cx + Math.cos(blip.angle) * (blip.distRatio * maxR);
      const by = cy + Math.sin(blip.angle) * (blip.distRatio * maxR);
      const alpha = blip.intensity;

      ctx.save();
      // Blip core
      ctx.beginPath();
      ctx.arc(bx, by, 4.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0, 255, 136, ${alpha})`;
      ctx.shadowColor = '#00ff88';
      ctx.shadowBlur = 14;
      ctx.fill();

      // Expanding radar ripple ring
      const rippleR = 5 + blip.age * 24;
      ctx.beginPath();
      ctx.arc(bx, by, rippleR, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(0, 255, 136, ${alpha * 0.6})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Lock label
      ctx.font = '700 8px "JetBrains Mono", monospace';
      ctx.fillStyle = `rgba(0, 255, 136, ${alpha})`;
      ctx.fillText(`<50cm LOCK`, bx + 8, by + 3);
      ctx.restore();
    }

    // Near-field perimeter active border flash
    if (state.isNear) {
      ctx.save();
      ctx.strokeStyle = 'rgba(0, 255, 136, 0.4)';
      ctx.lineWidth = 2;
      ctx.strokeRect(4, 4, w - 8, h - 8);
      ctx.restore();
    }
  }

  // --- Visualizer 3: Piezo Mechanical Vibration Seismograph (#seismoCanvas) ---
  // Rolling time-series chart with knock shock alert popup
  function renderSeismograph() {
    if (!seismoCtx || !dom.seismoCanvas) return;
    const ctx = seismoCtx;
    const w = dom.seismoCanvas.width;
    const h = dom.seismoCanvas.height;
    const cy = h / 2;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#04060a';
    ctx.fillRect(0, 0, w, h);

    // Seismograph Grid Lines
    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(191, 85, 236, 0.08)';

    // Vertical timing marks
    const vSteps = 12;
    for (let i = 1; i < vSteps; i++) {
      const vx = (w / vSteps) * i;
      ctx.beginPath();
      ctx.setLineDash([2, 4]);
      ctx.moveTo(vx, 0);
      ctx.lineTo(vx, h);
      ctx.stroke();
    }

    // Horizontal baseline & knock shock threshold guides (±180 ADC units)
    const base = state.piezoBaseline;
    const scale = (h / 2) / 450.0; // Scaled so ±400 ADC units fill vertical height

    // Upper & Lower Knock Shock Alert Thresholds
    const upperY = cy - 180 * scale;
    const lowerY = cy + 180 * scale;

    ctx.strokeStyle = 'rgba(255, 51, 102, 0.3)';
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(0, upperY);
    ctx.lineTo(w, upperY);
    ctx.moveTo(0, lowerY);
    ctx.lineTo(w, lowerY);
    ctx.stroke();

    // Resting Baseline Zero Line
    ctx.strokeStyle = 'rgba(191, 85, 236, 0.25)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, cy);
    ctx.lineTo(w, cy);
    ctx.stroke();
    ctx.restore();

    // Plot Rolling Seismograph Waveform Buffer
    const history = state.seismoHistory;
    const len = history.length;
    const startIdx = state.seismoIdx;

    // Gradient area fill underneath vibration wave
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(0, cy);

    for (let i = 0; i < len; i++) {
      const bufIdx = (startIdx + i) % len;
      const rawVal = history[bufIdx];
      const delta = rawVal - base;
      const x = (w / (len - 1)) * i;
      const y = cy - delta * scale;
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, cy);
    ctx.closePath();

    const areaGrad = ctx.createLinearGradient(0, cy - 80, 0, cy + 80);
    areaGrad.addColorStop(0, 'rgba(191, 85, 236, 0.25)');
    areaGrad.addColorStop(0.5, 'rgba(191, 85, 236, 0.05)');
    areaGrad.addColorStop(1, 'rgba(191, 85, 236, 0.25)');
    ctx.fillStyle = areaGrad;
    ctx.fill();
    ctx.restore();

    // Vivid Purple Vibration Curve
    ctx.save();
    ctx.strokeStyle = state.knockDetected ? '#ff3366' : '#bf55ec';
    ctx.shadowColor = state.knockDetected ? '#ff3366' : '#bf55ec';
    ctx.shadowBlur = state.knockDetected ? 16 : 8;
    ctx.lineWidth = state.knockDetected ? 2.6 : 1.8;
    ctx.beginPath();

    for (let i = 0; i < len; i++) {
      const bufIdx = (startIdx + i) % len;
      const rawVal = history[bufIdx];
      const delta = rawVal - base;
      const x = (w / (len - 1)) * i;
      const y = cy - delta * scale;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();

    // Knock Shock Impact Spike Marker
    if (state.knockDetected) {
      ctx.save();
      const lastX = w - 10;
      const lastDelta = history[(startIdx + len - 1) % len] - base;
      const lastY = cy - lastDelta * scale;

      ctx.beginPath();
      ctx.arc(lastX, lastY, 7, 0, Math.PI * 2);
      ctx.fillStyle = '#ff3366';
      ctx.shadowColor = '#ff3366';
      ctx.shadowBlur = 20;
      ctx.fill();

      // Radiating shock ring
      ctx.beginPath();
      ctx.arc(lastX, lastY, 14, 0, Math.PI * 2);
      ctx.strokeStyle = '#ffd600';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.restore();
    }

    // Seismograph Legend & Threshold Annotation
    ctx.save();
    ctx.font = '600 9px "JetBrains Mono", monospace';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.35)';
    ctx.fillText('PIEZOELECTRIC SENSOR (GPIO 1 ADC1) • 12-BIT ROLLING TIME-SERIES', 12, 18);

    ctx.fillStyle = 'rgba(255, 51, 102, 0.6)';
    ctx.fillText('+180 ADC SHOCK THRESHOLD', w - 165, upperY - 4);
    ctx.restore();
  }

  // --- Main 60 FPS Render Loop ---
  let lastFrameTime = performance.now();

  function renderLoop(now) {
    const dt = Math.min(0.1, (now - lastFrameTime) * 0.001);
    lastFrameTime = now;

    // Update Telemetry Data Model
    updateTelemetryState(dt, now);

    // Render Canvas Visualizers
    renderOscilloscope();
    renderRadar();
    renderSeismograph();
    renderSpectrumCanvas();

    // Calculate Dynamic FPS
    state.frameCount++;
    if (now - state.lastFpsUpdate >= 500) {
      const elapsed = (now - state.lastFpsUpdate) * 0.001;
      state.fps = Math.round(state.frameCount / elapsed);
      state.frameCount = 0;
      state.lastFpsUpdate = now;
      if (dom.fpsBadge) {
        dom.fpsBadge.textContent = `${state.fps} FPS`;
      }
    }

    requestAnimationFrame(renderLoop);
  }

  // --- Visualizer 4: 32-Band Mel Frequency Spectrum Canvas (#spectrumCanvas) ---
  function updateSpectrumData(bands32) {
    if (!bands32 || bands32.length === 0) return;
    const len = Math.min(32, bands32.length);
    for (let i = 0; i < len; i++) {
      const v = Math.max(0.02, Math.min(1.0, bands32[i]));
      // Fast attack, smooth decay
      if (v > state.spectrum32[i]) {
        state.spectrum32[i] = v;
      } else {
        state.spectrum32[i] = state.spectrum32[i] * 0.92 + v * 0.08;
      }

      // Peak hold indicator with gravity
      if (state.spectrum32[i] > state.spectrumPeaks[i]) {
        state.spectrumPeaks[i] = state.spectrum32[i];
      } else {
        state.spectrumPeaks[i] = Math.max(0.04, state.spectrumPeaks[i] - 0.015);
      }
    }
  }

  function renderSpectrumCanvas() {
    if (!spectrumCtx || !dom.spectrumCanvas) return;
    const ctx = spectrumCtx;
    const w = dom.spectrumCanvas.width;
    const h = dom.spectrumCanvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#04060a';
    ctx.fillRect(0, 0, w, h);

    // Subtle Grid Guides
    ctx.save();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let y = 20; y < h; y += 30) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
    ctx.restore();

    const numBars = 32;
    const padding = 2;
    const totalPadding = padding * (numBars + 1);
    const barWidth = Math.max(2, (w - totalPadding) / numBars);

    for (let i = 0; i < numBars; i++) {
      const x = padding + i * (barWidth + padding);
      const val = state.spectrum32[i] || 0.04;
      const barH = Math.max(4, val * (h - 16));
      const y = h - barH - 4;

      // Equalizer Bar Gradient
      const grad = ctx.createLinearGradient(0, h, 0, y);
      if (val > 0.75) {
        grad.addColorStop(0, '#00f0ff');
        grad.addColorStop(0.6, '#ffd600');
        grad.addColorStop(1, '#ff3366');
      } else if (val > 0.45) {
        grad.addColorStop(0, '#00f0ff');
        grad.addColorStop(0.8, '#00ff88');
        grad.addColorStop(1, '#ffd600');
      } else {
        grad.addColorStop(0, 'rgba(0, 240, 255, 0.6)');
        grad.addColorStop(1, '#00f0ff');
      }

      ctx.save();
      ctx.fillStyle = grad;
      ctx.shadowColor = '#00f0ff';
      ctx.shadowBlur = val > 0.6 ? 8 : 3;
      ctx.fillRect(x, y, barWidth, barH);
      ctx.restore();

      // Peak Hold Cap Line
      const peakVal = state.spectrumPeaks[i] || 0.04;
      const peakY = Math.max(2, h - peakVal * (h - 16) - 6);
      ctx.save();
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(x, peakY, barWidth, 2);
      ctx.restore();
    }
  }

  // --- Feature 4: Live Acoustic Ear Monitor & Web Audio API (Zero Storage) ---
  function initLiveAudioListening() {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      console.warn('[MotoPulse Ear] Web Audio API is not supported in this browser.');
      return;
    }

    function setupAudio() {
      if (!state.audioCtx) {
        try {
          state.audioCtx = new AudioContextClass({ sampleRate: 16000 });
        } catch (e) {
          state.audioCtx = new AudioContextClass();
        }
        state.audioGain = state.audioCtx.createGain();
        state.audioGain.gain.setValueAtTime(state.audioVolume, state.audioCtx.currentTime);
        state.audioGain.connect(state.audioCtx.destination);
      }
      if (state.audioCtx && state.audioCtx.state === 'suspended') {
        state.audioCtx.resume().catch(() => {});
      }
    }

    // Auto-attempt resume on dashboard launch
    setupAudio();

    // Browser policy unlock: auto-unsuspend upon user's first natural gesture
    const unlockEvents = ['pointerdown', 'click', 'keydown', 'touchstart'];
    function unlockHandler() {
      setupAudio();
      if (state.audioCtx && state.audioCtx.state === 'running') {
        unlockEvents.forEach(evt => window.removeEventListener(evt, unlockHandler));
      }
    }
    unlockEvents.forEach(evt => window.addEventListener(evt, unlockHandler, { passive: true }));

    // Listen / Mute Toggle Button
    if (dom.btnEarListen) {
      dom.btnEarListen.addEventListener('click', function () {
        setupAudio();
        state.isAudioListening = !state.isAudioListening;
        updateEarButtonState();
      });
    }

    // Volume Slider
    if (dom.earVolume) {
      dom.earVolume.addEventListener('input', function () {
        state.audioVolume = parseFloat(this.value) / 100.0;
        if (dom.volPct) dom.volPct.textContent = `${Math.round(state.audioVolume * 100)}%`;
        if (state.audioGain && state.audioCtx) {
          state.audioGain.gain.setValueAtTime(state.isAudioListening ? state.audioVolume : 0, state.audioCtx.currentTime);
        }
      });
    }

    updateEarButtonState();
  }

  function updateEarButtonState() {
    if (!dom.btnEarListen) return;
    if (state.isAudioListening) {
      dom.btnEarListen.classList.remove('muted');
      if (dom.earIcon) dom.earIcon.textContent = '🔊';
      if (dom.earListenText) dom.earListenText.textContent = 'Listening to Vehicle Audio';
      if (state.audioGain && state.audioCtx) {
        state.audioGain.gain.setValueAtTime(state.audioVolume, state.audioCtx.currentTime);
      }
    } else {
      dom.btnEarListen.classList.add('muted');
      if (dom.earIcon) dom.earIcon.textContent = '🔇';
      if (dom.earListenText) dom.earListenText.textContent = 'Sound Muted (Click to Listen)';
      if (state.audioGain && state.audioCtx) {
        state.audioGain.gain.setValueAtTime(0, state.audioCtx.currentTime);
      }
    }
  }

  function queueLivePcmAudio(pcmSamples) {
    if (!state.isAudioListening || !state.audioCtx || state.audioCtx.state !== 'running') return;
    if (!pcmSamples || pcmSamples.length === 0) return;

    const sr = state.audioCtx.sampleRate || 16000;
    const len = pcmSamples.length;
    let peak = 0.0001;

    const buffer = state.audioCtx.createBuffer(1, len, sr);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < len; i++) {
      let s = pcmSamples[i];
      if (Math.abs(s) > 1.0) s = s / 32768.0;
      s = Math.max(-1.0, Math.min(1.0, s));
      data[i] = s;
      const absS = Math.abs(s);
      if (absS > peak) peak = absS;
    }

    // Dynamic dBFS calculation
    const curDb = 20 * Math.log10(peak);
    state.audioDbDecay = Math.max(curDb, state.audioDbDecay - 1.2);
    if (dom.earDbLevel) {
      dom.earDbLevel.textContent = `Live Peak: ${state.audioDbDecay.toFixed(1)} dBFS`;
    }

    const now = state.audioCtx.currentTime;
    if (state.audioNextTime < now) {
      state.audioNextTime = now + 0.015;
    }

    const source = state.audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(state.audioGain);
    source.start(state.audioNextTime);
    state.audioNextTime += buffer.duration;

    // Boundary check to prevent queue runaway
    if (state.audioNextTime > now + 0.3) {
      state.audioNextTime = now + 0.05;
    }
  }

  // --- Feature: Live Browser Microphone Auto-Listening (Zero Storage Ephemeral Stream) ---
  function initBrowserMicrophoneCapture() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      console.warn('[MotoPulse Mic] Browser MediaDevices getUserMedia not supported.');
      return;
    }

    let isMicActive = false;
    let micCtx = null;
    let micSource = null;
    let micProcessor = null;
    let lastSendTime = 0;

    async function startMicCapture() {
      if (isMicActive) return;
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false
          }
        });

        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        micCtx = new AudioContextClass();
        if (micCtx.state === 'suspended') {
          await micCtx.resume();
        }

        const nativeSr = micCtx.sampleRate;
        micSource = micCtx.createMediaStreamSource(stream);
        // 4096 samples at 48kHz is ~85ms; at 16kHz is ~256ms
        micProcessor = micCtx.createScriptProcessor(4096, 1, 1);

        micProcessor.onaudioprocess = function (e) {
          const input = e.inputBuffer.getChannelData(0);

          // Downsample to 16,000 Hz if needed
          let pcm16k;
          if (nativeSr === 16000) {
            pcm16k = Array.from(input);
          } else {
            const ratio = nativeSr / 16000.0;
            const newLen = Math.floor(input.length / ratio);
            pcm16k = new Float32Array(newLen);
            for (let i = 0; i < newLen; i++) {
              const srcIdx = Math.floor(i * ratio);
              pcm16k[i] = input[srcIdx] || 0.0;
            }
          }

          // Compute peak dBFS
          let peak = 0.0001;
          for (let i = 0; i < input.length; i++) {
            const a = Math.abs(input[i]);
            if (a > peak) peak = a;
          }
          const db = 20 * Math.log10(peak);
          if (dom.earDbLevel) {
            dom.earDbLevel.textContent = `Live Mic: ${db.toFixed(1)} dBFS`;
          }

          // Throttle sending to ~100ms intervals
          const now = performance.now();
          if (now - lastSendTime >= 95) {
            lastSendTime = now;
            const pcmArray = Array.from(pcm16k);
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
              state.ws.send(JSON.stringify({
                type: "audio_pcm",
                pcm: pcmArray
              }));
            }
          }
        };

        const muteNode = micCtx.createGain();
        muteNode.gain.value = 0.0;
        micSource.connect(micProcessor);
        micProcessor.connect(muteNode);
        muteNode.connect(micCtx.destination);
        isMicActive = true;
        console.log('[MotoPulse Mic] 🎙️ Live vehicle audio capture active via browser microphone!');

        const micPill = document.getElementById('pill-mic');
        const micStatus = document.getElementById('mic-status');
        if (micPill) micPill.classList.add('active');
        if (micStatus) micStatus.textContent = 'LISTENING';
      } catch (err) {
        console.warn('[MotoPulse Mic] Microphone permission not granted:', err);
        const micStatus = document.getElementById('mic-status');
        if (micStatus) micStatus.textContent = 'CLICK TO ENABLE';
      }
    }

    // Auto-attempt start on first user interaction on dashboard
    const unlockEvents = ['click', 'pointerdown', 'keydown', 'touchstart'];
    function onGesture() {
      startMicCapture();
      unlockEvents.forEach(evt => window.removeEventListener(evt, onGesture));
    }
    unlockEvents.forEach(evt => window.addEventListener(evt, onGesture, { passive: true }));

    // Also trigger on listen button
    if (dom.btnEarListen) {
      dom.btnEarListen.addEventListener('click', function () {
        startMicCapture();
      });
    }

    const micPill = document.getElementById('pill-mic');
    if (micPill) {
      micPill.style.cursor = 'pointer';
      micPill.addEventListener('click', function () {
        startMicCapture();
      });
    }
  }

  // --- Feature 5: AI Predictive Prognostics Horizon Engine ---
  function initPredictivePrognostics() {
    if (!dom.probDistribution) return;
    dom.probDistribution.innerHTML = '';

    CORE9_CLASSES.forEach(item => {
      const row = document.createElement('div');
      row.className = 'prob-row';
      row.id = `prob-row-${item.key}`;
      row.innerHTML = `
        <div class="prob-header">
          <span class="prob-label">
            <span>${item.icon}</span>
            <span>${item.label}</span>
          </span>
          <span class="prob-pct" id="prob-pct-${item.key}">0.0%</span>
        </div>
        <div class="prob-track">
          <div class="prob-bar ${item.color}" id="prob-bar-${item.key}" style="width: 5%;"></div>
        </div>
      `;
      dom.probDistribution.appendChild(row);
    });
  }

  function updatePredictivePrognosticsUI(pred) {
    if (!pred) return;
    const prog = pred.prognosis || {};
    const probs = pred.probabilities || {};

    // 0. Vehicle Acoustic Health State (GOOD vs BAD) & Problem Identification
    const isHealthy = pred.is_healthy !== undefined ? Boolean(pred.is_healthy) : (pred.predicted_class === 'normal_idle');
    const healthState = pred.health_state || (isHealthy ? 'GOOD' : 'BAD');
    const problemIdentified = pred.problem_identified || (isHealthy ? 'NONE (NORMAL OPERATION)' : (pred.predicted_label || 'MECHANICAL DEFECT'));

    if (dom.predHealthBadge) {
      dom.predHealthBadge.textContent = `HEALTH: ${healthState}`;
      dom.predHealthBadge.className = `badge ${isHealthy ? 'green' : 'red'}`;
    }

    if (dom.healthHeroBanner) {
      if (isHealthy) {
        dom.healthHeroBanner.className = 'health-hero-banner healthy';
        if (dom.healthHeroIcon) dom.healthHeroIcon.textContent = '🟢';
        if (dom.healthHeroBadge) dom.healthHeroBadge.textContent = 'VEHICLE ACOUSTIC STATE: GOOD';
        if (dom.healthHeroTitle) dom.healthHeroTitle.textContent = 'Healthy Engine Sound Detected (Normal Baseline)';
        if (dom.healthHeroSub) dom.healthHeroSub.textContent = 'Acoustic spectrum matches calibrated OEM vehicle idle and operating profile without mechanical anomalies.';
        if (dom.problemCard) dom.problemCard.className = 'problem-card healthy';
        if (dom.problemTitle) dom.problemTitle.textContent = 'NONE (NORMAL OPERATION)';
        if (dom.problemSub) dom.problemSub.textContent = 'All cylinder acoustics, lifters, belts, and bearing frequencies within nominal range.';
      } else {
        dom.healthHeroBanner.className = 'health-hero-banner defect';
        if (dom.healthHeroIcon) dom.healthHeroIcon.textContent = '🔴';
        if (dom.healthHeroBadge) dom.healthHeroBadge.textContent = 'VEHICLE ACOUSTIC STATE: BAD';
        if (dom.healthHeroTitle) dom.healthHeroTitle.textContent = `Defect Detected: ${pred.predicted_label || 'Mechanical Anomaly'}`;
        const confStr = pred.confidence !== undefined ? `${pred.confidence}%` : 'high';
        if (dom.healthHeroSub) dom.healthHeroSub.textContent = `Characteristic acoustic defect signature recognized with ${confStr} confidence.`;
        if (dom.problemCard) dom.problemCard.className = 'problem-card defect';
        if (dom.problemTitle) dom.problemTitle.textContent = problemIdentified;
        if (dom.problemSub) dom.problemSub.textContent = prog.prescriptive_action || 'Immediate workshop inspection advised.';
      }
    }

    // 1. RUL Forecasts
    if (dom.rulKm) {
      const km = prog.rul_km ?? 18500;
      dom.rulKm.textContent = `${Number(km).toLocaleString()} km`;
    }
    if (dom.rulHours) {
      const hrs = prog.rul_hours ?? 450;
      dom.rulHours.textContent = `${Number(hrs).toLocaleString()} hrs`;
    }

    // 2. Health Score
    if (dom.healthScore) {
      const score = Number(prog.health_score ?? 98.5);
      dom.healthScore.textContent = `${score.toFixed(1)}%`;
      dom.healthScore.className = 'rul-val ' + (score >= 80 ? 'green' : (score >= 45 ? 'orange' : 'red'));
    }

    // 3. Risk Badge
    if (dom.predRiskBadge) {
      const risk = (prog.risk_level || 'NOMINAL').toUpperCase();
      dom.predRiskBadge.textContent = `STATUS: ${risk}`;
      dom.predRiskBadge.className = 'badge ' + (prog.risk_color || 'green');
    }

    // 4. Degradation Stage Stepper
    if (dom.progStageName) {
      dom.progStageName.textContent = prog.degradation_stage || 'Stage 0 (Nominal Operation)';
    }

    const stageStr = (prog.degradation_stage || '').toLowerCase();
    let activeStageIdx = 0;
    if (stageStr.includes('stage 3')) activeStageIdx = 3;
    else if (stageStr.includes('stage 2')) activeStageIdx = 2;
    else if (stageStr.includes('stage 1')) activeStageIdx = 1;

    if (dom.stageSteps) {
      dom.stageSteps.forEach((step, idx) => {
        if (!step) return;
        if (idx === activeStageIdx) {
          step.classList.add('active');
          if (idx >= 2) step.classList.add('danger');
          else step.classList.remove('danger');
        } else {
          step.classList.remove('active', 'danger');
        }
      });
    }

    // 5. Prescriptive Maintenance Advisory
    if (dom.rxTrend) {
      dom.rxTrend.textContent = `TREND: ${prog.trend || 'STABLE'}`;
      dom.rxTrend.style.color = (prog.trend === 'STABLE') ? 'var(--green)' : 'var(--orange)';
    }
    if (dom.rxBody && prog.prescriptive_action) {
      dom.rxBody.textContent = prog.prescriptive_action;
    }

    // 6. Primary Diagnosis
    if (dom.primaryDiagnosis) {
      const primaryLbl = pred.predicted_label || 'Normal Engine Idle';
      const conf = pred.confidence ?? 94.6;
      dom.primaryDiagnosis.textContent = `${primaryLbl} (${conf}%)`;
    }

    // 7. 9-Class Probability Distribution Bars (with EMA Damping to prevent flickering)
    const topClass = pred.predicted_class || 'normal_idle';
    CORE9_CLASSES.forEach(item => {
      const targetPct = Number(probs[item.key] ?? 1.0);
      const prevPct = state.smoothedProbs[item.key] ?? targetPct;
      // Exponential moving average: instant update if locked, smooth damping if streaming
      const smoothPct = (state.diagState === 'LOCKED') ? targetPct : (prevPct * 0.72 + targetPct * 0.28);
      state.smoothedProbs[item.key] = smoothPct;

      const pctEl = document.getElementById(`prob-pct-${item.key}`);
      const barEl = document.getElementById(`prob-bar-${item.key}`);
      const rowEl = document.getElementById(`prob-row-${item.key}`);

      if (pctEl) pctEl.textContent = `${smoothPct.toFixed(1)}%`;
      if (barEl) barEl.style.width = `${Math.min(100, Math.max(3, smoothPct))}%`;

      if (rowEl) {
        if (item.key === topClass) {
          rowEl.classList.add('active-pred');
        } else {
          rowEl.classList.remove('active-pred');
        }
      }
    });
  }

  // --- Acoustic Diagnostic Window Controls (5s - 15s Fixed Prediction Lock) ---
  function initDiagnosticSessionControls() {
    const durBtns = [dom.btnDiag5s, dom.btnDiag10s, dom.btnDiag15s];
    durBtns.forEach(btn => {
      if (!btn) return;
      btn.addEventListener('click', function () {
        durBtns.forEach(b => b && b.classList.remove('active'));
        this.classList.add('active');
        state.diagDuration = parseInt(this.dataset.sec || "10", 10);
        if (dom.btnDiagText && state.diagState !== 'EVALUATING') {
          dom.btnDiagText.textContent = `Start ${state.diagDuration}s Diagnostic Scan`;
        }
      });
    });

    if (dom.btnStartDiag) {
      dom.btnStartDiag.addEventListener('click', function () {
        fetch('/api/diagnostics/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ duration: state.diagDuration })
        }).then(r => r.json()).then(diag => {
          updateDiagnosticSessionUI(diag);
        }).catch(err => console.error(err));
      });
    }

    if (dom.btnResetDiag) {
      dom.btnResetDiag.addEventListener('click', function () {
        fetch('/api/diagnostics/reset', { method: 'POST' })
          .then(r => r.json()).then(diag => {
            updateDiagnosticSessionUI(diag);
          }).catch(err => console.error(err));
      });
    }
  }

  function updateDiagnosticSessionUI(diag) {
    if (!diag) return;
    state.diagState = diag.state;

    if (dom.diagFill) {
      dom.diagFill.style.width = `${Math.min(100, Math.max(0, diag.progress_percent || 0))}%`;
    }

    if (diag.state === 'EVALUATING') {
      if (dom.diagTimerStatus) dom.diagTimerStatus.textContent = `Profiling Acoustic Harmonics (${(diag.elapsed_seconds || 0).toFixed(1)}s)...`;
      if (dom.diagTimerCountdown) dom.diagTimerCountdown.textContent = `${(diag.elapsed_seconds || 0).toFixed(1)}s / ${(diag.target_duration || 10).toFixed(1)}s`;
      if (dom.btnStartDiag) dom.btnStartDiag.classList.add('evaluating');
      if (dom.btnDiagText) dom.btnDiagText.textContent = `Analyzing Sound... (${Math.round(diag.progress_percent || 0)}%)`;
      if (dom.btnDiagIcon) dom.btnDiagIcon.textContent = '⏳';
      if (dom.diagLockBadge) {
        dom.diagLockBadge.className = 'diag-lock-badge';
        if (dom.lockIcon) dom.lockIcon.textContent = '⏱️';
        if (dom.lockText) dom.lockText.textContent = 'ANALYZING...';
      }
    } else if (diag.state === 'LOCKED') {
      const fixed = diag.fixed_diagnosis || {};
      const stab = diag.stability_index || 98.0;
      const isHealthy = Boolean(fixed.is_healthy);

      if (dom.diagTimerStatus) dom.diagTimerStatus.textContent = `Fixed Diagnosis Locked (${stab.toFixed(1)}% Stable)`;
      if (dom.diagTimerCountdown) dom.diagTimerCountdown.textContent = `Done (${(diag.target_duration || 10).toFixed(0)}s Scan Completed)`;
      if (dom.btnStartDiag) dom.btnStartDiag.classList.remove('evaluating');
      if (dom.btnDiagText) dom.btnDiagText.textContent = 'Start New Diagnostic Scan';
      if (dom.btnDiagIcon) dom.btnDiagIcon.textContent = '🔄';
      if (dom.diagLockBadge) {
        dom.diagLockBadge.className = `diag-lock-badge locked ${isHealthy ? '' : 'defect'}`;
        if (dom.lockIcon) dom.lockIcon.textContent = '🔒';
        if (dom.lockText) dom.lockText.textContent = `FIXED LOCKED (${stab.toFixed(0)}%)`;
      }
    } else {
      // STREAMING
      if (dom.diagTimerStatus) dom.diagTimerStatus.textContent = 'Continuous Real-Time Stream';
      if (dom.diagTimerCountdown) dom.diagTimerCountdown.textContent = `--.-s / ${(state.diagDuration || 10).toFixed(0)}s`;
      if (dom.btnStartDiag) dom.btnStartDiag.classList.remove('evaluating');
      if (dom.btnDiagText) dom.btnDiagText.textContent = `Start ${state.diagDuration}s Diagnostic Scan`;
      if (dom.btnDiagIcon) dom.btnDiagIcon.textContent = '🎙️';
      if (dom.diagFill) dom.diagFill.style.width = '0%';
      if (dom.diagLockBadge) {
        dom.diagLockBadge.className = 'diag-lock-badge';
        if (dom.lockIcon) dom.lockIcon.textContent = '🔓';
        if (dom.lockText) dom.lockText.textContent = 'STREAMING';
      }
    }
  }

  function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // --- Autonomous Continual Learner UI Update & Controls ---
  function updateContinualLearnerUI(lrn) {
    if (!lrn) return;

    // Engine running pill
    if (dom.learnerEnginePill) {
      const conf = lrn.confidence ?? 95;
      if (lrn.is_running) {
        dom.learnerEnginePill.textContent = `ENGINE: RUNNING (${conf}%)`;
        dom.learnerEnginePill.style.color = 'var(--green)';
        dom.learnerEnginePill.style.borderColor = 'rgba(0, 255, 136, 0.4)';
        dom.learnerEnginePill.style.background = 'rgba(0, 255, 136, 0.12)';
      } else {
        dom.learnerEnginePill.textContent = 'ENGINE: OFF (PARKED)';
        dom.learnerEnginePill.style.color = 'var(--text-muted)';
        dom.learnerEnginePill.style.borderColor = 'var(--border-card)';
        dom.learnerEnginePill.style.background = 'rgba(255, 255, 255, 0.04)';
      }
    }

    // Status pill
    if (dom.learnerStatusPill) {
      if (lrn.is_anomaly || lrn.status === 'ANOMALY_DETECTED') {
        dom.learnerStatusPill.textContent = '🛡️ SHIELD LOCKED (DEFECT DETECTED)';
        dom.learnerStatusPill.style.color = '#ff3366';
        dom.learnerStatusPill.style.borderColor = 'rgba(255, 51, 102, 0.6)';
        dom.learnerStatusPill.style.background = 'rgba(255, 51, 102, 0.2)';
      } else if (lrn.is_running && lrn.status === 'ADAPTING_BASELINE') {
        dom.learnerStatusPill.textContent = '⚡ ACTIVE SELF-LEARNING';
        dom.learnerStatusPill.style.color = 'var(--green)';
        dom.learnerStatusPill.style.borderColor = 'rgba(0, 255, 136, 0.4)';
        dom.learnerStatusPill.style.background = 'rgba(0, 255, 136, 0.12)';
      } else if (lrn.status === 'BOOTSTRAPPING') {
        dom.learnerStatusPill.textContent = '🌱 BOOTSTRAPPING MANIFOLD';
        dom.learnerStatusPill.style.color = 'var(--cyan)';
        dom.learnerStatusPill.style.borderColor = 'rgba(0, 240, 255, 0.4)';
        dom.learnerStatusPill.style.background = 'rgba(0, 240, 255, 0.12)';
      } else {
        dom.learnerStatusPill.textContent = 'RESTING (ENGINE OFF)';
        dom.learnerStatusPill.style.color = 'var(--text-muted)';
        dom.learnerStatusPill.style.borderColor = 'var(--border-card)';
        dom.learnerStatusPill.style.background = 'rgba(255, 255, 255, 0.04)';
      }
    }

    // Regime chips
    const activeRegime = lrn.regime ?? 0;
    if (dom.chipRegimes) {
      dom.chipRegimes.forEach((chip, idx) => {
        if (chip) {
          if (lrn.is_running && idx === activeRegime) {
            chip.classList.add('active');
          } else {
            chip.classList.remove('active');
          }
        }
      });
    }

    // Learned time
    if (dom.learnerFrames) {
      const tot = lrn.total_learned ?? 0;
      dom.learnerFrames.textContent = `${tot}s (${tot} Frames)`;
    }

    // Drift guard badge
    if (dom.learnerGuard) {
      if (lrn.is_anomaly) {
        dom.learnerGuard.textContent = 'BASELINE PROTECTED (DRIFT FROZEN)';
        dom.learnerGuard.style.color = 'var(--red)';
      } else {
        dom.learnerGuard.textContent = 'SHIELD ARMED (3.2σ)';
        dom.learnerGuard.style.color = 'var(--blue)';
      }
    }

    // Z-Meter bar
    const score = Number(lrn.score ?? 0.8);
    if (dom.zMeterBar) {
      const pct = Math.min(100, Math.max(5, (score / 8.0) * 100));
      dom.zMeterBar.style.width = `${pct}%`;
      if (score >= 3.2 || lrn.is_anomaly) {
        dom.zMeterBar.classList.add('danger');
      } else {
        dom.zMeterBar.classList.remove('danger');
      }
    }

    if (dom.zMeterVal) {
      if (score >= 3.2 || lrn.is_anomaly) {
        dom.zMeterVal.textContent = `ALERT: ${score.toFixed(2)}σ (Defect Exceeds 3.2σ Limit — Baseline Frozen)`;
        dom.zMeterVal.style.color = 'var(--red)';
      } else if (!lrn.is_running) {
        dom.zMeterVal.textContent = 'Current Metric: 0.00σ (Engine Off)';
        dom.zMeterVal.style.color = 'var(--text-muted)';
      } else {
        dom.zMeterVal.textContent = `Current Metric: ${score.toFixed(2)}σ (Normal Vehicle Baseline Adaptation)`;
        dom.zMeterVal.style.color = 'var(--cyan)';
      }
    }
  }

  function initContinualLearnerControls() {
    if (dom.btnToggleEngine) {
      dom.btnToggleEngine.addEventListener('click', function () {
        fetch('/api/learner/toggle_engine', { method: 'POST' })
          .then(r => r.json())
          .then(data => {
            console.log('[Learner] Toggled engine state:', data);
          })
          .catch(e => console.error(e));
      });
    }

    if (dom.btnInjectDefect) {
      dom.btnInjectDefect.addEventListener('click', function () {
        fetch('/api/learner/simulate_defect', { method: 'POST' })
          .then(r => r.json())
          .then(data => {
            console.log('[Learner] Injected defect simulation:', data);
          })
          .catch(e => console.error(e));
      });
    }

    if (dom.btnResetLearner) {
      dom.btnResetLearner.addEventListener('click', function () {
        if (confirm('Reset learned vehicle baseline to factory defaults?')) {
          fetch('/api/learner/reset', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
              console.log('[Learner] Baseline reset:', data);
            })
            .catch(e => console.error(e));
        }
      });
    }
  }

  // --- Initialization on DOM Ready ---
  function init() {
    initCanvases();
    connectWebSocket();
    initLiveAudioListening();
    initBrowserMicrophoneCapture();
    initContinualLearnerControls();
    initPredictivePrognostics();
    requestAnimationFrame(renderLoop);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
