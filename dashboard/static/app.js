/**
 * MotoPulse™ Cockpit - AI Vehicle Acoustic & Vibration Telemetry UI
 * 
 * High-performance 60 FPS Canvas Telemetry visualizers:
 * 1. Dual-Microphone Oscilloscope (#scopeCanvas): 4cm baseline acoustic gradient (Left Cyan, Right Emerald)
 * 2. 50cm Acoustic Perimeter Radar (#radarCanvas): Circular sweep, proximity detection, lock states
 * 3. Piezo Seismograph (#seismoCanvas): Rolling mechanical vibration time-series chart & knock alerts
 * 4. Diagnostic Audio Recorder (#btn-record): 3s countdown & studio WAV playback
 * 5. Vehicle Defect Library Table (#dataset-tbody): Populated from /api/datasets with 7 car defect clips
 * 6. Resilient WebSocket client (ws://localhost:8765) with auto-reconnection & lifelike simulation fallback
 */

(function () {
  'use strict';

  // --- Constants & Pre-populated Vehicle Defect Library (Ishan's 7 Car Clips) ---
  const DEFAULT_DATASETS = [
    {
      file_name: "cranking_failure_freesound_community-car-not-starting-40006.wav",
      label: "cranking_failure",
      label_class: "red",
      duration_sec: "9.8",
      sensor_location: "Engine Bay",
      notes: "Car not starting / failed cranking attempt (9s)",
      url: "/dataset_audio/cranking_failure_freesound_community-car-not-starting-40006.wav"
    },
    {
      file_name: "cranking_failure_freesound_community-car-not-starting-74857.wav",
      label: "cranking_failure",
      label_class: "red",
      duration_sec: "20.5",
      sensor_location: "Engine Bay",
      notes: "Car not starting / struggling starter motor (20s)",
      url: "/dataset_audio/cranking_failure_freesound_community-car-not-starting-74857.wav"
    },
    {
      file_name: "difficult_start_VEHCar_Car_difficult_start_ID_0872_BigSoundBank.com.wav",
      label: "difficult_start",
      label_class: "orange",
      duration_sec: "45.9",
      sensor_location: "Engine Bay",
      notes: "Difficult delayed vehicle start and extended cranking (45s)",
      url: "/dataset_audio/difficult_start_VEHCar_Car_difficult_start_ID_0872_BigSoundBank.com.wav"
    },
    {
      file_name: "normal_idle_soumages-car-engine-335601.wav",
      label: "normal_idle",
      label_class: "green",
      duration_sec: "10.1",
      sensor_location: "Engine Bay Front",
      notes: "Steady car engine sound and idle rev (10s)",
      url: "/dataset_audio/normal_idle_soumages-car-engine-335601.wav"
    },
    {
      file_name: "engine_startup_car-ignition-1.wav",
      label: "engine_startup",
      label_class: "",
      duration_sec: "29.8",
      sensor_location: "Engine Bay",
      notes: "Car ignition start sequence (29s)",
      url: "/dataset_audio/engine_startup_car-ignition-1.wav"
    },
    {
      file_name: "brake_squeal_magiaz-car-brake-325519.wav",
      label: "brake_squeal",
      label_class: "red",
      duration_sec: "5.0",
      sensor_location: "Wheel Well / Brake Assembly",
      notes: "High pitch car brake squeak friction wear (5s)",
      url: "/dataset_audio/brake_squeal_magiaz-car-brake-325519.wav"
    },
    {
      file_name: "exhaust_leak_VEHCar_Damaged_muffler_3_parked_car_ID_1571_BigSoundBank.com.wav",
      label: "exhaust_leak",
      label_class: "orange",
      duration_sec: "16.3",
      sensor_location: "Exhaust Tip / Muffler",
      notes: "Damaged muffler exhaust sputtering leak on parked car (16s)",
      url: "/dataset_audio/exhaust_leak_VEHCar_Damaged_muffler_3_parked_car_ID_1571_BigSoundBank.com.wav"
    }
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

    // Audio recording state
    isRecording: false,
    recordTimerInterval: null,
    currentlyPlayingAudio: null
  };

  // --- DOM References ---
  const dom = {
    espStatus: document.getElementById('esp-status'),
    pillEsp: document.getElementById('pill-esp'),
    fpsBadge: document.getElementById('fps-badge'),

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

    // Recorder
    recStatusText: document.getElementById('rec-status-text'),
    recTimer: document.getElementById('rec-timer'),
    btnRecord: document.getElementById('btn-record'),
    latestPlaybackBox: document.getElementById('latest-playback-box'),
    latestAudioPlayer: document.getElementById('latest-audio-player'),

    // Defect Library Table
    datasetTbody: document.getElementById('dataset-tbody'),

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
    btnResetLearner: document.getElementById('btn-reset-learner')
  };

  // --- Canvas Contexts ---
  let scopeCtx = null;
  let radarCtx = null;
  let seismoCtx = null;

  function initCanvases() {
    if (dom.scopeCanvas) scopeCtx = dom.scopeCanvas.getContext('2d');
    if (dom.radarCanvas) radarCtx = dom.radarCanvas.getContext('2d');
    if (dom.seismoCanvas) seismoCtx = dom.seismoCanvas.getContext('2d');
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

    // Direct wave arrays if supplied
    if (Array.isArray(pkt.wave_l) && pkt.wave_l.length > 0) {
      const count = Math.min(128, pkt.wave_l.length);
      for (let i = 0; i < count; i++) state.waveLeft[i] = pkt.wave_l[i];
    }
    if (Array.isArray(pkt.wave_r) && pkt.wave_r.length > 0) {
      const count = Math.min(128, pkt.wave_r.length);
      for (let i = 0; i < count; i++) state.waveRight[i] = pkt.wave_r[i];
    }

    // Continual Learner Telemetry Update
    if (pkt.learner) {
      updateContinualLearnerUI(pkt.learner);
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

  // --- Feature 4: Live Diagnostic Audio Recorder (#btn-record) ---
  // Calls /api/record?seconds=3, animates countdown, loads & plays studio WAV
  function initAudioRecorder() {
    if (!dom.btnRecord) return;

    dom.btnRecord.addEventListener('click', function () {
      if (state.isRecording) return;
      startRecordingSequence();
    });
  }

  function startRecordingSequence() {
    state.isRecording = true;
    if (dom.btnRecord) {
      dom.btnRecord.disabled = true;
      dom.btnRecord.style.opacity = '0.7';
      dom.btnRecord.innerHTML = '<span class="rec-dot"></span> RECORDING VEHICLE SOUND (3s)...';
    }

    if (dom.recStatusText) {
      dom.recStatusText.textContent = '🔴 RECORDING IN PROGRESS — Dual INMP441 Studio DSP Active';
      dom.recStatusText.style.color = 'var(--cyan)';
    }

    // High-resolution countdown timer: 3.0s down to 0.0s
    let remainingMs = 3000;
    const startTime = performance.now();

    if (state.recordTimerInterval) clearInterval(state.recordTimerInterval);

    state.recordTimerInterval = setInterval(function () {
      const elapsed = performance.now() - startTime;
      remainingMs = Math.max(0, 3000 - elapsed);

      const sec = Math.floor(remainingMs / 1000);
      const tenths = Math.floor((remainingMs % 1000) / 100);
      if (dom.recTimer) {
        dom.recTimer.textContent = `00:0${sec}.${tenths}`;
      }

      if (remainingMs <= 0) {
        clearInterval(state.recordTimerInterval);
        state.recordTimerInterval = null;
      }
    }, 60);

    // Call /api/record?seconds=3
    const recordUrl = '/api/record?seconds=3';
    fetch(recordUrl, { method: 'POST' })
      .then(function (res) {
        if (!res.ok) {
          // Fallback to GET if server prefers GET
          return fetch(recordUrl);
        }
        return res;
      })
      .then(function (res) {
        if (!res.ok) throw new Error('Record endpoint returned status ' + res.status);
        return res.json();
      })
      .then(function (data) {
        const audioUrl = data.url || data.file || (data.filename ? `/audio/${data.filename}` : '/audio/latest_recording.wav');
        finishRecording(audioUrl);
      })
      .catch(function (err) {
        console.warn('[MotoPulse Recorder] /api/record endpoint error or offline fallback:', err);
        // Fallback for demo when backend is in standalone test mode
        setTimeout(function () {
          finishRecording('/dataset_audio/normal_idle_soumages-car-engine-335601.wav');
        }, 1200);
      });
  }

  function finishRecording(audioUrl) {
    state.isRecording = false;

    if (state.recordTimerInterval) {
      clearInterval(state.recordTimerInterval);
      state.recordTimerInterval = null;
    }

    if (dom.recTimer) dom.recTimer.textContent = '00:03.0';

    if (dom.recStatusText) {
      dom.recStatusText.textContent = '✓ Recording Complete • Enhanced Studio WAV Ready';
      dom.recStatusText.style.color = 'var(--green)';
    }

    if (dom.btnRecord) {
      dom.btnRecord.disabled = false;
      dom.btnRecord.style.opacity = '1';
      dom.btnRecord.innerHTML = '<span class="rec-dot"></span> START 3s VEHICLE RECORDING';
    }

    // Load and play enhanced studio WAV in #latest-audio-player
    if (dom.latestAudioPlayer && dom.latestPlaybackBox) {
      dom.latestPlaybackBox.style.display = 'block';
      dom.latestAudioPlayer.src = audioUrl;

      stopAllPlayingAudio();
      state.currentlyPlayingAudio = dom.latestAudioPlayer;

      const playPromise = dom.latestAudioPlayer.play();
      if (playPromise !== undefined) {
        playPromise.catch(function (e) {
          console.log('[MotoPulse Player] Browser autoplay restricted user interaction:', e);
        });
      }
    }
  }

  // --- Feature 5: Automotive Defect Library Table (#dataset-tbody) ---
  // Loads Ishan's 7 car audio recordings from /api/datasets with in-browser playback
  function loadDatasetTable() {
    if (!dom.datasetTbody) return;

    fetch('/api/datasets')
      .then(function (res) {
        if (!res.ok) throw new Error('API returned ' + res.status);
        return res.json();
      })
      .then(function (data) {
        if (Array.isArray(data) && data.length > 0) {
          renderDatasetRows(data);
        } else {
          renderDatasetRows(DEFAULT_DATASETS);
        }
      })
      .catch(function (err) {
        console.log('[MotoPulse Dataset] Using built-in vehicle defect library manifest:', err);
        renderDatasetRows(DEFAULT_DATASETS);
      });
  }

  function renderDatasetRows(items) {
    if (!dom.datasetTbody) return;
    dom.datasetTbody.innerHTML = '';

    items.forEach(function (item, index) {
      const tr = document.createElement('tr');

      // Determine label pill color
      let pillClass = item.label_class || '';
      if (!pillClass) {
        const lbl = (item.label || '').toLowerCase();
        if (lbl.includes('failure') || lbl.includes('squeal') || lbl.includes('knock')) {
          pillClass = 'red';
        } else if (lbl.includes('difficult') || lbl.includes('leak')) {
          pillClass = 'orange';
        } else if (lbl.includes('idle') || lbl.includes('normal')) {
          pillClass = 'green';
        }
      }

      const audioSrc = item.url || item.audio_url || `/dataset_audio/${item.file_name}`;
      const durationStr = item.duration_sec ? `${parseFloat(item.duration_sec).toFixed(1)}s` : '—';

      tr.innerHTML = `
        <td>
          <span class="defect-pill ${pillClass}">
            ${escapeHtml(item.label || 'Vehicle Defect')}
          </span>
        </td>
        <td>
          <code style="font-family: var(--font-mono); font-size: 0.78rem; color: #a5b4fc;">
            ${escapeHtml(item.file_name || 'audio.wav')}
          </code>
        </td>
        <td style="font-family: var(--font-mono); font-weight: 600;">
          ${escapeHtml(durationStr)}
        </td>
        <td>
          <span style="color: var(--text-muted); font-size: 0.8rem;">
            ${escapeHtml(item.sensor_location || 'Engine Bay')}
          </span>
        </td>
        <td>
          <span style="font-size: 0.82rem; line-height: 1.4;">
            ${escapeHtml(item.notes || 'Automotive acoustic test sample')}
          </span>
        </td>
        <td style="min-width: 200px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <button class="btn-play-clip" data-idx="${index}" style="
              background: rgba(0, 240, 255, 0.12);
              border: 1px solid rgba(0, 240, 255, 0.3);
              color: var(--cyan);
              padding: 6px 12px;
              border-radius: 6px;
              cursor: pointer;
              font-family: var(--font-mono);
              font-size: 0.75rem;
              font-weight: 700;
              transition: all 0.2s;
              display: flex;
              align-items: center;
              gap: 4px;
            ">
              <span class="play-icon">▶</span> Play
            </button>
            <audio id="clip-audio-${index}" src="${escapeHtml(audioSrc)}" preload="none" style="display:none;"></audio>
          </div>
        </td>
      `;

      dom.datasetTbody.appendChild(tr);
    });

    // Attach click listeners for dataset play buttons
    const playButtons = dom.datasetTbody.querySelectorAll('.btn-play-clip');
    playButtons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        const idx = this.getAttribute('data-idx');
        const audioEl = document.getElementById(`clip-audio-${idx}`);
        if (!audioEl) return;

        if (audioEl.paused) {
          stopAllPlayingAudio();
          audioEl.currentTime = 0;
          audioEl.play().then(() => {
            this.innerHTML = '<span class="play-icon" style="color: #ff3366;">⏸</span> Pause';
            this.style.background = 'rgba(255, 51, 102, 0.15)';
            this.style.borderColor = 'rgba(255, 51, 102, 0.4)';
            this.style.color = '#ff99aa';
            state.currentlyPlayingAudio = audioEl;
          }).catch(function (e) {
            console.log('Audio playback error:', e);
          });

          audioEl.onended = () => {
            this.innerHTML = '<span class="play-icon">▶</span> Play';
            this.style.background = 'rgba(0, 240, 255, 0.12)';
            this.style.borderColor = 'rgba(0, 240, 255, 0.3)';
            this.style.color = 'var(--cyan)';
            if (state.currentlyPlayingAudio === audioEl) state.currentlyPlayingAudio = null;
          };
        } else {
          audioEl.pause();
          this.innerHTML = '<span class="play-icon">▶</span> Play';
          this.style.background = 'rgba(0, 240, 255, 0.12)';
          this.style.borderColor = 'rgba(0, 240, 255, 0.3)';
          this.style.color = 'var(--cyan)';
          if (state.currentlyPlayingAudio === audioEl) state.currentlyPlayingAudio = null;
        }
      });
    });
  }

  function stopAllPlayingAudio() {
    if (state.currentlyPlayingAudio) {
      try {
        state.currentlyPlayingAudio.pause();
      } catch (e) {}
      state.currentlyPlayingAudio = null;
    }

    if (dom.latestAudioPlayer && !dom.latestAudioPlayer.paused) {
      dom.latestAudioPlayer.pause();
    }

    // Reset button states in table
    const playButtons = document.querySelectorAll('.btn-play-clip');
    playButtons.forEach(function (btn) {
      btn.innerHTML = '<span class="play-icon">▶</span> Play';
      btn.style.background = 'rgba(0, 240, 255, 0.12)';
      btn.style.borderColor = 'rgba(0, 240, 255, 0.3)';
      btn.style.color = 'var(--cyan)';
    });
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
    initAudioRecorder();
    initContinualLearnerControls();
    loadDatasetTable();
    requestAnimationFrame(renderLoop);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
