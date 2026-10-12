# -*- coding: utf-8 -*-
"""
Attack Shark R85 HE - Studio (3D arayuz)

Wootility tarzi, 3D klavyeli yeni arayuz. Arayuz ui/ klasorundeki HTML/CSS/JS (three.js) ile
cizilir, pencereyi pywebview acar (Windows'taki Edge WebView2 motoru).
Mantik (HID okuma, sanal Xbox kolu, profiller, BLOK) gamepad_studio.py'den gelir; bu dosya onu
Tkinter'dan bagimsiz bir motora sarar. Ikisi AYNI klasorde durmali.
Ayarlar ayni gamepad_profiles.json dosyasini kullanir, yani eski ayarlarin aynen gelir.

Gerekenler: key_config.json, ViGEmBus, vgamepad, pywinusb, pywebview.
"""

import copy
import ctypes
import json
import os
import sys
import threading
import time
import traceback

import webview

import gamepad_studio as gs

APP_NAME = "R85 HE Studio"
DEVICE_NAME = "Attack Shark R85 HE"

if getattr(sys, "frozen", False):
    UI_DIR = os.path.join(sys._MEIPASS, "ui")
else:
    UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")

LOOP_HZ = 120


def _keys(*labels):
    return [(lbl, 1, "key") for lbl in labels]


