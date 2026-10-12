/* R85 HE Studio — arayüz
 * Python tarafı (r85_studio.py) window.pywebview.api üzerinden çağrılır.
 * Tarayıcıda tek başına açılırsa sahte (demo) veriyle çalışır, böylece tasarım test edilebilir. */
"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  const S = {
    init: null, prof: null, sel: null, mapped: new Set(),
    values: {}, peaks: {}, active: false,
    display: { lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0, pressed: [] },
  };

  const NICE = {
    F_ESC: "Esc", ESC: "`", BKSP: "Backspace", DEL: "Del", TAB: "Tab", CAPS: "Caps", ENTER: "Enter",
    PGUP: "PgUp", PGDN: "PgDn", LSHIFT: "Shift", RSHIFT: "Shift", LCTRL: "Ctrl", WIN: "Win",
    LALT: "Alt", RALT: "Ctrl", FN: "Fn", SPACE: "", UP: "↑", DOWN: "↓", LEFT: "←", RIGHT: "→",
  };
  const nice = (l) => (l in NICE ? NICE[l] : l);
  const tileName = (l) => (l === "SPACE" ? "Space" : nice(l));

  // ── çıktı eğrisi (gamepad_studio.KeyboardState.get_normalized ile aynı) ──
  function curveOut(x, st) {
    const dz = st.deadzone, c = st.sensitivity_curve;
    if (x < dz) return 0;
    const n = dz < 1 ? (x - dz) / (1 - dz) : 0;
    return clamp(Math.pow(n, c), 0, 1);
  }
  const actuationRaw = (st) => st.deadzone + (1 - st.deadzone) * Math.pow(st.button_threshold, 1 / st.sensitivity_curve);
  const amax = () => (S.prof && S.prof.settings.analog_max) || 350;
  const ratio = (l) => Math.min(1, (S.values[l] || 0) / amax());

  // ═══════════════════════════════════════════════════════════════
  //  Demo API (pywebview yoksa)
  // ═══════════════════════════════════════════════════════════════
  function makeMockApi() {
    const K = (...a) => a.map((l) => [l, 1, "key"]), G = [null, 0.5, "gap"];
    const L = [
      [["F_ESC", 1, "key"], G, ...K("F1", "F2", "F3", "F4"), G, ...K("F5", "F6", "F7", "F8"), G, ...K("F9", "F10", "F11", "F12"), G, ["LOGO", 1, "logo"], ["KNOB", 0, "knob"]],
      [...K("ESC", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="), ["BKSP", 2, "key"], ["DEL", 1, "key"]],
      [["TAB", 1.5, "key"], ...K("Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]"), ["\\", 1.5, "key"], ["PGUP", 1, "key"]],
      [["CAPS", 1.75, "key"], ...K("A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'"), ["ENTER", 2.25, "key"], ["PGDN", 1, "key"]],
      [["LSHIFT", 2.25, "key"], ...K("Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"), ["RSHIFT", 1.75, "key"], ["UP", 1, "key"], [null, 1, "gap"]],
      [["LCTRL", 1.25, "key"], ["WIN", 1.25, "key"], ["LALT", 1.25, "key"], ["SPACE", 6.25, "key"], ["FN", 1, "key"], ["RALT", 1, "key"], [null, 1, "gap"], ...K("LEFT", "DOWN", "RIGHT")],
    ];
    const groups = [
      ["SOL ÇUBUK (analog)", [["ls_up","LS Yukarı"],["ls_down","LS Aşağı"],["ls_left","LS Sol"],["ls_right","LS Sağ"]]],
      ["SAĞ ÇUBUK (analog)", [["rs_up","RS Yukarı"],["rs_down","RS Aşağı"],["rs_left","RS Sol"],["rs_right","RS Sağ"]]],
      ["TETİKLER (analog)", [["lt","LT   (PS5: L2)"],["rt","RT   (PS5: R2)"]]],
      ["BUTONLAR", [["a","A   (PS5: Cross)"],["b","B   (PS5: Circle)"],["x","X   (PS5: Square)"],["y","Y   (PS5: Triangle)"],["lb","LB  (PS5: L1)"],["rb","RB  (PS5: R1)"],["l3","L3  (sol çubuğa bas)"],["r3","R3  (sağ çubuğa bas)"],["start","Start (PS5: Options)"],["back","Back  (PS5: Create)"],["guide","Guide (PS tuşu)"]]],
      ["D-PAD", [["dpad_up","D-Pad Yukarı"],["dpad_down","D-Pad Aşağı"],["dpad_left","D-Pad Sol"],["dpad_right","D-Pad Sağ"]]],
      ["UYGULAMA", [["profile_next","Sonraki profil"],["profile_prev","Önceki profil"]]],
    ];
    const short = { ls_up:"LS↑", ls_down:"LS↓", ls_left:"LS←", ls_right:"LS→", rs_up:"RS↑", rs_down:"RS↓", rs_left:"RS←", rs_right:"RS→",
      lt:"LT", rt:"RT", a:"A", b:"B", x:"X", y:"Y", lb:"LB", rb:"RB", l3:"L3", r3:"R3", start:"STR", back:"BCK", guide:"GDE",
      dpad_up:"D↑", dpad_down:"D↓", dpad_left:"D←", dpad_right:"D→", profile_next:"P+", profile_prev:"P-" };
    const buttons = ["a","b","x","y","lb","rb","l3","r3","start","back","guide","dpad_up","dpad_down","dpad_left","dpad_right"];
    const defaults = { deadzone: 0.05, smoothing: 0.3, sensitivity_curve: 1.0, button_threshold: 0.15, analog_max: 350 };
    const sliders = [["deadzone","Deadzone",0,0.5],["smoothing","Smoothing",0,0.95],["sensitivity_curve","Sensitivity",0.2,3],["button_threshold","Button actuation",0.05,0.8],["analog_max","Analog Max",100,500]];
    const wasd = { ls_up: ["W"], ls_down: ["S"], ls_left: ["A"], ls_right: ["D"] };
    const P = {
      "Walk": { bindings: JSON.parse(JSON.stringify(wasd)), settings: { ...defaults } },
      "Drive": { bindings: { ...JSON.parse(JSON.stringify(wasd)), rt: ["W"], lt: ["S"] }, settings: { ...defaults } },
      "Full controller": { bindings: { ...JSON.parse(JSON.stringify(wasd)), a: ["SPACE"], b: ["LSHIFT"], x: ["E"], y: ["Q"], rs_up: ["I"], rs_down: ["K"], rs_left: ["J"], rs_right: ["L"] }, settings: { ...defaults, sensitivity_curve: 1.4 } },
    };
    let active = "Walk", block = false, on = false, rev = 0;
    const pd = () => ({ names: Object.keys(P), active, bindings: JSON.parse(JSON.stringify(P[active].bindings)), settings: { ...P[active].settings }, block, rev });
    const t0 = performance.now();
    const mapped = L.flat().filter((k) => k[2] === "key" && k[0] !== "TAB" && !/^F(_ESC|\d+)$/.test(k[0])).map((k) => k[0]);
    return {
      get_init: async () => ({ app: "R85 HE Studio", device: "Attack Shark R85 HE", layout: L, mapped, groups, short, buttons, sliders, defaults, profile: pd() }),
      get_state: async () => {
        const t = (performance.now() - t0) / 1000, w = (p, f = 1) => Math.max(0, Math.sin(t * f + p)) ** 1.5 * 350;
        const v = { W: w(0), A: w(2.1, 0.7), D: w(4.2, 0.7), S: w(3.3, 0.5) * 0.6, SPACE: w(1, 1.7) * 0.9, LSHIFT: w(5, 0.9) * 0.4, E: w(0.3, 2.3) * 0.7 };
        const n = (k) => Math.min(1, (v[k] || 0) / 350);
        const pr = [];
        if (n("SPACE") > 0.15) pr.push("a");
        if (n("E") > 0.15) pr.push("x");
        return { values: v, display: { lx: on ? n("D") - n("A") : 0, ly: on ? n("W") - n("S") : 0, rx: 0, ry: 0, lt: on ? n("S") : 0, rt: on ? n("W") : 0, pressed: on ? pr : [] },
          active: on, status: on ? { text: "GAMEPAD AKTİF", level: "ok" } : { text: "DEMO MODU", level: "info" }, profile_rev: rev, active_name: active };
      },
      get_profile: async () => pd(),
      switch_profile: async (n) => { if (P[n]) { active = n; rev++; } return pd(); },
      new_profile: async (n) => { while (P[n]) n += " 2"; P[n] = JSON.parse(JSON.stringify(P[active])); active = n; rev++; return pd(); },
      rename_profile: async (o, n) => { if (P[n]) return { result: "Bu isimde bir profil zaten var.", profile: pd() }; const e = Object.entries(P).map(([k, v]) => [k === o ? n : k, v]); for (const k in P) delete P[k]; e.forEach(([k, v]) => (P[k] = v)); if (active === o) active = n; rev++; return { result: "ok", profile: pd() }; },
      delete_profile: async (n) => { if (Object.keys(P).length <= 1) return { result: "Son profil silinemez.", profile: pd() }; delete P[n]; if (!P[active]) active = Object.keys(P)[0]; rev++; return { result: "ok", profile: pd() }; },
      set_binding: async (k, o, v) => { const l = (P[active].bindings[o] ||= []); if (v && !l.includes(k)) l.push(k); if (!v) l.splice(l.indexOf(k) >>> 0, l.includes(k) ? 1 : 0); return pd().bindings; },
      set_setting: async (k, v) => { P[active].settings[k] = v; return true; },
      toggle_active: async () => { on = !on; return "ok"; },
      set_block: async (v) => { block = v; return "ok"; },
    };
  }

  // ═══════════════════════════════════════════════════════════════
  //  3D klavye
  // ═══════════════════════════════════════════════════════════════
  const VIOLET = new THREE.Color("#7c3aed").convertSRGBToLinear();
  const PINK = new THREE.Color("#ec4899").convertSRGBToLinear();
  const CYAN = new THREE.Color("#22d3ee").convertSRGBToLinear();
  const GAP = 0.1, CAP_DEPTH = 0.3, CAP_BEVEL = 0.07, CAP_H = CAP_DEPTH + CAP_BEVEL * 2, TRAVEL = 0.2;
  const PLATE_Y = 0.5;
  const STILL = /still/.test(location.search);  // test: açılış animasyonu olmadan
  const CASE_W = 16, CASE_D = 6.2;
  const rowZ = (ri) => ri + (ri > 0 ? 0.2 : 0) - CASE_D / 2 + 0.5;
  // R85 HE gradyan tuş takımı: üstte beyaz, altta siyah
  const ROW_COLORS = ["#eef0f3", "#dfe2e7", "#bfc3ca", "#868b94", "#4b4e55", "#1e1f23"];
  const lin = (hex) => new THREE.Color(hex).convertSRGBToLinear();

  function rrShape(w, h, r) {
    const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
    r = Math.min(r, w / 2, h / 2);
    s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r);
    s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
    s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
    return s;
  }
  function rrPath(w, h, r) {
    const p = new THREE.Path(), x = -w / 2, y = -h / 2;
    p.moveTo(x + r, y); p.lineTo(x + w - r, y); p.quadraticCurveTo(x + w, y, x + w, y + r);
    p.lineTo(x + w, y + h - r); p.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    p.lineTo(x + r, y + h); p.quadraticCurveTo(x, y + h, x, y + h - r);
    p.lineTo(x, y + r); p.quadraticCurveTo(x, y, x + r, y);
    return p;
  }
  function flatExtrude(shape, depth, bevel, segs = 3) {
    const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: segs, curveSegments: 8 });
    g.rotateX(-Math.PI / 2);
    g.translate(0, bevel, 0);
    return g;
  }
  function canvasTex(canvas) {
    const t = new THREE.CanvasTexture(canvas);
    t.encoding = THREE.sRGBEncoding;
    t.anisotropy = 8;
    return t;
  }
  function radialTex(inner, outer = "rgba(0,0,0,0)", size = 128) {
    const c = document.createElement("canvas"); c.width = c.height = size;
    const g = c.getContext("2d"), gr = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    gr.addColorStop(0, inner); gr.addColorStop(1, outer);
    g.fillStyle = gr; g.fillRect(0, 0, size, size);
    return canvasTex(c);
  }

  class Keyboard3D {
    constructor(canvas, layout, mapped, onSelect) {
      this.canvas = canvas;
      this.onSelect = onSelect;
      this.keys = {};
      this.pick = [];
      this.hover = null;
      this.selected = null;
      this.ringCache = {};

      const r = (this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true }));
      r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      r.outputEncoding = THREE.sRGBEncoding;
      r.toneMapping = THREE.ACESFilmicToneMapping;
      r.toneMappingExposure = 0.95;
      r.shadowMap.enabled = true;
      r.shadowMap.type = THREE.PCFSoftShadowMap;

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(32, 2, 0.1, 200);
      this.target = new THREE.Vector3(0, 0.4, 0.15);
      this.base = 20;
      this.zoom = 1;
      this.view = { az: -0.55, pol: 1.12, rad: 34 };
      this.goal = { az: 0, pol: 0.78, rad: 20 };

      this._lights();
      this._case();
      this._keys(layout, mapped);
      this._controls();
      new ResizeObserver(() => this.resize()).observe(canvas.parentElement);
      this.resize();
    }

    _lights() {
      const s = this.scene;
      s.add(new THREE.HemisphereLight(0xc4b5fd, 0x0a0614, 0.55));
      const key = new THREE.DirectionalLight(0xffffff, 1.05);
      key.position.set(-5, 12, 9);
      key.castShadow = true;
      key.shadow.mapSize.set(2048, 2048);
      Object.assign(key.shadow.camera, { left: -12, right: 12, top: 8, bottom: -8, near: 1, far: 40 });
      key.shadow.bias = -0.0006;
      s.add(key);
      const rim = new THREE.DirectionalLight(0x8b5cf6, 0.9);
      rim.position.set(4, 5, -10);
      s.add(rim);
      const fill = new THREE.PointLight(0xe879f9, 0.55, 30);
      fill.position.set(9, 3, 6);
      s.add(fill);
    }

    _case() {
      const s = this.scene;
      this.kb = new THREE.Group();
      this.kb.rotation.x = 0.05;
      s.add(this.kb);

      // zemin: gölge + hafif hale
      const floor = new THREE.Mesh(new THREE.PlaneGeometry(90, 90), new THREE.ShadowMaterial({ opacity: 0.5 }));
      floor.rotation.x = -Math.PI / 2; floor.position.y = -0.02; floor.receiveShadow = true;
      s.add(floor);
      const halo = new THREE.Mesh(new THREE.PlaneGeometry(30, 15),
        new THREE.MeshBasicMaterial({ map: radialTex("rgba(124,58,237,0.45)"), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
      halo.rotation.x = -Math.PI / 2; halo.position.y = -0.01;
      s.add(halo);

      // siyah alüminyum kasa (R85 HE)
      const OW = CASE_W + 0.7, OD = CASE_D + 0.75, IW = CASE_W + 0.2, ID = CASE_D + 0.25;
      const caseMat = new THREE.MeshStandardMaterial({ color: lin(0x111215), metalness: 0.55, roughness: 0.38 });
      const base = new THREE.Mesh(flatExtrude(rrShape(OW, OD, 0.3), 0.3, 0.1), caseMat);
      base.castShadow = true; base.receiveShadow = true;
      this.kb.add(base);
      const ring = rrShape(OW, OD, 0.3);
      ring.holes.push(rrPath(IW, ID, 0.15));
      const frame = new THREE.Mesh(flatExtrude(ring, 0.5, 0.1), caseMat);
      frame.castShadow = true; frame.receiveShadow = true;
      this.kb.add(frame);

      const plate = new THREE.Mesh(new THREE.PlaneGeometry(IW, ID), new THREE.MeshStandardMaterial({ color: lin(0x08080a), roughness: 0.9 }));
      plate.rotation.x = -Math.PI / 2; plate.position.y = PLATE_Y + 0.001; plate.receiveShadow = true;
      this.kb.add(plate);

      // arka üst kenardaki RGB ışık barı
      const c = document.createElement("canvas"); c.width = 1024; c.height = 8;
      const g = c.getContext("2d"), gr = g.createLinearGradient(0, 0, 1024, 0);
      ["#ff3b6b", "#ffb020", "#3df57a", "#22d3ee", "#6d5bff", "#e879f9", "#ff3b6b"].forEach((col, i, a) => gr.addColorStop(i / (a.length - 1), col));
      g.fillStyle = gr; g.fillRect(0, 0, 1024, 8);
      this.stripTex = canvasTex(c);
      this.stripTex.wrapS = THREE.RepeatWrapping;
      const barMat = new THREE.MeshBasicMaterial({ map: this.stripTex, toneMapped: false });
      const bar = new THREE.Mesh(new THREE.BoxGeometry(OW - 0.5, 0.07, 0.1), barMat);
      bar.position.set(0, 0.7 + 0.035, -OD / 2 + 0.17);
      this.kb.add(bar);
      const backBar = new THREE.Mesh(new THREE.PlaneGeometry(OW - 0.5, 0.1), barMat);
      backBar.position.set(0, 0.62, -OD / 2 - 0.105); backBar.rotation.y = Math.PI;
      this.kb.add(backBar);
      const spill = new THREE.Mesh(new THREE.PlaneGeometry(20, 3.2),
        new THREE.MeshBasicMaterial({ map: radialTex("rgba(167,139,250,0.55)"), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
      spill.rotation.x = -Math.PI / 2; spill.position.set(0, 0.0, -OD / 2 - 1.0);
      s.add(spill);

      this.glowTex = radialTex("rgba(255,255,255,1)", "rgba(255,255,255,0)");
    }

    _logo(cx, cz) {
      const c = document.createElement("canvas"); c.width = c.height = 256;
      const g = c.getContext("2d");
      g.fillStyle = "#0c0c0e"; g.fillRect(0, 0, 256, 256);
      // köpekbalığı yüzgeci şeklinde "A"
      g.fillStyle = "#f2f2f2";
      g.beginPath();
      g.moveTo(58, 206); g.bezierCurveTo(92, 150, 128, 84, 196, 46); g.lineTo(178, 112);
      g.bezierCurveTo(166, 150, 160, 180, 164, 206); g.lineTo(136, 206); g.lineTo(140, 164);
      g.lineTo(108, 164); g.lineTo(88, 206); g.closePath(); g.fill();
      g.fillStyle = "#0c0c0e"; g.beginPath(); g.moveTo(118, 142); g.lineTo(146, 100); g.lineTo(142, 142); g.closePath(); g.fill();
      const top = new THREE.MeshStandardMaterial({ map: canvasTex(c), metalness: 0.4, roughness: 0.35 });
      const side = new THREE.MeshStandardMaterial({ color: lin(0x0c0c0e), metalness: 0.5, roughness: 0.4 });
      const plate = new THREE.Mesh(flatExtrude(rrShape(1 - GAP - 0.1, 1 - GAP - 0.1, 0.08), 0.12, 0.04, 2), [top, side]);
      // üst yüzeye doku düzgün otursun diye UV'leri x/z konumundan hesapla
      const pos = plate.geometry.attributes.position, uv = plate.geometry.attributes.uv, half = (1 - GAP) / 2;
      for (let i = 0; i < pos.count; i++) uv.setXY(i, (pos.getX(i) + half) / (2 * half), 1 - (pos.getZ(i) + half) / (2 * half));
      plate.position.set(cx, PLATE_Y, cz);
      plate.castShadow = true;
      this.kb.add(plate);
    }

    _knob(cx, cz) {
      const c = document.createElement("canvas"); c.width = 256; c.height = 32;
      const g = c.getContext("2d");
      for (let i = 0; i < 64; i++) { g.fillStyle = i % 2 ? "#3a3c42" : "#1b1c20"; g.fillRect(i * 4, 0, 4, 32); }
      const side = new THREE.MeshStandardMaterial({ map: canvasTex(c), metalness: 0.8, roughness: 0.32 });
      const top = new THREE.MeshStandardMaterial({ color: lin(0x26272c), metalness: 0.85, roughness: 0.25 });
      // R85 HE'de knob kasanın sağ yan yüzünde, F sırası hizasında durur (ekseni yatay)
      const sideX = (CASE_W + 0.7) / 2 + 0.1, len = 0.42, R = 0.4;
      const knob = new THREE.Mesh(new THREE.CylinderGeometry(R, R, len, 64), [side, top, top]);
      knob.rotation.z = -Math.PI / 2;
      knob.position.set(sideX + len / 2, 0.42, cz);
      knob.castShadow = true;
      this.kb.add(knob);
      const dot = new THREE.Mesh(new THREE.CircleGeometry(0.05, 20), new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }));
      dot.rotation.y = Math.PI / 2; dot.position.set(sideX + len + 0.002, 0.42 + R * 0.65, cz);
      this.kb.add(dot);
    }

    _keys(layout, mapped) {
      const geoCache = {};
      const capGeo = (w) => (geoCache[w] ||= flatExtrude(rrShape(w - GAP - CAP_BEVEL * 2, 1 - GAP - CAP_BEVEL * 2, 0.1), CAP_DEPTH, CAP_BEVEL, 4));
      layout.forEach((row, ri) => {
        let x = -CASE_W / 2;
        const cz = rowZ(ri);
        row.forEach(([label, w, kind]) => {
          const cx = x + w / 2;
          x += w;
          if (kind === "gap") return;
          if (kind === "logo") return this._logo(cx, cz);
          if (kind === "knob") return this._knob(cx, cz);
          const isMapped = mapped.has(label);
          const grp = new THREE.Group();
          grp.position.set(cx, PLATE_Y, cz);
          this.kb.add(grp);

          const hex = ROW_COLORS[Math.min(ri, ROW_COLORS.length - 1)];
          const mat = new THREE.MeshStandardMaterial({ color: lin(hex), roughness: 0.5, metalness: 0.02, emissive: 0x000000 });
          const cap = new THREE.Mesh(capGeo(w), mat);
          cap.castShadow = true; cap.receiveShadow = true;
          grp.add(cap);

          const lw = w - GAP - 0.1, lh = 1 - GAP - 0.1;
          const lc = document.createElement("canvas");
          lc.height = 200; lc.width = Math.round(200 * lw / lh);
          const ltex = canvasTex(lc);
          const legend = new THREE.Mesh(new THREE.PlaneGeometry(lw, lh), new THREE.MeshBasicMaterial({ map: ltex, transparent: true, depthWrite: false }));
          legend.rotation.x = -Math.PI / 2; legend.position.y = CAP_H + 0.004;
          grp.add(legend);

          const glowMat = new THREE.MeshBasicMaterial({ map: this.glowTex, color: VIOLET.clone(), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false });
          const glow = new THREE.Mesh(new THREE.PlaneGeometry(w + 0.7, 1.7), glowMat);
          glow.rotation.x = -Math.PI / 2; glow.position.set(cx, PLATE_Y + 0.004, cz);
          this.kb.add(glow);

          const light = parseInt(hex.slice(1, 3), 16) >= 0x80;
          const k = { label, w, grp, cap, mat, legend, lc, ltex, glow, glowMat, mapped: isMapped, light, hue: (cx + CASE_W / 2) / CASE_W, cur: 0, lift: 0, bind: "", sel: false };
          cap.userData.k = k; legend.userData.k = k;
          this.pick.push(cap, legend);
          this.keys[label] = k;
          this.drawLegend(k);
        });
      });

      this.ring = new THREE.Mesh(new THREE.PlaneGeometry(1, 1),
        new THREE.MeshBasicMaterial({ transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }));
      this.ring.rotation.x = -Math.PI / 2;
      this.ring.visible = false;
      this.kb.add(this.ring);
    }

    ringTex(w) {
      if (this.ringCache[w]) return this.ringCache[w];
      const pw = w + 0.36, ph = 1.36, H = 128, W = Math.round(H * pw / ph);
      const c = document.createElement("canvas"); c.width = W; c.height = H;
      const g = c.getContext("2d"), s = H / ph, m = 0.18 * s, r = 0.2 * s;
      g.strokeStyle = "#22d3ee"; g.shadowColor = "#22d3ee";
      for (const [lw, blur] of [[6, 18], [3, 6]]) {
        g.lineWidth = lw; g.shadowBlur = blur;
        g.beginPath();
        g.roundRect ? g.roundRect(m, m, W - 2 * m, H - 2 * m, r) : g.rect(m, m, W - 2 * m, H - 2 * m);
        g.stroke();
      }
      return (this.ringCache[w] = { tex: canvasTex(c), pw, ph });
    }

    drawLegend(k) {
      const c = k.lc, g = c.getContext("2d"), W = c.width, H = c.height;
      g.clearRect(0, 0, W, H);
      const main = nice(k.label);
      const labelCol = k.light ? (!k.mapped ? "#a3a8b0" : k.sel ? "#0e7490" : "#26272c") : (!k.mapped ? "#6b6f77" : k.sel ? "#67e8f9" : "#eef0f3");
      const fitFont = (txt, weight, size, maxW) => {
        for (; size > 18; size -= 2) { g.font = `${weight} ${size}px "Segoe UI", sans-serif`; if (g.measureText(txt).width <= maxW) break; }
      };
      g.textBaseline = "middle";
      if (!k.bind) {
        // atanmamış tuş: harf ortada
        g.textAlign = "center"; g.fillStyle = labelCol;
        fitFont(main, 700, main.length <= 1 ? 72 : main.length <= 3 ? 56 : 44, W - 24);
        if (main) g.fillText(main, W / 2, H * 0.5);
      } else {
        // atanmış tuş: harf sol üstte küçük, atama büyük rozet içinde
        if (main) {
          g.textAlign = "left"; g.fillStyle = labelCol;
          fitFont(main, 700, 38, W - 30);
          g.fillText(main, 16, H * 0.2);
        }
        const bx = 10, by = H * 0.4, bw = W - 20, bh = H * 0.52;
        const bg = g.createLinearGradient(0, by, 0, by + bh);
        bg.addColorStop(0, k.sel ? "rgba(34,211,238,0.85)" : "rgba(167,139,250,0.95)");
        bg.addColorStop(1, k.sel ? "rgba(8,145,178,0.85)" : "rgba(124,58,237,0.95)");
        g.fillStyle = bg;
        g.beginPath(); g.roundRect ? g.roundRect(bx, by, bw, bh, 22) : g.rect(bx, by, bw, bh); g.fill();
        g.strokeStyle = "rgba(255,255,255,0.55)"; g.lineWidth = 3; g.stroke();
        g.textAlign = "center"; g.fillStyle = "#ffffff";
        g.shadowColor = "rgba(30,0,60,0.8)"; g.shadowBlur = 6;
        fitFont(k.bind, 800, 76, bw - 24);
        g.fillText(k.bind, W / 2, by + bh / 2 + 3);
        g.shadowBlur = 0;
      }
      k.ltex.needsUpdate = true;
    }

    setBindings(map) {
      for (const k of Object.values(this.keys)) {
        const b = map[k.label] || "";
        if (b !== k.bind) { k.bind = b; this.drawLegend(k); }
      }
    }

    setSelected(label) {
      for (const k of Object.values(this.keys)) {
        const s = k.label === label;
        if (s !== k.sel) { k.sel = s; this.drawLegend(k); }
      }
      this.selected = this.keys[label] || null;
      if (this.selected) {
        const k = this.selected, rt = this.ringTex(k.w);
        this.ring.material.map = rt.tex; this.ring.material.needsUpdate = true;
        this.ring.scale.set(rt.pw, rt.ph, 1);
        this.ring.position.set(k.grp.position.x, PLATE_Y + 0.006, k.grp.position.z);
        this.ring.visible = true;
      }
    }

    _controls() {
      const c = this.canvas;
      let drag = null;
      c.addEventListener("pointerdown", (e) => {
        drag = { x: e.clientX, y: e.clientY, moved: 0 };
        c.setPointerCapture(e.pointerId);
      });
      c.addEventListener("pointermove", (e) => {
        if (drag) {
          const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
          drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy);
          if (drag.moved > 4) {
            c.classList.add("dragging");
            this.goal.az = clamp(this.goal.az - dx * 0.006, -1.2, 1.2);
            this.goal.pol = clamp(this.goal.pol - dy * 0.005, 0.22, 1.3);
          }
        } else {
          const k = this._hit(e);
          if (k !== this.hover) { this.hover = k; c.classList.toggle("hovering", !!k); }
        }
      });
      c.addEventListener("pointerup", (e) => {
        if (drag && drag.moved <= 4) { const k = this._hit(e); if (k) this.onSelect(k.label); }
        drag = null; c.classList.remove("dragging");
      });
      c.addEventListener("pointerleave", () => { if (!drag) { this.hover = null; c.classList.remove("hovering"); } });
      c.addEventListener("wheel", (e) => {
        e.preventDefault();
        this.zoom = clamp(this.zoom * (1 + e.deltaY * 0.0012), 0.55, 1.8);
        this.goal.rad = this.base * this.zoom;
      }, { passive: false });
      c.addEventListener("dblclick", () => { this.zoom = 1; Object.assign(this.goal, { az: 0, pol: 0.78, rad: this.base }); });
      this.ray = new THREE.Raycaster();
      this.ndc = new THREE.Vector2();
    }

    _hit(e) {
      const r = this.canvas.getBoundingClientRect();
      this.ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      this.ray.setFromCamera(this.ndc, this.camera);
      const h = this.ray.intersectObjects(this.pick, false)[0];
      return h ? h.object.userData.k : null;
    }

    resize() {
      const p = this.canvas.parentElement, w = p.clientWidth, h = p.clientHeight;
      if (!w || !h) return;
      this.renderer.setSize(w, h, false);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      const hHalf = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
      this.base = clamp(Math.max(9.4 / (hHalf * this.camera.aspect), 4.9 / hHalf), 11, 46);
      this.goal.rad = this.base * this.zoom;
    }

    frame(dt, t) {
      const e = STILL ? 1 : 1 - Math.exp(-dt * 7);
      for (const a of ["az", "pol", "rad"]) this.view[a] += (this.goal[a] - this.view[a]) * e;
      const { az, pol, rad } = this.view;
      this.camera.position.set(this.target.x + rad * Math.sin(pol) * Math.sin(az), this.target.y + rad * Math.cos(pol), this.target.z + rad * Math.sin(pol) * Math.cos(az));
      this.camera.lookAt(this.target);

      const fast = 1 - Math.exp(-dt * 38), soft = 1 - Math.exp(-dt * 14);
      const pulse = 0.5 + 0.5 * Math.sin(t * 3.2);
      for (const k of Object.values(this.keys)) {
        const target = k.mapped ? ratio(k.label) : 0;
        k.cur += (target - k.cur) * fast;
        k.lift += ((k === this.hover ? 0.035 : 0) - k.lift) * soft;
        k.grp.position.y = PLATE_Y - k.cur * TRAVEL + k.lift;
        const r = k.cur;
        if (r > 0.015) {
          k.mat.emissive.copy(VIOLET).lerp(PINK, r);
          k.mat.emissiveIntensity = 0.35 + r * 0.9;
          k.glowMat.color.copy(VIOLET).lerp(PINK, r);
          k.glowMat.opacity = 0.25 + r * 0.85;
        } else if (k.sel) {
          k.mat.emissive.copy(CYAN);
          k.mat.emissiveIntensity = 0.08 + pulse * 0.1;
          k.glowMat.color.copy(CYAN);
          k.glowMat.opacity = 0.12 + pulse * 0.12;
        } else {
          k.mat.emissiveIntensity = 0;
          if (k.bind) { k.glowMat.color.copy(VIOLET); k.glowMat.opacity = 0.32; }
          else { k.glowMat.color.setHSL((k.hue * 0.9 + t * 0.06) % 1, 0.95, 0.55); k.glowMat.opacity = 0.16; }
        }
      }
      if (this.selected) {
        this.ring.material.opacity = 0.55 + pulse * 0.45;
        this.ring.position.y = PLATE_Y + 0.006;
      }
      this.stripTex.offset.x = (t * 0.06) % 1;
      this.renderer.render(this.scene, this.camera);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  2D çizimler (çubuk, yol göstergesi, eğri)
  // ═══════════════════════════════════════════════════════════════
  function ctx2d(c) {
    const dpr = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
    const g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    return { g, w, h };
  }
  const grad = (g, x0, y0, x1, y1) => { const gr = g.createLinearGradient(x0, y0, x1, y1); gr.addColorStop(0, "#8b5cf6"); gr.addColorStop(1, "#f472b6"); return gr; };
  function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect ? g.roundRect(x, y, w, h, r) : g.rect(x, y, w, h); }

  function drawStick(c, x, y, dz) {
    const { g, w, h } = ctx2d(c), cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2 - 8;
    const bg = g.createRadialGradient(cx, cy, 0, cx, cy, R);
    bg.addColorStop(0, "#151127"); bg.addColorStop(1, "#0b0916");
    g.fillStyle = bg; g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.fill();
    g.strokeStyle = "rgba(139,92,246,0.35)"; g.lineWidth = 1.5; g.stroke();
    g.strokeStyle = "rgba(139,92,246,0.12)"; g.lineWidth = 1;
    for (const f of [0.33, 0.66]) { g.beginPath(); g.arc(cx, cy, R * f, 0, Math.PI * 2); g.stroke(); }
    g.beginPath(); g.moveTo(cx - R, cy); g.lineTo(cx + R, cy); g.moveTo(cx, cy - R); g.lineTo(cx, cy + R); g.stroke();
    if (dz > 0.005) { g.setLineDash([2, 3]); g.strokeStyle = "rgba(251,113,133,0.5)"; g.beginPath(); g.arc(cx, cy, R * dz, 0, Math.PI * 2); g.stroke(); g.setLineDash([]); }
    const kx = cx + x * R, ky = cy - y * R, mag = Math.min(1, Math.hypot(x, y));
    if (mag > 0.02) {
      g.strokeStyle = grad(g, cx, cy, kx, ky); g.lineWidth = 3; g.lineCap = "round";
      g.beginPath(); g.moveTo(cx, cy); g.lineTo(kx, ky); g.stroke();
    }
    g.shadowColor = mag > 0.02 ? "#f472b6" : "#8b5cf6"; g.shadowBlur = 8 + mag * 14;
    g.fillStyle = mag > 0.02 ? "#f5d0fe" : "#c4b5fd";
    g.beginPath(); g.arc(kx, ky, 6.5, 0, Math.PI * 2); g.fill();
    g.shadowBlur = 0;
  }

  function drawTravel(c, r, peak, st) {
    const { g, w, h } = ctx2d(c), x = 28, tw = 20, top = 8, bot = h - 8, th = bot - top;
    rr(g, x, top, tw, th, 7); g.fillStyle = "#16122a"; g.fill();
    g.strokeStyle = "rgba(139,92,246,0.25)"; g.lineWidth = 1; g.stroke();
    if (r > 0.004) {
      g.save(); rr(g, x, top, tw, th, 7); g.clip();
      g.shadowColor = "#f472b6"; g.shadowBlur = 14;
      g.fillStyle = grad(g, 0, top, 0, top + th); g.fillRect(x, top, tw, th * r);
      g.restore();
    }
    g.fillStyle = "#5b5778"; g.font = "9px Segoe UI";
    for (let i = 0; i <= 4; i++) { const yy = top + th * i / 4; g.fillRect(x + tw + 4, yy - 0.5, 4, 1); }
    const line = (v, col, lbl, dash) => {
      const yy = top + th * v;
      g.strokeStyle = col; g.lineWidth = 1.5; g.setLineDash(dash || []);
      g.beginPath(); g.moveTo(x - 4, yy); g.lineTo(x + tw + 4, yy); g.stroke(); g.setLineDash([]);
      g.fillStyle = col; g.font = "700 8px Segoe UI"; g.textAlign = "right"; g.fillText(lbl, x - 5, yy + 3); g.textAlign = "left";
    };
    if (st.deadzone > 0.005) line(st.deadzone, "#fb7185", "DZ", [3, 2]);
    line(actuationRaw(st), "#22d3ee", "TET");
    if (peak > 0.01) {
      const yy = top + th * Math.min(1, peak);
      g.fillStyle = "#a78bfa"; g.beginPath(); g.moveTo(x + tw + 2, yy); g.lineTo(x + tw + 9, yy - 4); g.lineTo(x + tw + 9, yy + 4); g.fill();
    }
  }

  function drawCurve(c, r, st) {
    const { g, w, h } = ctx2d(c), L = 26, R = 8, T = 8, B = 20, pw = w - L - R, ph = h - T - B;
    const X = (v) => L + v * pw, Y = (v) => T + (1 - v) * ph;
    rr(g, L, T, pw, ph, 8); g.fillStyle = "#100d1e"; g.fill();
    g.strokeStyle = "rgba(139,92,246,0.10)"; g.lineWidth = 1;
    for (let i = 1; i < 4; i++) { g.beginPath(); g.moveTo(X(i / 4), T); g.lineTo(X(i / 4), T + ph); g.moveTo(L, Y(i / 4)); g.lineTo(L + pw, Y(i / 4)); g.stroke(); }
    if (st.deadzone > 0.005) { g.fillStyle = "rgba(251,113,133,0.10)"; g.fillRect(X(0), T, pw * st.deadzone, ph); }
    const thr = st.button_threshold;
    g.setLineDash([4, 3]); g.strokeStyle = "rgba(34,211,238,0.55)";
    g.beginPath(); g.moveTo(L, Y(thr)); g.lineTo(L + pw, Y(thr)); g.stroke(); g.setLineDash([]);
    g.fillStyle = "rgba(34,211,238,0.8)"; g.font = "700 8.5px Segoe UI"; g.textAlign = "right"; g.fillText("BUTON", L + pw - 4, Y(thr) - 4);

    g.beginPath();
    for (let i = 0; i <= 120; i++) { const v = i / 120; const px = X(v), py = Y(curveOut(v, st)); i ? g.lineTo(px, py) : g.moveTo(px, py); }
    const area = new Path2D(); area.moveTo(X(0), Y(0));
    for (let i = 0; i <= 120; i++) { const v = i / 120; area.lineTo(X(v), Y(curveOut(v, st))); }
    area.lineTo(X(1), Y(0)); area.closePath();
    const ag = g.createLinearGradient(0, T, 0, T + ph); ag.addColorStop(0, "rgba(232,121,249,0.20)"); ag.addColorStop(1, "rgba(139,92,246,0.02)");
    g.fillStyle = ag; g.fill(area);
    g.strokeStyle = grad(g, L, 0, L + pw, 0); g.lineWidth = 2.5; g.shadowColor = "#c084fc"; g.shadowBlur = 10; g.stroke(); g.shadowBlur = 0;

    const o = curveOut(r, st);
    if (r > 0.004) {
      g.setLineDash([2, 3]); g.strokeStyle = "rgba(244,114,182,0.5)"; g.lineWidth = 1;
      g.beginPath(); g.moveTo(X(r), Y(0)); g.lineTo(X(r), Y(o)); g.lineTo(L, Y(o)); g.stroke(); g.setLineDash([]);
    }
    g.shadowColor = "#f472b6"; g.shadowBlur = 14; g.fillStyle = "#fdf4ff";
    g.beginPath(); g.arc(X(r), Y(o), 5, 0, Math.PI * 2); g.fill(); g.shadowBlur = 0;

    g.fillStyle = "#5b5778"; g.font = "9px Segoe UI"; g.textAlign = "left";
    g.fillText("tuş yolu →", L + 2, h - 5);
    g.textAlign = "right"; g.fillText(Math.round(o * 100) + "%", L - 4, Math.max(T + 8, Math.min(T + ph, Y(o) + 3)));
  }

  // ═══════════════════════════════════════════════════════════════
  //  Uygulama
  // ═══════════════════════════════════════════════════════════════
  let api = null, kb = null;
  const SLIDER_STEP = { deadzone: 0.01, smoothing: 0.01, sensitivity_curve: 0.05, button_threshold: 0.01, analog_max: 5 };
  const fmt = (k, v) => (k === "analog_max" ? Math.round(v).toString() : Number(v).toFixed(2));

  function toast(msg, info) {
    const t = $("toast");
    t.textContent = msg; t.className = "toast" + (info ? " info" : ""); t.hidden = false;
    clearTimeout(toast.tm); toast.tm = setTimeout(() => (t.hidden = true), 3800);
  }

  function bindMap() {
    const m = {};
    for (const [out, keys] of Object.entries(S.prof.bindings)) for (const k of keys || []) (m[k] ||= []).push(out);
    const txt = {};
    for (const [k, outs] of Object.entries(m)) txt[k] = outs.slice(0, 2).map((o) => S.init.short[o] || o).join(" ") + (outs.length > 2 ? "+" : "");
    return txt;
  }

  // profil sekmeleri
  function buildTabs() {
    const box = $("tabs");
    box.textContent = "";
    for (const name of S.prof.names) {
      const b = document.createElement("button");
      b.className = "tab" + (name === S.prof.active ? " active" : "");
      b.textContent = name;
      b.title = "Çift tık: yeniden adlandır · Sağ tık: menü";
      b.onclick = () => name !== S.prof.active && api.switch_profile(name).then(applyProfile);
      b.ondblclick = () => renameProfile(name);
      b.oncontextmenu = (e) => { e.preventDefault(); openCtx(e, name); };
      box.appendChild(b);
    }
    const add = document.createElement("button");
    add.className = "tab add"; add.textContent = "+"; add.title = "Yeni profil (aktif profilin kopyası)";
    add.onclick = async () => { const n = await askName("Yeni profil", ""); if (n) applyProfile(await api.new_profile(n)); };
    box.appendChild(add);
  }

  async function renameProfile(name) {
    const n = await askName("Profili yeniden adlandır", name);
    if (!n || n === name) return;
    const res = await api.rename_profile(name, n);
    if (res.result !== "ok") toast(res.result);
    applyProfile(res.profile);
  }

  function openCtx(e, name) {
    const m = $("ctx");
    m.hidden = false;
    m.style.left = Math.min(e.clientX, innerWidth - 180) + "px";
    m.style.top = e.clientY + 4 + "px";
    m.onclick = async (ev) => {
      const act = ev.target.dataset.act;
      m.hidden = true;
      if (act === "rename") renameProfile(name);
      if (act === "dup") {
        if (name !== S.prof.active) applyProfile(await api.switch_profile(name));
        applyProfile(await api.new_profile(name + " kopya"));
      }
      if (act === "delete") {
        if (!confirm(`'${name}' profili silinsin mi?`)) return;
        const res = await api.delete_profile(name);
        if (res.result !== "ok") toast(res.result);
        applyProfile(res.profile);
      }
    };
  }
  document.addEventListener("pointerdown", (e) => { if (!$("ctx").contains(e.target)) $("ctx").hidden = true; });

  function askName(title, initial) {
    return new Promise((resolve) => {
      const m = $("modal"), inp = $("modalInput");
      $("modalTitle").textContent = title;
      inp.value = initial || "";
      m.hidden = false;
      setTimeout(() => { inp.focus(); inp.select(); }, 0);
      const done = (v) => { m.hidden = true; inp.onkeydown = null; resolve(v ? v.trim() : null); };
      $("modalOk").onclick = () => done(inp.value);
      $("modalCancel").onclick = () => done(null);
      inp.onkeydown = (e) => { if (e.key === "Enter") done(inp.value); if (e.key === "Escape") done(null); };
    });
  }

  // ayar kaydırıcıları
  function buildSliders() {
    const box = $("sliders");
    box.textContent = "";
    for (const [key, label, lo, hi] of S.init.sliders) {
      const row = document.createElement("div");
      row.className = "slider";
      row.innerHTML = `<label></label><output></output><input type="range">`;
      row.querySelector("label").textContent = label;
      const inp = row.querySelector("input"), out = row.querySelector("output");
      Object.assign(inp, { min: lo, max: hi, step: SLIDER_STEP[key] || 0.01 });
      inp.dataset.key = key;
      inp.oninput = () => {
        const v = parseFloat(inp.value);
        S.prof.settings[key] = v;
        paintSlider(inp, out);
        api.set_setting(key, v, false);
      };
      inp.onchange = () => { api.set_setting(key, parseFloat(inp.value), true); inp.blur(); };
      box.appendChild(row);
    }
  }
  function paintSlider(inp, out) {
    const p = ((inp.value - inp.min) / (inp.max - inp.min)) * 100;
    inp.style.setProperty("--p", p + "%");
    out.textContent = fmt(inp.dataset.key, parseFloat(inp.value));
  }
  function loadSliders() {
    for (const inp of $("sliders").querySelectorAll("input")) {
      const k = inp.dataset.key;
      inp.value = S.prof.settings[k] ?? S.init.defaults[k];
      paintSlider(inp, inp.parentElement.querySelector("output"));
    }
    $("settingsProfile").textContent = S.prof.active + " profili";
  }

  // tuş ataması
  function buildAssign() {
    const box = $("assign"), key = S.sel;
    box.textContent = "";
    $("assign").parentElement.classList.toggle("disabled", !S.mapped.has(key));
    for (const [gname, items] of S.init.groups) {
      const grp = document.createElement("div");
      grp.className = "grp";
      grp.innerHTML = `<div class="grp-title"></div><div class="chips"></div>`;
      grp.querySelector(".grp-title").textContent = gname;
      const chips = grp.querySelector(".chips");
      for (const [out, name] of items) {
        const keys = S.prof.bindings[out] || [];
        const on = keys.includes(key);
        const others = keys.filter((k) => k !== key).map(tileName);
        const b = document.createElement("button");
        b.className = "chip" + (on ? " on" : "");
        b.dataset.out = out;
        b.innerHTML = `<span class="tag"></span><span class="nm"><b></b><small></small></span>`;
        b.querySelector(".tag").textContent = S.init.short[out] || out;
        b.querySelector("b").textContent = name.replace(/\s{2,}/g, " ");
        b.querySelector("small").textContent = others.length ? "ayrıca: " + others.join(", ") : on ? "yalnız bu tuş" : "atanmamış";
        b.onclick = async () => {
          S.prof.bindings = await api.set_binding(key, out, !on);
          kb.setBindings(bindMap());
          buildAssign();
        };
        chips.appendChild(b);
      }
      box.appendChild(grp);
    }
  }

  function selectKey(label) {
    S.sel = label;
    const mapped = S.mapped.has(label);
    $("keytileLbl").textContent = tileName(label);
    $("keytile").classList.toggle("small", tileName(label).length > 3);
    const hint = $("selHint");
    hint.textContent = mapped ? "Seçili tuş" : "Haritalanmamış tuş · key_mapper_gui.py ile haritala";
    hint.classList.toggle("warn", !mapped);
    kb.setSelected(label);
    buildAssign();
  }

  function applyProfile(p) {
    S.prof = p;
    buildTabs();
    loadSliders();
    kb.setBindings(bindMap());
    buildAssign();
    $("blockSwitch").setAttribute("aria-checked", String(!!p.block));
    $("vpMeta").textContent = `${p.active} profili · ${S.mapped.size} tuş haritalı`;
  }

  function liveOuts(d) {
    const s = new Set(d.pressed), t = 0.08;
    if (d.ly > t) s.add("ls_up"); if (d.ly < -t) s.add("ls_down"); if (d.lx < -t) s.add("ls_left"); if (d.lx > t) s.add("ls_right");
    if (d.ry > t) s.add("rs_up"); if (d.ry < -t) s.add("rs_down"); if (d.rx < -t) s.add("rs_left"); if (d.rx > t) s.add("rs_right");
    if (d.lt > 0.05) s.add("lt"); if (d.rt > 0.05) s.add("rt");
    return s;
  }

  async function poll() {
    try {
      const s = await api.get_state();
      S.values = s.values || {};
      S.display = s.display;
      for (const [k, v] of Object.entries(S.values)) if (v > (S.peaks[k] || 0)) S.peaks[k] = v;
      const st = $("status");
      st.dataset.level = s.status.level;
      st.querySelector("span").textContent = s.status.text;
      if (s.active !== S.active) {
        S.active = s.active;
        const b = $("activateBtn");
        b.classList.toggle("on", s.active);
        b.querySelector(".txt").textContent = s.active ? "DEVRE DIŞI BIRAK" : "GAMEPAD'İ AKTİF ET";
      }
      if (S.prof && s.profile_rev !== S.prof.rev) applyProfile(await api.get_profile());
    } catch (e) {
      console.error(e);
    }
    setTimeout(poll, 16);
  }

  let lastLive = "";
  function uiFrame() {
    const d = S.display, st = S.prof.settings;
    drawStick($("stickL"), d.lx, d.ly, st.deadzone);
    drawStick($("stickR"), d.rx, d.ry, st.deadzone);
    $("stickLv").textContent = `${d.lx >= 0 ? "+" : ""}${d.lx.toFixed(2)} ${d.ly >= 0 ? "+" : ""}${d.ly.toFixed(2)}`;
    $("stickRv").textContent = `${d.rx >= 0 ? "+" : ""}${d.rx.toFixed(2)} ${d.ry >= 0 ? "+" : ""}${d.ry.toFixed(2)}`;
    $("ltBar").style.width = d.lt * 100 + "%"; $("ltVal").textContent = Math.round(d.lt * 100) + "%";
    $("rtBar").style.width = d.rt * 100 + "%"; $("rtVal").textContent = Math.round(d.rt * 100) + "%";
    const pressed = new Set(d.pressed);
    for (const el of $("btnGrid").children) el.classList.toggle("on", pressed.has(el.dataset.out));

    const k = S.sel, raw = S.values[k] || 0, r = ratio(k), pk = S.peaks[k] || 0;
    $("selRaw").textContent = "Ham " + Math.round(raw);
    $("selPct").textContent = Math.round(r * 100) + "%";
    $("selPeak").textContent = Math.round(pk);
    $("keytile").style.transform = `translateY(${r * 5}px)`;
    drawTravel($("travel"), r, pk / amax(), st);
    drawCurve($("curve"), r, st);

    const live = liveOuts(d), sig = [...live].sort().join();
    if (sig !== lastLive) {
      lastLive = sig;
      for (const ch of $("assign").querySelectorAll(".chip")) ch.classList.toggle("live", live.has(ch.dataset.out));
    }
  }

  async function start(a) {
    api = a;
    try {
      S.init = await api.get_init();
    } catch (e) {
      toast("Başlatılamadı: " + e);
      return;
    }
    S.mapped = new Set(S.init.mapped);
    kb = new Keyboard3D($("kb3d"), S.init.layout, S.mapped, selectKey);

    for (const id of S.init.buttons) {
      const c = document.createElement("div");
      c.className = "bchip"; c.dataset.out = id; c.textContent = S.init.short[id] || id;
      $("btnGrid").appendChild(c);
    }
    buildSliders();
    applyProfile(S.init.profile);
    selectKey(S.mapped.has("W") ? "W" : S.init.mapped[0]);

    $("activateBtn").onclick = async () => {
      const res = await api.toggle_active();
      if (res !== "ok") toast(res);
    };
    $("blockSwitch").onclick = async () => {
      const want = !S.prof.block;
      const res = await api.set_block(want);
      S.prof.block = res === "ok" ? want : false;
      $("blockSwitch").setAttribute("aria-checked", String(S.prof.block));
      if (res !== "ok") toast(res);
      else toast(want ? "BLOK açık: atanmış tuşlar oyuna gitmez (gamepad aktifken)." : "BLOK kapalı.", true);
    };
    $("peakMaxBtn").onclick = () => {
      const v = Math.max(S.peaks[S.sel] || 0, S.values[S.sel] || 0);
      if (v <= 0) return toast("Önce bu tuşa sonuna kadar bas.", true);
      S.prof.settings.analog_max = v;
      api.set_setting("analog_max", v, true);
      loadSliders();
    };
    $("peakResetBtn").onclick = () => { S.peaks[S.sel] = 0; };

    poll();
    let last = performance.now();
    const loop = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      if (!document.hidden) { kb.frame(dt, now / 1000); uiFrame(); }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  // Oyun tuşları (boşluk, enter, oklar) arayüzde düğmeye/kaydırıcıya basmasın
  document.addEventListener("keydown", (e) => {
    if (e.target && e.target.id === "modalInput") return;
    if (e.key === "Escape") $("ctx").hidden = true;
    e.preventDefault();
  }, true);
  document.addEventListener("contextmenu", (e) => e.preventDefault());

  let booted = false;
  const boot = (a) => { if (!booted) { booted = true; start(a); } };
  window.addEventListener("pywebviewready", () => boot(window.pywebview.api));
  if (window.pywebview && window.pywebview.api && window.pywebview.api.get_init) boot(window.pywebview.api);
  // Demo verisi sadece düz tarayıcıda (pywebview yokken) kullanılır
  setTimeout(() => { if (!booted && !window.pywebview) boot(makeMockApi()); }, 1500);
})();
