# -*- coding: utf-8 -*-
"""
X68PRO HE - Gamepad Studio  (Wootility tarzi atama arayuzu)

Klavyedeki her Hall-effect tusu, Xbox 360 / PS5 tipi kolun herhangi bir girisine atayabilirsin:
  - Sol / sag cubuk yonleri (analog)
  - LT / RT tetikleri (analog)  = PS5 L2 / R2
  - A B X Y, LB RB, L3 R3, Start, Back, Guide, D-Pad
Bir tus birden fazla girise, bir giris birden fazla tusa atanabilir.
Profiller: Walk / Drive / istedigin kadar ekle. Profil degistirmek icin bir tusa
"Sonraki profil" / "Onceki profil" ata (oyunda kullanmadigin bir tus sec).

Gerekenler: key_config.json (key_mapper_gui.py ile olusturulur), ViGEmBus, vgamepad, pywinusb.
Ayarlar gamepad_profiles.json dosyasina kaydedilir. Eski virtual_gamepad.py aynen calismaya devam eder.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import vgamepad as vg
import pywinusb.hid as hid
import ctypes
import threading
import time
import json
import os
import math
import sys
import copy
import traceback
try:
    from ctypes import wintypes
except Exception:      # Windows disi ortamda sadece test icin
    wintypes = None

if getattr(sys, "frozen", False):          # PyInstaller ile exe yapildiysa: ayarlar exe'nin yaninda durur
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_CONFIG_PATH = os.path.join(BASE_DIR, "key_config.json")
OLD_CONFIG_PATH = os.path.join(BASE_DIR, "gamepad_config.json")
PROFILES_PATH = os.path.join(BASE_DIR, "gamepad_profiles.json")

VID = 0x3151
PID = 0x5029
ENABLE_CMD = [0x1B, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xE3] + [0x00] * 56
DISABLE_CMD = [0x1B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xE4] + [0x00] * 56

hid_dll = ctypes.WinDLL('hid.dll')
kernel32 = ctypes.WinDLL('kernel32.dll')
user32 = ctypes.WinDLL('user32.dll')

# ── Renkler ─────────────────────────────────────────────────────────
BG = "#1a1a2e"
PANEL = "#16213e"
KEY_BASE = "#2a2a4e"
KEY_HOT = "#00dd77"

# ── Kol cikislari ────────────────────────────────────────────────────
OUTPUT_GROUPS = [
    ("SOL ÇUBUK (analog)", [
        ("ls_up", "LS Yukarı"), ("ls_down", "LS Aşağı"),
        ("ls_left", "LS Sol"), ("ls_right", "LS Sağ"),
    ]),
    ("SAĞ ÇUBUK (analog)", [
        ("rs_up", "RS Yukarı"), ("rs_down", "RS Aşağı"),
        ("rs_left", "RS Sol"), ("rs_right", "RS Sağ"),
    ]),
    ("TETİKLER (analog)", [
        ("lt", "LT   (PS5: L2)"), ("rt", "RT   (PS5: R2)"),
    ]),
    ("BUTONLAR", [
        ("a", "A   (PS5: Cross)"), ("b", "B   (PS5: Circle)"),
        ("x", "X   (PS5: Square)"), ("y", "Y   (PS5: Triangle)"),
        ("lb", "LB  (PS5: L1)"), ("rb", "RB  (PS5: R1)"),
        ("l3", "L3  (sol çubuğa bas)"), ("r3", "R3  (sağ çubuğa bas)"),
        ("start", "Start (PS5: Options)"), ("back", "Back  (PS5: Create)"),
        ("guide", "Guide (PS tuşu)"),
    ]),
    ("D-PAD", [
        ("dpad_up", "D-Pad Yukarı"), ("dpad_down", "D-Pad Aşağı"),
        ("dpad_left", "D-Pad Sol"), ("dpad_right", "D-Pad Sağ"),
    ]),
    ("UYGULAMA", [
        ("profile_next", "Sonraki profil"), ("profile_prev", "Önceki profil"),
    ]),
]

SHORT = {
    "ls_up": "LS↑", "ls_down": "LS↓", "ls_left": "LS←", "ls_right": "LS→",
    "rs_up": "RS↑", "rs_down": "RS↓", "rs_left": "RS←", "rs_right": "RS→",
    "lt": "LT", "rt": "RT", "a": "A", "b": "B", "x": "X", "y": "Y",
    "lb": "LB", "rb": "RB", "l3": "L3", "r3": "R3",
    "start": "STR", "back": "BCK", "guide": "GDE",
    "dpad_up": "D↑", "dpad_down": "D↓", "dpad_left": "D←", "dpad_right": "D→",
    "profile_next": "P+", "profile_prev": "P-",
}

BUTTON_IDS = ["a", "b", "x", "y", "lb", "rb", "l3", "r3", "start", "back", "guide",
              "dpad_up", "dpad_down", "dpad_left", "dpad_right"]

DEFAULT_SETTINGS = {
    "deadzone": 0.05,
    "smoothing": 0.30,
    "sensitivity_curve": 1.0,
    "button_threshold": 0.15,
    "analog_max": 350.0,
}

SLIDERS = [
    ("deadzone", "Deadzone", 0.0, 0.5),
    ("smoothing", "Smoothing", 0.0, 0.95),
    ("sensitivity_curve", "Sensitivity", 0.2, 3.0),
    ("button_threshold", "Button actuation", 0.05, 0.8),
    ("analog_max", "Analog Max", 100.0, 500.0),
]

# X68 Pro HE yerlesimi (key_mapper_gui.py ile ayni)
KEYBOARD_LAYOUT = [
    [("ESC", 1), ("1", 1), ("2", 1), ("3", 1), ("4", 1), ("5", 1), ("6", 1),
     ("7", 1), ("8", 1), ("9", 1), ("0", 1), ("-", 1), ("=", 1), ("BKSP", 2), ("DEL", 1)],
    [("TAB", 1.5), ("Q", 1), ("W", 1), ("E", 1), ("R", 1), ("T", 1), ("Y", 1),
     ("U", 1), ("I", 1), ("O", 1), ("P", 1), ("[", 1), ("]", 1), ("\\", 1.5), ("PGUP", 1)],
    [("CAPS", 1.75), ("A", 1), ("S", 1), ("D", 1), ("F", 1), ("G", 1), ("H", 1),
     ("J", 1), ("K", 1), ("L", 1), (";", 1), ("'", 1), ("ENTER", 2.25), ("PGDN", 1)],
    [("LSHIFT", 2.25), ("Z", 1), ("X", 1), ("C", 1), ("V", 1), ("B", 1), ("N", 1),
     ("M", 1), (",", 1), (".", 1), ("/", 1), ("RSHIFT", 1.75), ("UP", 1)],
    [("LCTRL", 1.25), ("WIN", 1.25), ("LALT", 1.25), ("SPACE", 6.25),
     ("RALT", 1), ("FN", 1), ("LEFT", 1), ("DOWN", 1), ("RIGHT", 1)],
]
KEY_LABELS = [lbl for row in KEYBOARD_LAYOUT for lbl, _ in row]


# ═════════════════════════════════════════════════════════════════════
#  Yardimci fonksiyonlar
# ═════════════════════════════════════════════════════════════════════

def blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class KeyboardState:
    """Tum tuslarin analog degerlerini tutar."""

    def __init__(self, key_mapping):
        self.key_mapping = key_mapping            # label -> key_id
        self.id_to_key = {v: k for k, v in key_mapping.items()}
        self.values = {}
        self.lock = threading.Lock()

    def update(self, key_id, analog_value):
        label = self.id_to_key.get(key_id)
        if label:
            with self.lock:
                self.values[label] = analog_value

    def get(self, label):
        with self.lock:
            return self.values.get(label, 0)

    def get_normalized(self, label, settings):
        raw = self.get(label)
        max_val = float(settings.get("analog_max", 350.0)) or 350.0
        n = min(1.0, raw / max_val)
        dz = float(settings.get("deadzone", 0.05))
        if n < dz:
            return 0.0
        n = (n - dz) / (1.0 - dz) if dz < 1.0 else 0.0
        curve = float(settings.get("sensitivity_curve", 1.0))
        if curve != 1.0:
            n = math.pow(n, curve)
        return min(1.0, max(0.0, n))


def output_value(kb, bindings, settings, out):
    """Bir kol girisine atanmis tuslarin en buyuk normalize degeri (0-1)."""
    best = 0.0
    for k in bindings.get(out) or ():
        v = kb.get_normalized(k, settings)
        if v > best:
            best = v
    return best


class SmoothedAxis:
    def __init__(self):
        self.value = 0.0

    def update(self, target, smoothing):
        if smoothing <= 0:
            self.value = target
        else:
            self.value += (target - self.value) * (1.0 - smoothing)
        return self.value


class VirtualGamepad:
    """ViGEm Xbox 360 sanal kolu. Her guncellemede TUM girisleri atamalardan hesaplar."""

    def __init__(self):
        self.pad = vg.VX360Gamepad()
        self.axes = {n: SmoothedAxis() for n in ("lx", "ly", "rx", "ry", "lt", "rt")}
        X = vg.XUSB_BUTTON
        self.button_map = {
            "a": X.XUSB_GAMEPAD_A, "b": X.XUSB_GAMEPAD_B,
            "x": X.XUSB_GAMEPAD_X, "y": X.XUSB_GAMEPAD_Y,
            "lb": X.XUSB_GAMEPAD_LEFT_SHOULDER, "rb": X.XUSB_GAMEPAD_RIGHT_SHOULDER,
            "l3": X.XUSB_GAMEPAD_LEFT_THUMB, "r3": X.XUSB_GAMEPAD_RIGHT_THUMB,
            "start": X.XUSB_GAMEPAD_START, "back": X.XUSB_GAMEPAD_BACK,
            "guide": X.XUSB_GAMEPAD_GUIDE,
            "dpad_up": X.XUSB_GAMEPAD_DPAD_UP, "dpad_down": X.XUSB_GAMEPAD_DPAD_DOWN,
            "dpad_left": X.XUSB_GAMEPAD_DPAD_LEFT, "dpad_right": X.XUSB_GAMEPAD_DPAD_RIGHT,
        }
        self.pressed = set()

    @staticmethod
    def _clamp_circle(x, y):
        mag = math.sqrt(x * x + y * y)
        if mag > 1.0:
            return x / mag, y / mag
        return x, y

    def update(self, kb, bindings, settings):
        sm = float(settings.get("smoothing", 0.3))
        thr = float(settings.get("button_threshold", 0.15))

        def val(out):
            return output_value(kb, bindings, settings, out)

        lx_raw, ly_raw = self._clamp_circle(val("ls_right") - val("ls_left"),
                                            val("ls_up") - val("ls_down"))
        rx_raw, ry_raw = self._clamp_circle(val("rs_right") - val("rs_left"),
                                            val("rs_up") - val("rs_down"))
        lx = self.axes["lx"].update(lx_raw, sm)
        ly = self.axes["ly"].update(ly_raw, sm)
        rx = self.axes["rx"].update(rx_raw, sm)
        ry = self.axes["ry"].update(ry_raw, sm)
        lt = self.axes["lt"].update(val("lt"), sm)
        rt = self.axes["rt"].update(val("rt"), sm)

        self.pad.left_joystick_float(x_value_float=lx, y_value_float=ly)
        self.pad.right_joystick_float(x_value_float=rx, y_value_float=ry)
        self.pad.left_trigger_float(value_float=lt)
        self.pad.right_trigger_float(value_float=rt)

        now_pressed = set()
        for out in BUTTON_IDS:
            if val(out) > thr:
                now_pressed.add(out)
        # Karsit D-Pad yonleri birbirini iptal etsin
        if "dpad_up" in now_pressed and "dpad_down" in now_pressed:
            now_pressed -= {"dpad_up", "dpad_down"}
        if "dpad_left" in now_pressed and "dpad_right" in now_pressed:
            now_pressed -= {"dpad_left", "dpad_right"}

        for out in BUTTON_IDS:
            if out in now_pressed and out not in self.pressed:
                self.pad.press_button(button=self.button_map[out])
            elif out not in now_pressed and out in self.pressed:
                self.pad.release_button(button=self.button_map[out])
        self.pressed = now_pressed

        self.pad.update()
        return {"lx": lx, "ly": ly, "rx": rx, "ry": ry, "lt": lt, "rt": rt,
                "pressed": sorted(now_pressed)}

    def reset(self):
        for a in self.axes.values():
            a.value = 0.0
        self.pressed = set()
        self.pad.reset()
        self.pad.update()


# ═════════════════════════════════════════════════════════════════════
#  Tus engelleyici (istege bagli): atanmis tuslari oyuna gonderme
# ═════════════════════════════════════════════════════════════════════

VK_BY_LABEL = {
    "BKSP": 0x08, "TAB": 0x09, "ENTER": 0x0D, "CAPS": 0x14, "ESC": 0x1B, "SPACE": 0x20,
    "PGUP": 0x21, "PGDN": 0x22, "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    "DEL": 0x2E, "WIN": 0x5B, "LSHIFT": 0xA0, "RSHIFT": 0xA1, "LCTRL": 0xA2,
    "LALT": 0xA4, "RALT": 0xA5,
    ";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD, ".": 0xBE, "/": 0xBF,
    "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}
# Guvenlik: bu tuslar ASLA engellenmez (Alt+Tab, Alt+F4, Win tusu hep calisir)
BLOCK_EXEMPT = {0x5B, 0xA4, 0xA5}


def vk_for_label(label):
    if label in VK_BY_LABEL:
        return VK_BY_LABEL[label]
    if len(label) == 1 and label.isalpha():
        return ord(label.upper())
    if len(label) == 1 and label.isdigit():
        return ord(label)
    return None


class KeyBlocker:
    """WH_KEYBOARD_LL ile secili tuslarin oyuna ulasmasini engeller.
    Uygulama klavyeyi HID uzerinden dogrudan okudugu icin etkilenmez.
    Sadece kendi penceren on plandayken ve enjekte edilmemis tuslarda calisir."""

    def __init__(self):
        self.vks = frozenset()
        self.enabled = False
        self.blocked_down = set()
        self.thread = None
        self.thread_id = None
        self.hook = None
        self._proc = None
        self.ready = threading.Event()
        self.pid = os.getpid()

    def _own_foreground(self):
        try:
            pid = wintypes.DWORD(0)
            user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
            return pid.value == self.pid
        except Exception:
            return False

    def should_block(self, vk, is_up, injected):
        """True donerse tus oyuna gitmez. Basilma engellendiyse birakma da engellenir
        (tus oyunda takili kalmasin), basilma gecirildiyse birakma da gecer."""
        if not self.enabled or injected:
            return False
        if is_up:
            if vk in self.blocked_down:
                self.blocked_down.discard(vk)
                return True
            return False
        if (vk in self.vks or vk in self.blocked_down) and not self._own_foreground():
            self.blocked_down.add(vk)
            return True
        return False

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            return self.hook is not None
        self.hook = None
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.ready.wait(2.0)
        return self.hook is not None

    def _run(self):
        try:
            LRESULT = ctypes.c_ssize_t
            HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t)

            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [("vkCode", ctypes.c_ulong), ("scanCode", ctypes.c_ulong),
                            ("flags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                            ("dwExtraInfo", ctypes.c_size_t)]

            user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, ctypes.c_ulong]
            user32.SetWindowsHookExW.restype = ctypes.c_void_p
            user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]
            user32.CallNextHookEx.restype = LRESULT
            user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
            user32.GetForegroundWindow.restype = ctypes.c_void_p
            user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
            user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), ctypes.c_void_p,
                                           ctypes.c_uint, ctypes.c_uint]
            kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
            kernel32.GetModuleHandleW.restype = ctypes.c_void_p

            def hook_proc(nCode, wParam, lParam):
                try:
                    if nCode >= 0 and self.enabled:
                        info = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                        is_up = wParam in (0x101, 0x105)          # WM_KEYUP / WM_SYSKEYUP
                        injected = bool(info.flags & 0x10)        # LLKHF_INJECTED
                        if self.should_block(info.vkCode, is_up, injected):
                            return 1
                except Exception:
                    pass
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            self._proc = HOOKPROC(hook_proc)
            self.thread_id = kernel32.GetCurrentThreadId()
            self.hook = user32.SetWindowsHookExW(13, self._proc, kernel32.GetModuleHandleW(None), 0)
            self.ready.set()
            if not self.hook:
                print("Klavye kancasi kurulamadi, hata:", kernel32.GetLastError())
                return
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                pass
            user32.UnhookWindowsHookEx(self.hook)
        except Exception:
            traceback.print_exc()
        finally:
            self.hook = None
            self.ready.set()

    def stop(self):
        self.enabled = False
        t = self.thread
        if t is not None and t.is_alive() and self.thread_id:
            for _ in range(20):                      # WM_QUIT gonder, thread kapanana kadar dene
                try:
                    user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
                except Exception:
                    break
                t.join(0.05)
                if not t.is_alive():
                    break
        self.thread = None
        self.blocked_down.clear()


# ═════════════════════════════════════════════════════════════════════
#  Profil dosyasi
# ═════════════════════════════════════════════════════════════════════

def default_full_bindings():
    return {
        "ls_up": ["W"], "ls_down": ["S"], "ls_left": ["A"], "ls_right": ["D"],
        "rs_up": ["I"], "rs_down": ["K"], "rs_left": ["J"], "rs_right": ["L"],
        "a": ["SPACE"], "b": ["LSHIFT"], "x": ["E"], "y": ["Q"],
        "lb": ["TAB"], "rb": ["R"], "lt": ["LCTRL"], "rt": ["F"],
        "dpad_up": ["UP"], "dpad_down": ["DOWN"], "dpad_left": ["LEFT"], "dpad_right": ["RIGHT"],
        "start": ["ENTER"], "back": ["ESC"], "l3": ["C"], "r3": ["V"],
    }


def build_initial_profiles():
    """Ilk acilis: eski gamepad_config.json varsa ondan al, yoksa varsayilanlari kullan."""
    old_b, old_s = {}, {}
    if os.path.exists(OLD_CONFIG_PATH):
        try:
            with open(OLD_CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            old_b = cfg.get("bindings", {}) or {}
            old_s = cfg.get("settings", {}) or {}
        except Exception as e:
            print("Eski ayar okunamadi:", e)

    settings = dict(DEFAULT_SETTINGS)
    for k_old, k_new in (("deadzone", "deadzone"), ("smoothing", "smoothing"),
                         ("sensitivity_curve", "sensitivity_curve"),
                         ("button_threshold", "button_threshold"),
                         ("analog_max_override", "analog_max")):
        if k_old in old_s:
            try:
                settings[k_new] = float(old_s[k_old])
            except (TypeError, ValueError):
                pass

    ls = {
        "ls_up": [old_b.get("left_stick_up", "W")],
        "ls_down": [old_b.get("left_stick_down", "S")],
        "ls_left": [old_b.get("left_stick_left", "A")],
        "ls_right": [old_b.get("left_stick_right", "D")],
    }
    drive = dict(copy.deepcopy(ls))
    drive["rt"] = [old_b.get("drive_gas", "W")]
    drive["lt"] = [old_b.get("drive_brake", "S")]
    full = default_full_bindings()
    full.update(copy.deepcopy(ls))

    return {
        "Walk": {"bindings": copy.deepcopy(ls), "settings": dict(settings)},
        "Drive": {"bindings": drive, "settings": dict(settings)},
        "Full controller": {"bindings": full, "settings": dict(settings)},
    }


def load_profiles():
    data = None
    if os.path.exists(PROFILES_PATH):
        try:
            with open(PROFILES_PATH, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("Profil dosyasi okunamadi:", e)
    if data and isinstance(data.get("profiles"), dict) and data["profiles"]:
        profiles = {}
        for name, p in data["profiles"].items():
            b = {k: [str(x) for x in v] for k, v in (p.get("bindings") or {}).items()
                 if isinstance(v, list)}
            s = {**DEFAULT_SETTINGS, **(p.get("settings") or {})}
            profiles[name] = {"bindings": b, "settings": s}
        active = data.get("active")
        if active not in profiles:
            active = next(iter(profiles))
        return profiles, active
    return build_initial_profiles(), "Walk"


def load_block_flag():
    try:
        with open(PROFILES_PATH, encoding="utf-8") as f:
            return bool(json.load(f).get("block_keys", False))
    except Exception:
        return False


# ═════════════════════════════════════════════════════════════════════
#  Uygulama
# ═════════════════════════════════════════════════════════════════════

class GamepadStudio:
    U = 48       # 1 tus birimi (piksel)
    KH = 46      # tus yuksekligi
    GAP = 4

    def __init__(self, root, key_mapping):
        self.root = root
        self.root.title("X68PRO HE - Gamepad Studio")
        self.root.geometry("1220x740")
        self.root.configure(bg=BG)

        self.running = True
        self.active = False
        self.gamepad = None
        self.opened_devices = []
        self.config_path = None
        self.all_paths = []

        self.key_mapping = key_mapping
        self.kb_state = KeyboardState(key_mapping)
        self.profiles, self.active_name = load_profiles()

        self.selected_key = None
        self.display = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0,
                        "lt": 0.0, "rt": 0.0, "pressed": []}
        self._pn_prev = False
        self._pp_prev = False
        self._loading = False
        self.key_last_color = {}
        self.key_items = {}
        self.out_vars = {}
        self.blocker = KeyBlocker()

        self._build_ui()
        self._init_hid()
        self._apply_profile_to_ui()
        first = "W" if "W" in self.key_mapping else (
            next(iter(self.key_mapping), KEY_LABELS[0]))
        self._select_key(first)
        self._save()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._gamepad_loop()
        self._ui_loop()

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

    # ── arayuz ───────────────────────────────────────────────────────
    def _build_ui(self):
        # Oyun tuslari (bosluk/enter) odaktaki dugmeleri tetiklemesin
        self.root.bind_all('<space>', lambda e: 'break')
        self.root.bind_all('<Return>', lambda e: 'break')

        # Ust cubuk
        top = tk.Frame(self.root, bg=PANEL)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))

        self.status_label = tk.Label(top, text="DISCONNECTED",
                                     font=("Consolas", 12, "bold"), fg="#ff4444", bg=PANEL)
        self.status_label.pack(side=tk.LEFT, padx=10, pady=8)

        tk.Label(top, text="Profil:", font=("Consolas", 10, "bold"),
                 fg="#ccc", bg=PANEL).pack(side=tk.LEFT, padx=(20, 4))
        self.profile_var = tk.StringVar(value=self.active_name)
        self.profile_combo = ttk.Combobox(top, textvariable=self.profile_var,
                                          values=list(self.profiles), width=18,
                                          state="readonly", font=("Consolas", 10))
        self.profile_combo.pack(side=tk.LEFT)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)
        self.profile_combo.bind("<MouseWheel>", lambda e: "break")

        for text, cmd in (("Yeni", self._new_profile),
                          ("Yeniden adlandır", self._rename_profile),
                          ("Sil", self._delete_profile)):
            tk.Button(top, text=text, command=cmd, font=("Consolas", 9),
                      bg="#2a2a4e", fg="white").pack(side=tk.LEFT, padx=3)

        self.toggle_btn = tk.Button(top, text="ACTIVATE GAMEPAD",
                                    font=("Consolas", 11, "bold"), bg="#00aa55", fg="white",
                                    command=self._toggle_active, width=20)
        self.toggle_btn.pack(side=tk.RIGHT, padx=10, pady=8)

        # Ana alan
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left = tk.Frame(main, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Klavye
        kf = tk.LabelFrame(left, text=" KLAVYE  (bir tuşa tıkla, sağdan kol girişini seç) ",
                           font=("Consolas", 10, "bold"), fg="#00ccff", bg=PANEL)
        kf.pack(fill=tk.X)
        U, KH, GAP = self.U, self.KH, self.GAP
        self.keys_canvas = tk.Canvas(kf, width=16 * U + 6, height=5 * (KH + GAP) + 6,
                                     bg=PANEL, highlightthickness=0)
        self.keys_canvas.pack(padx=6, pady=6)
        c = self.keys_canvas
        for r, row in enumerate(KEYBOARD_LAYOUT):
            x = 0.0
            for label, wu in row:
                x0 = x * U + 3
                x1 = (x + wu) * U - 1
                y0 = r * (KH + GAP) + 3
                y1 = y0 + KH
                rect = c.create_rectangle(x0, y0, x1, y1, fill=KEY_BASE,
                                          outline="#3a3a6e", width=2)
                cx = (x0 + x1) / 2
                mapped = label in self.key_mapping
                t1 = c.create_text(cx, y0 + 14, text=label,
                                   fill="#dddddd" if mapped else "#555555",
                                   font=("Consolas", 9, "bold"))
                t2 = c.create_text(cx, y1 - 13, text="", fill="#00ccff",
                                   font=("Consolas", 8, "bold"))
                for item in (rect, t1, t2):
                    c.tag_bind(item, "<Button-1>", lambda e, k=label: self._select_key(k))
                self.key_items[label] = (rect, t1, t2)
                x += wu

        # Onizleme + ayarlar
        pv = tk.LabelFrame(left, text=" ÖNİZLEME & AYARLAR ",
                           font=("Consolas", 10, "bold"), fg="#00ccff", bg=PANEL)
        pv.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        c1 = tk.Frame(pv, bg=PANEL)
        c1.pack(side=tk.LEFT, padx=8, pady=6)
        tk.Label(c1, text="SOL ÇUBUK", font=("Consolas", 9, "bold"),
                 fg="#888", bg=PANEL).pack()
        self.left_canvas = tk.Canvas(c1, width=150, height=150, bg="#0a0a1a",
                                     highlightthickness=0)
        self.left_canvas.pack(pady=3)
        self.ls_label = tk.Label(c1, text="X:+0.00  Y:+0.00", font=("Consolas", 9),
                                 fg="#00ff88", bg=PANEL)
        self.ls_label.pack()

        c2 = tk.Frame(pv, bg=PANEL)
        c2.pack(side=tk.LEFT, padx=8, pady=6)
        tk.Label(c2, text="SAĞ ÇUBUK", font=("Consolas", 9, "bold"),
                 fg="#888", bg=PANEL).pack()
        self.right_canvas = tk.Canvas(c2, width=150, height=150, bg="#0a0a1a",
                                      highlightthickness=0)
        self.right_canvas.pack(pady=3)
        self.rs_label = tk.Label(c2, text="X:+0.00  Y:+0.00", font=("Consolas", 9),
                                 fg="#00ff88", bg=PANEL)
        self.rs_label.pack()

        c3 = tk.Frame(pv, bg=PANEL)
        c3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=6)

        trig = tk.Frame(c3, bg=PANEL)
        trig.pack(fill=tk.X)
        tk.Label(trig, text="LT", font=("Consolas", 9, "bold"), fg="#888",
                 bg=PANEL).pack(side=tk.LEFT)
        self.lt_bar = tk.Canvas(trig, height=16, bg="#0a0a1a", highlightthickness=0)
        self.lt_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.rt_bar = tk.Canvas(trig, height=16, bg="#0a0a1a", highlightthickness=0)
        self.rt_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        tk.Label(trig, text="RT", font=("Consolas", 9, "bold"), fg="#888",
                 bg=PANEL).pack(side=tk.LEFT)

        self.btn_label = tk.Label(c3, text="Butonlar: ---", font=("Consolas", 9),
                                  fg="#ffcc00", bg=PANEL, anchor=tk.W, justify=tk.LEFT,
                                  wraplength=380)
        self.btn_label.pack(fill=tk.X, pady=(6, 4))

        sf = tk.Frame(c3, bg=PANEL)
        sf.pack(fill=tk.X)
        self.slider_widgets = {}
        for r, (key, label, lo, hi) in enumerate(SLIDERS):
            lab = tk.Label(sf, text="", font=("Consolas", 9), fg="#ccc", bg=PANEL,
                           width=24, anchor=tk.W)
            lab.grid(row=r, column=0, sticky="w")
            sc = ttk.Scale(sf, from_=lo, to=hi, orient=tk.HORIZONTAL, length=170,
                           command=lambda v, k=key: self._on_slider(k, v))
            sc.grid(row=r, column=1, padx=4, pady=2)
            sc.bind("<ButtonRelease-1>", lambda e: self._save())
            self.slider_widgets[key] = (sc, lab, label)

        # Sag panel: secili tus -> kol girisleri
        right = tk.LabelFrame(main, text=" TUŞ ATAMASI ", font=("Consolas", 10, "bold"),
                              fg="#00ccff", bg=PANEL, width=340)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0))
        right.pack_propagate(False)

        self.sel_label = tk.Label(right, text="Seçili tuş: -", font=("Consolas", 12, "bold"),
                                  fg="#ffcc00", bg=PANEL)
        self.sel_label.pack(pady=(8, 0))
        self.raw_label = tk.Label(right, text="Ham değer: ---", font=("Consolas", 9),
                                  fg="#00ff88", bg=PANEL)
        self.raw_label.pack(pady=(0, 4))
        tk.Label(right, text="Bu tuşun bastığı kol girişlerini işaretle:",
                 font=("Consolas", 8), fg="#999", bg=PANEL).pack()

        cont = tk.Frame(right, bg=PANEL)
        cont.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.list_canvas = tk.Canvas(cont, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(cont, orient=tk.VERTICAL, command=self.list_canvas.yview)
        inner = tk.Frame(self.list_canvas, bg=PANEL)
        win = self.list_canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        inner.bind("<Configure>",
                   lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.bind("<Configure>",
                              lambda e: self.list_canvas.itemconfigure(win, width=e.width))
        self.list_canvas.configure(yscrollcommand=sb.set)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.root.bind_all("<MouseWheel>", self._on_wheel)

        for gname, items in OUTPUT_GROUPS:
            tk.Label(inner, text=gname, font=("Consolas", 9, "bold"), fg="#00ccff",
                     bg=PANEL, anchor=tk.W).pack(fill=tk.X, pady=(8, 1))
            for out_id, out_name in items:
                var = tk.BooleanVar(value=False)
                cb = tk.Checkbutton(inner, text=out_name, variable=var,
                                    command=lambda o=out_id: self._on_toggle(o),
                                    font=("Consolas", 9), fg="#dddddd", bg=PANEL,
                                    activebackground=PANEL, activeforeground="#ffffff",
                                    selectcolor="#0a0a1a", anchor=tk.W)
                cb.pack(fill=tk.X)
                self.out_vars[out_id] = var

        tk.Button(right, text="KAYDET", font=("Consolas", 10, "bold"), bg="#2266cc",
                  fg="white", command=self._save).pack(fill=tk.X, padx=8, pady=8)

        self.block_var = tk.BooleanVar(value=load_block_flag())
        tk.Checkbutton(self.root,
                       text="BLOK: bu profilde atanmış tuşları oyuna gönderme "
                            "(Forza için; GTA Online'da kapalı tut)",
                       variable=self.block_var, command=self._on_block_toggle,
                       font=("Consolas", 9, "bold"), fg="#ffcc00", bg=BG,
                       activebackground=BG, activeforeground="#ffcc00",
                       selectcolor="#0a0a1a", anchor=tk.W
                       ).pack(fill=tk.X, padx=12)
        tk.Label(self.root,
                 text="Not: BLOK kapalıyken uygulama klavye girişini engellemez. Oyunun klavye atamalarında "
                      "burada kullandığın tuşları boşalt / başka tuşa taşı.",
                 font=("Consolas", 8), fg="#777", bg=BG, anchor=tk.W
                 ).pack(fill=tk.X, padx=12, pady=(0, 6))

    def _on_wheel(self, e):
        try:
            w = self.root.winfo_containing(e.x_root, e.y_root)
        except Exception:
            return
        while w is not None:
            if w is self.list_canvas:
                self.list_canvas.yview_scroll(int(-e.delta / 120), "units")
                return
            w = getattr(w, "master", None)

    # ── tus secimi ve atama ──────────────────────────────────────────
    def _select_key(self, label):
        self.selected_key = label
        mapped = label in self.key_mapping
        self.sel_label.config(text=f"Seçili tuş: {label}" + ("" if mapped else "  (haritalanmamış)"))
        for out, var in self.out_vars.items():
            var.set(label in (self.bindings.get(out) or []))
        self._refresh_key_visuals()

    def _on_toggle(self, out):
        key = self.selected_key
        if not key:
            return
        lst = self.bindings.setdefault(out, [])
        if self.out_vars[out].get():
            if key not in lst:
                lst.append(key)
        else:
            if key in lst:
                lst.remove(key)
        self._refresh_key_visuals()
        self._save()

    def _refresh_key_visuals(self):
        assigned = {}
        for out, keys in self.bindings.items():
            for k in keys:
                assigned.setdefault(k, []).append(out)
        for label, (rect, t1, t2) in self.key_items.items():
            outs = assigned.get(label, [])
            txt = " ".join(SHORT.get(o, o) for o in outs[:2]) + ("+" if len(outs) > 2 else "")
            self.keys_canvas.itemconfig(t2, text=txt)
            if label == self.selected_key:
                self.keys_canvas.itemconfig(rect, outline="#ffcc00", width=3)
            elif outs:
                self.keys_canvas.itemconfig(rect, outline="#00aa66", width=2)
            else:
                self.keys_canvas.itemconfig(rect, outline="#3a3a6e", width=2)
        self._refresh_block_set()

    def _refresh_block_set(self):
        vks = set()
        for keys in self.bindings.values():
            for k in keys:
                vk = vk_for_label(k)
                if vk and vk not in BLOCK_EXEMPT:
                    vks.add(vk)
        self.blocker.vks = frozenset(vks)

    def _apply_block_state(self):
        if self.block_var.get() and self.active:
            self._refresh_block_set()
            if self.blocker.start():
                self.blocker.enabled = True
            else:
                self.block_var.set(False)
                self.blocker.stop()
                messagebox.showwarning("BLOK", "Tuş engelleme başlatılamadı. "
                                               "Komut penceresindeki mesaja bak.")
        else:
            self.blocker.stop()

    def _on_block_toggle(self):
        self._apply_block_state()
        self._save()

    # ── ayar kaydiricilari ───────────────────────────────────────────
    def _slider_text(self, key, label, value):
        if key == "analog_max":
            return f"{label}: {value:.0f}"
        return f"{label}: {value:.2f}"

    def _on_slider(self, key, value):
        sc, lab, label = self.slider_widgets[key]
        v = float(value)
        lab.config(text=self._slider_text(key, label, v))
        if not self._loading:
            self.settings[key] = v

    def _load_sliders(self):
        self._loading = True
        try:
            for key, (sc, lab, label) in self.slider_widgets.items():
                v = float(self.settings.get(key, DEFAULT_SETTINGS[key]))
                sc.set(v)
                lab.config(text=self._slider_text(key, label, v))
        finally:
            self._loading = False

    # ── profiller ────────────────────────────────────────────────────
    def _apply_profile_to_ui(self):
        self.profile_combo.config(values=list(self.profiles))
        self.profile_var.set(self.active_name)
        self._load_sliders()
        if self.selected_key:
            for out, var in self.out_vars.items():
                var.set(self.selected_key in (self.bindings.get(out) or []))
        self._refresh_key_visuals()

    def _switch_profile(self, name):
        if name not in self.profiles:
            return
        self.active_name = name
        if self.active and self.gamepad:
            self.gamepad.reset()
        self._apply_profile_to_ui()
        self._save()
        if self.active:
            self.status_label.config(text=f"PROFIL: {name}", fg="#00ccff")
            self.root.after(1200, self._restore_status)

    def _restore_status(self):
        if self.active:
            self.status_label.config(text="GAMEPAD ACTIVE", fg="#00ff88")

    def _cycle_profile(self, step):
        names = list(self.profiles)
        idx = (names.index(self.active_name) + step) % len(names)
        self._switch_profile(names[idx])

    def _on_profile_selected(self, event=None):
        self._switch_profile(self.profile_var.get())

    def _ask_name(self, title, initial=""):
        name = simpledialog.askstring(title, "Profil adı:", parent=self.root,
                                      initialvalue=initial)
        return name.strip() if name else None

    def _new_profile(self):
        name = self._ask_name("Yeni profil")
        if not name:
            return
        while name in self.profiles:
            name += " 2"
        self.profiles[name] = copy.deepcopy(self.profile)   # mevcut profilin kopyasi
        self._switch_profile(name)

    def _rename_profile(self):
        old = self.active_name
        name = self._ask_name("Yeniden adlandır", initial=old)
        if not name or name == old:
            return
        if name in self.profiles:
            messagebox.showerror("Hata", "Bu isimde bir profil zaten var.")
            return
        self.profiles = {(name if k == old else k): v for k, v in self.profiles.items()}
        self.active_name = name
        self._apply_profile_to_ui()
        self._save()

    def _delete_profile(self):
        if len(self.profiles) <= 1:
            messagebox.showinfo("Bilgi", "Son profil silinemez.")
            return
        if not messagebox.askyesno("Sil", f"'{self.active_name}' profili silinsin mi?"):
            return
        del self.profiles[self.active_name]
        self._switch_profile(next(iter(self.profiles)))

    def _save(self):
        try:
            data = {"version": 1, "active": self.active_name, "profiles": self.profiles,
                    "block_keys": bool(self.block_var.get())}
            with open(PROFILES_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Kaydedilemedi:", e)

    # ── HID ──────────────────────────────────────────────────────────
    def _init_hid(self):
        devices = hid.find_all_hid_devices()
        kbd_devs = [d for d in devices if d.vendor_id == VID and d.product_id == PID]

        print("kbd_devs sayisi:", len(kbd_devs))
        self.all_paths = []
        for d in kbd_devs:
            print("  yol:", d.device_path)
            self.all_paths.append(d.device_path)

        for d in kbd_devs:
            if 'mi_01' in d.device_path.lower():
                self.config_path = d.device_path

        for d in kbd_devs:
            try:
                d.open()
                d.set_raw_data_handler(self._hid_handler)
                self.opened_devices.append(d)
                print("ACILDI:", d.device_path)
            except Exception as e:
                print("ACILAMADI:", d.device_path, "->", e)

        if self.opened_devices:
            self.status_label.config(text=f"HID OK ({len(self.opened_devices)} ifaces)",
                                     fg="#ffcc00")
        else:
            self.status_label.config(text="HID ERROR", fg="#ff4444")

    def _send_feature(self, cmd):
        candidates = []
        if self.config_path:
            candidates.append(self.config_path)
        for p in self.all_paths:
            if p not in candidates:
                candidates.append(p)

        if not candidates:
            print("SEND_FEATURE: hic HID yolu yok (klavye bulunamadi)")
            return False

        kernel32.CreateFileW.restype = ctypes.c_void_p
        kernel32.CreateFileW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong,
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
        ]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        hid_dll.HidD_SetFeature.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        hid_dll.HidD_SetFeature.restype = ctypes.c_ubyte

        buf = (ctypes.c_ubyte * 65)()
        buf[0] = 0
        for i in range(64):
            buf[i + 1] = cmd[i] & 0xFF

        INVALID = ctypes.c_void_p(-1).value

        for path in candidates:
            for access in (0xC0000000, 0x40000000, 0x00000000):
                h = kernel32.CreateFileW(path, access, 0x03, None, 3, 0, None)
                if h is None or h == INVALID:
                    err = kernel32.GetLastError()
                    print(f"CreateFile basarisiz (erisim={hex(access)}, hata={err}): {path}")
                    continue
                r = hid_dll.HidD_SetFeature(h, ctypes.byref(buf), 65)
                err = kernel32.GetLastError()
                kernel32.CloseHandle(h)
                if r:
                    print(f"SetFeature BASARILI: {path} (erisim={hex(access)})")
                    self.config_path = path
                    return True
                print(f"SetFeature basarisiz (erisim={hex(access)}, hata={err}): {path}")
        return False

    def _hid_handler(self, data):
        if len(data) < 5 or data[0] != 5 or data[1] != 0x1B:
            return
        analog = data[2] + data[3] * 256
        key_id = data[4]
        self.kb_state.update(key_id, analog)

    # ── aktif / pasif ────────────────────────────────────────────────
    def _toggle_active(self):
        if self.active:
            self._deactivate()
        else:
            self._activate()

    def _activate(self):
        if not self._send_feature(ENABLE_CMD):
            print("ENABLE FAILED: yukaridaki CreateFile/SetFeature satirlarina bak")
            self.status_label.config(text="ENABLE FAILED", fg="#ff4444")
            return
        try:
            self.gamepad = VirtualGamepad()
        except Exception as e:
            self.status_label.config(text=f"ViGEm ERROR: {e}", fg="#ff4444")
            return
        self.active = True
        self.status_label.config(text="GAMEPAD ACTIVE", fg="#00ff88")
        self.toggle_btn.config(text="DEACTIVATE", bg="#cc2222")
        self._apply_block_state()

    def _deactivate(self):
        self.active = False
        self.blocker.stop()
        self._send_feature(DISABLE_CMD)
        if self.gamepad:
            try:
                self.gamepad.reset()
                del self.gamepad.pad
            except Exception as e:
                print("Kol kapatilirken hata:", e)
            self.gamepad = None
        self.status_label.config(text="GAMEPAD OFF", fg="#ffcc00")
        self.toggle_btn.config(text="ACTIVATE GAMEPAD", bg="#00aa55")

    # ── donguler ─────────────────────────────────────────────────────
    def _gamepad_loop(self):
        if not self.running:
            return
        try:
            pn = output_value(self.kb_state, self.bindings, self.settings, "profile_next") > 0.5
            pp = output_value(self.kb_state, self.bindings, self.settings, "profile_prev") > 0.5
            if pn and not self._pn_prev:
                self._cycle_profile(+1)
            elif pp and not self._pp_prev:
                self._cycle_profile(-1)
            self._pn_prev, self._pp_prev = pn, pp

            if self.active and self.gamepad:
                self.display = self.gamepad.update(self.kb_state, self.bindings, self.settings)
        except Exception:
            traceback.print_exc()
        self.root.after(8, self._gamepad_loop)     # ~120 Hz

    def _ui_loop(self):
        if not self.running:
            return
        try:
            amax = float(self.settings.get("analog_max", 350.0)) or 350.0
            for label, (rect, t1, t2) in self.key_items.items():
                if label not in self.key_mapping:
                    continue
                ratio = min(1.0, self.kb_state.get(label) / amax)
                col = blend(KEY_BASE, KEY_HOT, ratio) if ratio > 0.02 else KEY_BASE
                if self.key_last_color.get(label) != col:
                    self.key_last_color[label] = col
                    self.keys_canvas.itemconfig(rect, fill=col)

            if self.selected_key:
                v = self.kb_state.get(self.selected_key)
                self.raw_label.config(text=f"Ham değer: {v:3d}  ({min(100, v * 100 // int(amax))}%)")

            d = self.display
            self._draw_stick(self.left_canvas, d["lx"], d["ly"])
            self._draw_stick(self.right_canvas, d["rx"], d["ry"])
            self.ls_label.config(text=f"X:{d['lx']:+.2f}  Y:{d['ly']:+.2f}")
            self.rs_label.config(text=f"X:{d['rx']:+.2f}  Y:{d['ry']:+.2f}")
            self._draw_trigger(self.lt_bar, d["lt"])
            self._draw_trigger(self.rt_bar, d["rt"])
            names = [SHORT.get(o, o) for o in d["pressed"]]
            self.btn_label.config(text="Butonlar: " + (" ".join(names) if names else "---"))
        except Exception:
            traceback.print_exc()
        self.root.after(33, self._ui_loop)

    def _draw_stick(self, canvas, x, y):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10:
            return
        cx, cy = w / 2, h / 2
        r = min(cx, cy) - 10
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#333355", width=2)
        canvas.create_line(cx - r, cy, cx + r, cy, fill="#222244")
        canvas.create_line(cx, cy - r, cx, cy + r, fill="#222244")
        dz = float(self.settings.get("deadzone", 0.05))
        dz_r = r * dz
        canvas.create_oval(cx - dz_r, cy - dz_r, cx + dz_r, cy + dz_r,
                           outline="#442222", width=1, dash=(2, 2))
        dx = cx + x * r
        dy = cy - y * r
        dot_r = 8
        mag = math.sqrt(x ** 2 + y ** 2)
        if mag > 0.01:
            intensity = min(255, int(mag * 255))
            color = f'#{intensity:02X}{max(0, 255 - intensity):02X}00'
        else:
            color = '#00ff88'
        canvas.create_oval(dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r,
                           fill=color, outline="white", width=2)

    def _draw_trigger(self, canvas, value):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10:
            return
        intensity = min(255, int(value * 255))
        color = f'#{intensity:02X}{max(0, 200 - intensity):02X}00'
        canvas.create_rectangle(0, 0, int(value * w), h, fill=color)

    def _on_close(self):
        self.running = False
        self._save()
        self.blocker.stop()
        if self.active:
            self._deactivate()
        for d in self.opened_devices:
            try:
                d.close()
            except Exception:
                pass
        self.root.destroy()


def main():
    try:
        with open(KEY_CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        key_mapping = {k: int(v) for k, v in cfg["key_mapping"].items()}
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("key_config.json",
                             f"key_config.json okunamadı:\n{e}\n\n"
                             "Önce key_mapper_gui.py ile tuşları haritala.")
        return
    root = tk.Tk()
    GamepadStudio(root, key_mapping)
    root.mainloop()


if __name__ == '__main__':
    main()