# Attack Shark R85 HE fiziksel yerlesimi (%75). (etiket, genislik, tur)
# Etiketler key_config.json'daki isimlerle ayni. Not: eski X68 haritasindan dolayi
# 2. siradaki ` tusu "ESC", alt siradaki Ctrl tusu "RALT" adiyla kayitli; arayuz gercek
# yazisini gosterir. F sirasi: F_ESC=0, Fn=6*n (olculerek dogrulandi).
GAP = (None, 0.5, "gap")
R85_LAYOUT = [
    [("F_ESC", 1, "key"), GAP] + _keys("F1", "F2", "F3", "F4") + [GAP]
    + _keys("F5", "F6", "F7", "F8") + [GAP] + _keys("F9", "F10", "F11", "F12")
    + [GAP, ("LOGO", 1, "logo"), ("KNOB", 0, "knob")],
    _keys("ESC", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=")
    + [("BKSP", 2, "key"), ("DEL", 1, "key")],
    [("TAB", 1.5, "key")] + _keys("Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]")
    + [("\\", 1.5, "key"), ("PGUP", 1, "key")],
    [("CAPS", 1.75, "key")] + _keys("A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'")
    + [("ENTER", 2.25, "key"), ("PGDN", 1, "key")],
    [("LSHIFT", 2.25, "key")] + _keys("Z", "X", "C", "V", "B", "N", "M", ",", ".", "/")
    + [("RSHIFT", 1.75, "key"), ("UP", 1, "key"), (None, 1, "gap")],
    [("LCTRL", 1.25, "key"), ("WIN", 1.25, "key"), ("LALT", 1.25, "key"), ("SPACE", 6.25, "key"),
     ("FN", 1, "key"), ("RALT", 1, "key"), (None, 1, "gap")] + _keys("LEFT", "DOWN", "RIGHT"),
]


class Engine:
    """Klavyeyi okur, sanal kolu besler, profilleri yonetir. Arayuzden bagimsiz calisir."""

    # gamepad_studio.GamepadStudio'nun arayuzden bagimsiz metotlari aynen kullanilir
    _send_feature = gs.GamepadStudio._send_feature
    _hid_handler = gs.GamepadStudio._hid_handler
    _refresh_block_set = gs.GamepadStudio._refresh_block_set

    def __init__(self, key_mapping):
        self.key_mapping = key_mapping
        self.kb_state = gs.KeyboardState(key_mapping)
        self.profiles, self.active_name = gs.load_profiles()
        self.block_keys = gs.load_block_flag()
        self.lock = threading.RLock()

        self.running = True
        self.active = False
        self.gamepad = None
        self.opened_devices = []
        self.config_path = None
        self.all_paths = []
        self.blocker = gs.KeyBlocker()

        self.display = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0,
                        "lt": 0.0, "rt": 0.0, "pressed": []}
        self.status = ("BAĞLANTI YOK", "err")
        self.flash = None              # (metin, seviye, bitis_zamani)
        self.profile_rev = 0           # profil motor tarafinda degisince artar (arayuz yeniler)
        self._pn_prev = False
        self._pp_prev = False

        self._init_hid()
        self._refresh_block_set()
        self.save()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    # ── profil erisimi ───────────────────────────────────────────────
    @property
    def profile(self):
        return self.profiles[self.active_name]

    @property
    def bindings(self):
        return self.profile["bindings"]

    @property
    def settings(self):
        return self.profile["settings"]

    # ── HID ──────────────────────────────────────────────────────────
    def _init_hid(self):
        try:
            devices = gs.hid.find_all_hid_devices()
        except Exception:
            traceback.print_exc()
            devices = []
        kbd_devs = [d for d in devices if d.vendor_id == gs.VID and d.product_id == gs.PID]
        self.all_paths = [d.device_path for d in kbd_devs]
        for d in kbd_devs:
            if "mi_01" in d.device_path.lower():
                self.config_path = d.device_path
        for d in kbd_devs:
            try:
                d.open()
                d.set_raw_data_handler(self._hid_handler)
                self.opened_devices.append(d)
            except Exception as e:
                print("ACILAMADI:", d.device_path, "->", e)
        if self.opened_devices:
            self.status = ("R85 HE BAĞLI", "warn")
        else:
            self.status = ("KLAVYE BULUNAMADI", "err")

    # ── ana dongu (~120 Hz) ──────────────────────────────────────────
    def _loop(self):
        period = 1.0 / LOOP_HZ
        nxt = time.perf_counter()
        while self.running:
            try:
                with self.lock:
                    val = gs.output_value
                    pn = val(self.kb_state, self.bindings, self.settings, "profile_next") > 0.5
                    pp = val(self.kb_state, self.bindings, self.settings, "profile_prev") > 0.5
                    if pn and not self._pn_prev:
                        self._cycle_profile(+1)
                    elif pp and not self._pp_prev:
                        self._cycle_profile(-1)
                    self._pn_prev, self._pp_prev = pn, pp
                    if self.active and self.gamepad:
                        self.display = self.gamepad.update(self.kb_state, self.bindings,
                                                           self.settings)
            except Exception:
                traceback.print_exc()
            nxt += period
            delay = nxt - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            else:
                nxt = time.perf_counter()

    # ── profiller ────────────────────────────────────────────────────
    def switch_profile(self, name):
        with self.lock:
            if name not in self.profiles:
                return False
            self.active_name = name
            if self.active and self.gamepad:
                self.gamepad.reset()
            self._refresh_block_set()
            self.profile_rev += 1
            self.save()
            if self.active:
                self.flash = ("PROFİL: %s" % name, "info", time.time() + 1.2)
            return True

    def _cycle_profile(self, step):
        names = list(self.profiles)
        idx = (names.index(self.active_name) + step) % len(names)
        self.switch_profile(names[idx])

    def new_profile(self, name):
        with self.lock:
            name = (name or "").strip()
            if not name:
                return None
            while name in self.profiles:
                name += " 2"
            self.profiles[name] = copy.deepcopy(self.profile)
            self.switch_profile(name)
            return name

    def rename_profile(self, old, new):
        with self.lock:
            new = (new or "").strip()
            if not new or old not in self.profiles or new == old:
                return "ok"
            if new in self.profiles:
                return "Bu isimde bir profil zaten var."
            self.profiles = {(new if k == old else k): v for k, v in self.profiles.items()}
            if self.active_name == old:
                self.active_name = new
            self.profile_rev += 1
            self.save()
            return "ok"

    def delete_profile(self, name):
        with self.lock:
            if len(self.profiles) <= 1:
                return "Son profil silinemez."
            if name not in self.profiles:
                return "ok"
            del self.profiles[name]
            if self.active_name == name or self.active_name not in self.profiles:
                self.switch_profile(next(iter(self.profiles)))
            else:
                self.profile_rev += 1
                self.save()
            return "ok"

    # ── atama ve ayarlar ─────────────────────────────────────────────
    def set_binding(self, key, out, on):
        with self.lock:
            lst = self.bindings.setdefault(out, [])
            if on and key not in lst:
                lst.append(key)
            elif not on and key in lst:
                lst.remove(key)
            self._refresh_block_set()
            self.save()

    def set_setting(self, key, value, persist=False):
        with self.lock:
            if key in gs.DEFAULT_SETTINGS:
                self.settings[key] = float(value)
            if persist:
                self.save()

    def save(self):
        try:
            with self.lock:
                data = {"version": 1, "active": self.active_name, "profiles": self.profiles,
                        "block_keys": bool(self.block_keys)}
                text = json.dumps(data, indent=2, ensure_ascii=False)
            with open(gs.PROFILES_PATH, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            print("Kaydedilemedi:", e)

    # ── BLOK ─────────────────────────────────────────────────────────
    def _apply_block_state(self):
        if self.block_keys and self.active:
            self._refresh_block_set()
            if self.blocker.start():
                self.blocker.enabled = True
                return "ok"
            self.block_keys = False
            self.blocker.stop()
            return "Tuş engelleme başlatılamadı."
        self.blocker.stop()
        return "ok"

    def set_block(self, on):
        with self.lock:
            self.block_keys = bool(on)
            res = self._apply_block_state()
            self.save()
            return res

    # ── aktif / pasif ────────────────────────────────────────────────
    def toggle_active(self):
        with self.lock:
            if self.active:
                self._deactivate()
                return "ok"
            return self._activate()

    def _activate(self):
        if not self._send_feature(gs.ENABLE_CMD):
            self.status = ("ANALOG MOD AÇILAMADI", "err")
            return "Klavyede analog mod açılamadı. Klavye takılı mı?"
        try:
            self.gamepad = gs.VirtualGamepad()
        except Exception as e:
            self.status = ("ViGEm HATASI", "err")
            return "Sanal kol oluşturulamadı (ViGEmBus kurulu mu?):\n%s" % e
        self.active = True
        self.status = ("GAMEPAD AKTİF", "ok")
        res = self._apply_block_state()
        return res

    def _deactivate(self):
        self.active = False
        self.blocker.stop()
        self._send_feature(gs.DISABLE_CMD)
        if self.gamepad:
            try:
                self.gamepad.reset()
                del self.gamepad.pad
            except Exception as e:
                print("Kol kapatilirken hata:", e)
            self.gamepad = None
        self.display = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0,
                        "lt": 0.0, "rt": 0.0, "pressed": []}
        self.status = ("GAMEPAD KAPALI", "warn")

    # ── arayuz icin anlik durum ──────────────────────────────────────
    def snapshot(self):
        with self.kb_state.lock:
            values = dict(self.kb_state.values)
        status = self.status
        if self.flash and time.time() < self.flash[2]:
            status = self.flash[:2]
        d = self.display
        return {
            "values": values,
            "display": {"lx": d["lx"], "ly": d["ly"], "rx": d["rx"], "ry": d["ry"],
                        "lt": d["lt"], "rt": d["rt"], "pressed": list(d["pressed"])},
            "active": self.active,
            "status": {"text": status[0], "level": status[1]},
            "profile_rev": self.profile_rev,
            "active_name": self.active_name,
        }

    def profile_data(self):
        with self.lock:
            return {
                "names": list(self.profiles),
                "active": self.active_name,
                "bindings": copy.deepcopy(self.bindings),
                "settings": dict(self.settings),
                "block": bool(self.block_keys),
                "rev": self.profile_rev,
            }

    def shutdown(self):
        self.running = False
        try:
            with self.lock:
                if self.active:
                    self._deactivate()
                self.blocker.stop()
            self.save()
        except Exception:
            traceback.print_exc()
        for d in self.opened_devices:
            try:
                d.close()
            except Exception:
                pass


class Api:
    """JavaScript'in cagirdigi fonksiyonlar (window.pywebview.api.*).
    Alt cizgiyle baslayan alanlar JS'e acilmaz."""

    def __init__(self, engine):
        self._engine = engine

    def get_init(self):
        e = self._engine
        return {
            "app": APP_NAME,
            "device": DEVICE_NAME,
            "layout": [[[lbl, w, kind] for lbl, w, kind in row] for row in R85_LAYOUT],
            "mapped": list(e.key_mapping),
            "groups": [[g, [[o, n] for o, n in items]] for g, items in gs.OUTPUT_GROUPS],
            "short": gs.SHORT,
            "buttons": gs.BUTTON_IDS,
            "sliders": [[k, lbl, lo, hi] for k, lbl, lo, hi in gs.SLIDERS],
            "defaults": gs.DEFAULT_SETTINGS,
            "profile": e.profile_data(),
        }

    def get_state(self):
        return self._engine.snapshot()

    def get_profile(self):
        return self._engine.profile_data()

    def switch_profile(self, name):
        self._engine.switch_profile(name)
        return self._engine.profile_data()

    def new_profile(self, name):
        self._engine.new_profile(name)
        return self._engine.profile_data()

    def rename_profile(self, old, new):
        res = self._engine.rename_profile(old, new)
        return {"result": res, "profile": self._engine.profile_data()}

    def delete_profile(self, name):
        res = self._engine.delete_profile(name)
        return {"result": res, "profile": self._engine.profile_data()}

    def set_binding(self, key, out, on):
        self._engine.set_binding(key, out, bool(on))
        return self._engine.profile_data()["bindings"]

    def set_setting(self, key, value, persist=False):
        self._engine.set_setting(key, value, bool(persist))
        return True

    def toggle_active(self):
        return self._engine.toggle_active()

    def set_block(self, on):
        return self._engine.set_block(on)


def message_box(title, text):
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
    except Exception:
        print(title, text)


def main():
    try:
        with open(gs.KEY_CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        key_mapping = {k: int(v) for k, v in cfg["key_mapping"].items()}
    except Exception as e:
        message_box("key_config.json",
                    "key_config.json okunamadı:\n%s\n\nÖnce key_mapper_gui.py ile tuşları haritala." % e)
        return

    engine = Engine(key_mapping)
    api = Api(engine)
    window = webview.create_window(
        APP_NAME, url=os.path.join(UI_DIR, "index.html"), js_api=api,
        width=1440, height=880, min_size=(1240, 780), background_color="#07060d",
    )
    window.events.closing += engine.shutdown
    webview.start(debug="--debug" in sys.argv)
    engine.shutdown()


if __name__ == "__main__":
    main()
