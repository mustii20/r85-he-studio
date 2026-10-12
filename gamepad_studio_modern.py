# -*- coding: utf-8 -*-
"""
X68PRO HE - Gamepad Studio (Modern arayuz)

Siyah / mor, oyuncu yazilimi gorunumlu yeni arayuz.
Mantik (HID okuma, sanal kol, profiller, ayarlar) gamepad_studio.py'den gelir,
bu dosya sadece gorunumu degistirir. Ikisi AYNI klasorde durmali.
Ayarlar ayni gamepad_profiles.json dosyasini kullanir, yani eski ayarlarin aynen gelir.
"""

import tkinter as tk
from tkinter import ttk
import json
import math
import traceback

import gamepad_studio as gs
from gamepad_studio import (GamepadStudio, KEYBOARD_LAYOUT, OUTPUT_GROUPS, SHORT, SLIDERS,
                            DEFAULT_SETTINGS, BUTTON_IDS, KEY_CONFIG_PATH, blend,
                            load_block_flag)

# ── Tema ────────────────────────────────────────────────────────────
BG0 = "#0a0910"        # pencere
BG1 = "#110f1c"        # kart
BG2 = "#18152a"        # yukseltilmis yuzey
LINE = "#2a2548"
TEXT = "#ece9fb"
MUTED = "#8a86a8"
ACC = "#8b5cf6"
ACC_HI = "#a78bfa"
ACC_NEON = "#c084fc"
ACC_DEEP = "#6d28d9"
PINK = "#e879f9"
OK = "#34d399"
WARN = "#fbbf24"
ERR = "#fb7185"
FONT = "Segoe UI"

KEY_TOP = "#252242"
KEY_SIDE = "#15122a"
KEY_SHADOW = "#06050c"
KEY_EDGE = "#38336a"
KEY_GLOSS = "#4a4580"
KEY_HOT = "#7c3aed"
ASG_EDGE = "#6d4fd6"

SLIDER_STEPS = {"deadzone": 0.01, "smoothing": 0.01, "sensitivity_curve": 0.05,
                "button_threshold": 0.01, "analog_max": 5.0}


# ── Cizim yardimcilari ──────────────────────────────────────────────
def rr_points(x0, y0, x1, y1, r):
    """Yuvarlatilmis dikdortgen noktalari (create_polygon + smooth=True ile kullanilir)."""
    r = max(1.0, min(float(r), (x1 - x0) / 2.0, (y1 - y0) / 2.0))
    return [
        x0 + r, y0, x0 + r, y0, x1 - r, y0, x1 - r, y0,
        x1, y0, x1, y0 + r, x1, y0 + r, x1, y1 - r, x1, y1 - r,
        x1, y1, x1 - r, y1, x1 - r, y1, x0 + r, y1, x0 + r, y1,
        x0, y1, x0, y1 - r, x0, y1 - r, x0, y0 + r, x0, y0 + r,
        x0, y0,
    ]


def rrect(canvas, x0, y0, x1, y1, r, **kw):
    return canvas.create_polygon(rr_points(x0, y0, x1, y1, r), smooth=True, **kw)


def draw_hgradient(canvas, w, h, c1, c2, step=4):
    canvas.delete("all")
    n = max(1, int(w) // step)
    for i in range(n + 1):
        canvas.create_line(i * step, 0, i * step, h, fill=blend(c1, c2, i / n), width=step)


def _toggle_style(text):
    return "danger" if str(text).upper().startswith("DEACT") else "primary"


# ── Ozel bilesenler ─────────────────────────────────────────────────
class FlatButton(tk.Canvas):
    """Yuvarlak, gradyan hissi veren, hover efektli dugme."""

    STYLES = {
        "primary": dict(fill="#7c3aed", hover="#8b5cf6", press="#6d28d9",
                        shadow="#3b1782", fg="#ffffff", edge="#a78bfa"),
        "ghost": dict(fill="#1c1933", hover="#27234a", press="#15122a",
                      shadow="#0b0a16", fg="#d9d5f5", edge="#34305a"),
        "danger": dict(fill="#be123c", hover="#e11d48", press="#9f1239",
                       shadow="#4c0519", fg="#ffffff", edge="#fb7185"),
    }

    def __init__(self, parent, text, command=None, width=120, height=34, style="primary",
                 style_fn=None, font=(FONT, 10, "bold"), bg=BG1, radius=10):
        tk.Canvas.__init__(self, parent, width=width, height=height, bg=bg,
                           highlightthickness=0, bd=0, cursor="hand2")
        self.fb_w = width
        self.fb_h = height
        self.fb_text = text
        self.fb_cmd = command
        self.fb_style = style
        self.fb_style_fn = style_fn
        self.fb_font = font
        self.fb_r = radius
        self.fb_hover = False
        self.fb_down = False
        self.bind("<Enter>", self.fb_enter)
        self.bind("<Leave>", self.fb_leave)
        self.bind("<ButtonPress-1>", self.fb_press)
        self.bind("<ButtonRelease-1>", self.fb_release)
        self.fb_draw()

    def fb_style_name(self):
        if self.fb_style_fn:
            return self.fb_style_fn(self.fb_text)
        return self.fb_style

    def fb_enter(self, e=None):
        self.fb_hover = True
        self.fb_draw()

    def fb_leave(self, e=None):
        self.fb_hover = False
        self.fb_down = False
        self.fb_draw()

    def fb_press(self, e=None):
        self.fb_down = True
        self.fb_draw()

    def fb_release(self, e=None):
        was_down = self.fb_down
        self.fb_down = False
        self.fb_draw()
        inside = e is None or (0 <= e.x <= self.fb_w and 0 <= e.y <= self.fb_h)
        if was_down and inside and self.fb_cmd:
            self.fb_cmd()

    def fb_draw(self):
        self.delete("all")
        st = self.STYLES.get(self.fb_style_name(), self.STYLES["primary"])
        face = st["press"] if self.fb_down else (st["hover"] if self.fb_hover else st["fill"])
        w, h, r = self.fb_w, self.fb_h, self.fb_r
        dy = 2 if self.fb_down else 0
        rrect(self, 1, 4, w - 1, h - 1, r, fill=st["shadow"], outline="")
        rrect(self, 1, 1 + dy, w - 1, h - 4 + dy, r, fill=face, outline=st["edge"], width=1)
        self.create_line(r, 3 + dy, w - r, 3 + dy, fill=blend(face, "#ffffff", 0.22))
        self.create_text(w / 2.0, (h - 3) / 2.0 + dy, text=self.fb_text, fill=st["fg"],
                         font=self.fb_font)

    def config(self, text=None, **kw):
        if text is not None:
            self.fb_text = text
        self.fb_draw()


class StatusPill(tk.Canvas):
    PALETTE = {"#ff4444": ERR, "#ffcc00": WARN, "#00ff88": OK, "#00ccff": ACC_NEON}

    def __init__(self, parent, width=240, height=38, bg=BG0):
        tk.Canvas.__init__(self, parent, width=width, height=height, bg=bg,
                           highlightthickness=0, bd=0)
        self.sp_w = width
        self.sp_h = height
        self.sp_text = "DISCONNECTED"
        self.sp_color = ERR
        self.sp_draw()

    def sp_draw(self):
        self.delete("all")
        w, h = self.sp_w, self.sp_h
        rrect(self, 1, 1, w - 1, h - 1, 12, fill="#13111f", outline=LINE, width=1)
        cy = h / 2.0
        for rad, t in ((9, 0.12), (6.5, 0.28)):
            self.create_oval(22 - rad, cy - rad, 22 + rad, cy + rad,
                             fill=blend("#13111f", self.sp_color, t), outline="")
        self.create_oval(18, cy - 4, 26, cy + 4, fill=self.sp_color, outline="")
        self.create_text(38, cy, text=str(self.sp_text)[:30], anchor="w", fill=TEXT,
                         font=(FONT, 10, "bold"))

    def config(self, text=None, fg=None, **kw):
        if text is not None:
            self.sp_text = text
        if fg is not None:
            self.sp_color = self.PALETTE.get(str(fg).lower(), fg)
        self.sp_draw()


class GlowSlider(tk.Canvas):
    def __init__(self, parent, label, lo, hi, step, fmt, on_change, on_release,
                 width=250, bg=BG1):
        tk.Canvas.__init__(self, parent, width=width, height=34, bg=bg,
                           highlightthickness=0, bd=0, cursor="hand2")
        self.gs_w = width
        self.gs_label = label
        self.gs_lo, self.gs_hi, self.gs_step = lo, hi, step
        self.gs_fmt = fmt
        self.gs_change = on_change
        self.gs_release = on_release
        self.gs_value = lo
        self.gs_pad = 8
        self.bind("<ButtonPress-1>", self.gs_drag)
        self.bind("<B1-Motion>", self.gs_drag)
        self.bind("<ButtonRelease-1>", self.gs_up)
        self.gs_draw()

    def set_value(self, v):
        self.gs_value = max(self.gs_lo, min(self.gs_hi, float(v)))
        self.gs_draw()

    def gs_drag(self, e):
        span = float(self.gs_w - 2 * self.gs_pad)
        ratio = max(0.0, min(1.0, (e.x - self.gs_pad) / span))
        v = self.gs_lo + ratio * (self.gs_hi - self.gs_lo)
        if self.gs_step:
            v = round(v / self.gs_step) * self.gs_step
        v = max(self.gs_lo, min(self.gs_hi, v))
        self.gs_value = v
        self.gs_draw()
        if self.gs_change:
            self.gs_change(v)

    def gs_up(self, e=None):
        if self.gs_release:
            self.gs_release()

    def gs_draw(self):
        self.delete("all")
        w, pad = self.gs_w, self.gs_pad
        self.create_text(pad, 8, text=self.gs_label, anchor="w", fill=MUTED, font=(FONT, 9))
        self.create_text(w - pad, 8, text=self.gs_fmt.format(self.gs_value), anchor="e",
                         fill=ACC_HI, font=(FONT, 9, "bold"))
        ty = 25
        rrect(self, pad, ty - 3, w - pad, ty + 3, 3, fill="#1c1933", outline="")
        ratio = (self.gs_value - self.gs_lo) / float(self.gs_hi - self.gs_lo)
        kx = pad + ratio * (w - 2 * pad)
        if kx > pad + 2:
            rrect(self, pad, ty - 3, kx, ty + 3, 3, fill=ACC, outline="")
        for rad, t in ((11, 0.10), (8.5, 0.22)):
            self.create_oval(kx - rad, ty - rad, kx + rad, ty + rad,
                             fill=blend(BG1, ACC, t), outline="")
        self.create_oval(kx - 6, ty - 6, kx + 6, ty + 6, fill="#ede9fe", outline=ACC, width=2)


class CheckRow(tk.Frame):
    def __init__(self, parent, text, on_click):
        tk.Frame.__init__(self, parent, bg=BG1, cursor="hand2")
        self.cr_on_click = on_click
        self.cr_checked = False
        self.cr_box = tk.Canvas(self, width=20, height=20, bg=BG1, highlightthickness=0, bd=0)
        self.cr_box.pack(side=tk.LEFT, padx=(8, 8), pady=3)
        self.cr_lbl = tk.Label(self, text=text, font=(FONT, 9), fg=TEXT, bg=BG1, anchor="w")
        self.cr_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for w in (self, self.cr_box, self.cr_lbl):
            w.bind("<Button-1>", self.cr_click)
            w.bind("<Enter>", self.cr_enter)
            w.bind("<Leave>", self.cr_leave)
        self.cr_draw()

    def get(self):
        return self.cr_checked

    def set(self, value):
        self.cr_checked = bool(value)
        self.cr_draw()

    def cr_click(self, e=None):
        self.cr_checked = not self.cr_checked
        self.cr_draw()
        self.cr_on_click()

    def cr_paint_bg(self, color):
        self.configure(bg=color)
        self.cr_lbl.configure(bg=color)
        self.cr_box.configure(bg=color)

    def cr_enter(self, e=None):
        self.cr_paint_bg(BG2)

    def cr_leave(self, e=None):
        self.cr_paint_bg(BG1)

    def cr_draw(self):
        c = self.cr_box
        c.delete("all")
        if self.cr_checked:
            rrect(c, 2, 2, 18, 18, 5, fill=ACC, outline=ACC_HI, width=1)
            c.create_line(6, 10, 9, 13, 14, 6, fill="#ffffff", width=2)
            self.cr_lbl.configure(fg="#ffffff")
        else:
            rrect(c, 2, 2, 18, 18, 5, fill=BG0, outline=LINE, width=1)
            self.cr_lbl.configure(fg=TEXT)


class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, var, command, bg=BG0):
        tk.Canvas.__init__(self, parent, width=42, height=22, bg=bg, highlightthickness=0,
                           bd=0, cursor="hand2")
        self.ts_var = var
        self.ts_cmd = command
        self.ts_last = None
        self.bind("<Button-1>", self.ts_click)
        self.ts_draw()

    def ts_click(self, e=None):
        self.ts_var.set(not self.ts_var.get())
        self.ts_draw()
        if self.ts_cmd:
            self.ts_cmd()

    def refresh(self):
        if self.ts_last != bool(self.ts_var.get()):
            self.ts_draw()

    def ts_draw(self):
        self.delete("all")
        on = bool(self.ts_var.get())
        self.ts_last = on
        rrect(self, 1, 2, 41, 20, 9, fill=ACC if on else "#241f40", outline=ACC_HI if on else LINE)
        kx = 31 if on else 11
        self.create_oval(kx - 7, 4, kx + 7, 18, fill="#ede9fe" if on else "#6b6790", outline="")


def ask_text(parent, title, prompt, initial=""):
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=BG1)
    win.resizable(False, False)
    try:
        win.transient(parent)
    except Exception:
        pass
    box = tk.Frame(win, bg=BG1)
    box.pack(padx=22, pady=18)
    tk.Label(box, text=prompt, font=(FONT, 10), fg=TEXT, bg=BG1).pack(anchor="w")
    entry = tk.Entry(box, font=(FONT, 11), width=28, bg=BG0, fg=TEXT, insertbackground=TEXT,
                     relief="flat", highlightthickness=1, highlightbackground=LINE,
                     highlightcolor=ACC)
    entry.pack(pady=(8, 14), ipady=5)
    entry.insert(0, initial)
    result = {"v": None}

    def ok(event=None):
        result["v"] = entry.get().strip()
        win.destroy()

    def cancel(event=None):
        win.destroy()

    row = tk.Frame(box, bg=BG1)
    row.pack(anchor="e")
    FlatButton(row, "İptal", cancel, width=84, height=32, style="ghost", bg=BG1).pack(side=tk.LEFT, padx=4)
    FlatButton(row, "Tamam", ok, width=84, height=32, bg=BG1).pack(side=tk.LEFT, padx=4)
    entry.bind("<Return>", ok)
    win.bind("<Escape>", cancel)
    try:
        win.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_height()) // 3
        win.geometry("+%d+%d" % (px, py))
    except Exception:
        pass
    win.grab_set()
    entry.focus_set()
    entry.select_range(0, tk.END)
    parent.wait_window(win)
    return result["v"] or None


# ── Ana uygulama ────────────────────────────────────────────────────
class ModernStudio(GamepadStudio):
    U = 52
    KH = 48
    GAP = 6

    # -- arayuz kurulumu ---------------------------------------------
    def _build_ui(self):
        root = self.root
        root.title("R85 HE · Gamepad Studio")
        root.geometry("1270x740")
        root.minsize(1190, 700)
        root.configure(bg=BG0)
        self._init_styles()
        self.slider_widgets = {}
        self.chip_items = {}
        self._chips_on = set()

        self._build_header()
        body = tk.Frame(root, bg=BG0)
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(8, 0))

        right_outer, right_inner, _ = self._card(body, "TUŞ ATAMASI")
        right_outer.configure(width=350)
        right_outer.pack_propagate(False)
        right_outer.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        left = tk.Frame(body, bg=BG0)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_keyboard(left)
        self._build_preview(left)
        self._build_assign_panel(right_inner)
        self._build_footer()
        root.bind_all("<MouseWheel>", self._on_wheel)

    def _init_styles(self):
        try:
            st = ttk.Style(self.root)
            try:
                st.theme_use("clam")
            except tk.TclError:
                pass
            st.configure("Dark.Vertical.TScrollbar", background="#2a2548", troughcolor=BG1,
                         bordercolor=BG1, lightcolor="#2a2548", darkcolor="#2a2548",
                         arrowcolor=ACC_HI, gripcount=0)
            st.map("Dark.Vertical.TScrollbar", background=[("active", ACC_DEEP)])
        except Exception:
            traceback.print_exc()

    def _card(self, parent, title):
        outer = tk.Frame(parent, bg=LINE)
        inner = tk.Frame(outer, bg=BG1)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        head = tk.Frame(inner, bg=BG1)
        head.pack(fill=tk.X, padx=12, pady=(10, 0))
        tk.Frame(head, bg=ACC, width=3, height=12).pack(side=tk.LEFT)
        tk.Label(head, text=title, font=(FONT, 9, "bold"), fg=ACC_HI, bg=BG1).pack(side=tk.LEFT, padx=8)
        return outer, inner, head

    def _build_header(self):
        header = tk.Frame(self.root, bg=BG0)
        header.pack(fill=tk.X, padx=14, pady=(12, 6))

        brand = tk.Frame(header, bg=BG0)
        brand.pack(side=tk.LEFT)
        logo = tk.Canvas(brand, width=42, height=42, bg=BG0, highlightthickness=0, bd=0)
        logo.pack(side=tk.LEFT)
        rrect(logo, 2, 5, 40, 40, 11, fill="#3b1782", outline="")
        rrect(logo, 2, 2, 40, 35, 11, fill=ACC, outline=ACC_HI)
        logo.create_line(11, 5, 31, 5, fill=blend(ACC, "#ffffff", 0.35))
        logo.create_text(21, 19, text="G", fill="#ffffff", font=(FONT, 17, "bold"))
        txt = tk.Frame(brand, bg=BG0)
        txt.pack(side=tk.LEFT, padx=10)
        tk.Label(txt, text="GAMEPAD STUDIO", font=(FONT, 13, "bold"), fg=TEXT, bg=BG0).pack(anchor="w")
        tk.Label(txt, text="X68PRO HE  ·  analog → Xbox 360", font=(FONT, 8), fg=MUTED,
                 bg=BG0).pack(anchor="w")

        self.tabs_frame = tk.Frame(header, bg=BG0)
        self.tabs_frame.pack(side=tk.LEFT, padx=(30, 0))

        self.toggle_btn = FlatButton(header, "ACTIVATE GAMEPAD", self._toggle_active, width=190,
                                     height=40, style_fn=_toggle_style, bg=BG0)
        self.toggle_btn.pack(side=tk.RIGHT)
        self.status_label = StatusPill(header, width=240, height=38, bg=BG0)
        self.status_label.pack(side=tk.RIGHT, padx=10)

        glow = tk.Canvas(self.root, height=2, bg=BG0, highlightthickness=0, bd=0)
        glow.pack(fill=tk.X)
        glow.bind("<Configure>", lambda e: draw_hgradient(glow, e.width, 2, ACC_DEEP, BG0))

    def _build_keyboard(self, parent):
        outer, inner, head = self._card(parent, "KLAVYE")
        outer.pack(fill=tk.X)
        tk.Label(head, text="bir tuşa tıkla  ·  ışık = basınç", font=(FONT, 8), fg=MUTED,
                 bg=BG1).pack(side=tk.RIGHT)
        U, KH, GAP = self.U, self.KH, self.GAP
        self.keys_canvas = tk.Canvas(inner, width=16 * U + 8, height=5 * (KH + GAP) + 6,
                                     bg=BG1, highlightthickness=0, bd=0)
        self.keys_canvas.pack(padx=12, pady=(6, 12))
        c = self.keys_canvas
        for r, row in enumerate(KEYBOARD_LAYOUT):
            x = 0.0
            for label, wu in row:
                x0 = x * U + 4
                x1 = (x + wu) * U - 2
                y0 = r * (KH + GAP) + 4
                y1 = y0 + KH
                cx = (x0 + x1) / 2.0
                mapped = label in self.key_mapping
                ids = {}
                ids["shadow"] = rrect(c, x0, y0 + 4, x1, y1 + 2, 9, fill=KEY_SHADOW, outline="")
                ids["side"] = rrect(c, x0, y0 + 2, x1, y1, 9, fill=KEY_SIDE, outline="")
                ids["top"] = rrect(c, x0 + 1, y0, x1 - 1, y1 - 8, 8, fill=KEY_TOP,
                                   outline=KEY_EDGE, width=1)
                ids["gloss"] = c.create_line(x0 + 9, y0 + 2, x1 - 9, y0 + 2, fill=KEY_GLOSS)
                ids["t1"] = c.create_text(cx, y0 + 14, text=label,
                                          fill=TEXT if mapped else "#4a4668",
                                          font=(FONT, 9, "bold"))
                ids["t2"] = c.create_text(cx, y0 + 31, text="", fill=ACC_HI,
                                          font=(FONT, 8, "bold"))
                ids["ring"] = rrect(c, x0 - 2, y0 - 3, x1 + 2, y1 + 3, 11, fill="",
                                    outline=ACC_NEON, width=2, state="hidden")
                for item in ids.values():
                    c.tag_bind(item, "<Button-1>", lambda e, k=label: self._select_key(k))
                self.key_items[label] = {"ids": ids, "geom": (x0, y0, x1, y1, cx),
                                         "sel": False, "asg": False, "sig": None}
                x += wu

    def _build_preview(self, parent):
        outer, inner, _ = self._card(parent, "ÖNİZLEME & AYAR")
        outer.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        row = tk.Frame(inner, bg=BG1)
        row.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 10))

        def stick_col(title):
            col = tk.Frame(row, bg=BG1)
            col.pack(side=tk.LEFT, padx=(0, 14))
            tk.Label(col, text=title, font=(FONT, 8, "bold"), fg=MUTED, bg=BG1).pack()
            cv = tk.Canvas(col, width=150, height=150, bg=BG1, highlightthickness=0, bd=0)
            cv.pack(pady=2)
            lb = tk.Label(col, text="X +0.00   Y +0.00", font=("Consolas", 9), fg=ACC_HI, bg=BG1)
            lb.pack()
            return cv, lb

        self.left_canvas, self.ls_label = stick_col("SOL ÇUBUK")
        self.right_canvas, self.rs_label = stick_col("SAĞ ÇUBUK")

        mid = tk.Frame(row, bg=BG1)
        mid.pack(side=tk.LEFT, padx=(0, 14))
        tk.Label(mid, text="TETİKLER", font=(FONT, 8, "bold"), fg=MUTED, bg=BG1).pack(anchor="w")
        self.trig_canvas = tk.Canvas(mid, width=270, height=30, bg=BG1, highlightthickness=0, bd=0)
        self.trig_canvas.pack(pady=(2, 8))
        tk.Label(mid, text="BUTONLAR", font=(FONT, 8, "bold"), fg=MUTED, bg=BG1).pack(anchor="w")
        self.chip_canvas = tk.Canvas(mid, width=272, height=90, bg=BG1, highlightthickness=0, bd=0)
        self.chip_canvas.pack(pady=(2, 0))
        cc = self.chip_canvas
        for i, out in enumerate(BUTTON_IDS):
            x0 = (i % 5) * 54 + 1
            y0 = (i // 5) * 29 + 2
            rect = rrect(cc, x0, y0, x0 + 50, y0 + 25, 8, fill=BG2, outline=LINE, width=1)
            txt = cc.create_text(x0 + 25, y0 + 13, text=SHORT.get(out, out), fill=MUTED,
                                 font=(FONT, 8, "bold"))
            self.chip_items[out] = (rect, txt)

        sf = tk.Frame(row, bg=BG1)
        sf.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(sf, text="AYARLAR", font=(FONT, 8, "bold"), fg=MUTED, bg=BG1).pack(anchor="w")
        for key, label, lo, hi in SLIDERS:
            fmt = "{:.0f}" if key == "analog_max" else "{:.2f}"
            sl = GlowSlider(sf, label, lo, hi, SLIDER_STEPS.get(key, 0.01), fmt,
                            on_change=lambda v, k=key: self._on_slider(k, v),
                            on_release=self._save, width=250, bg=BG1)
            sl.pack(pady=1)
            self.slider_widgets[key] = sl

    def _build_assign_panel(self, inner):
        top = tk.Frame(inner, bg=BG1)
        top.pack(fill=tk.X, padx=12, pady=(8, 4))
        self.sel_tile = tk.Canvas(top, width=70, height=66, bg=BG1, highlightthickness=0, bd=0)
        self.sel_tile.pack(side=tk.LEFT)
        info = tk.Frame(top, bg=BG1)
        info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.sel_hint = tk.Label(info, text="Seçili tuş", font=(FONT, 9), fg=MUTED, bg=BG1, anchor="w")
        self.sel_hint.pack(fill=tk.X)
        self.raw_label = tk.Label(info, text="Ham: ---", font=("Consolas", 10, "bold"),
                                  fg=ACC_HI, bg=BG1, anchor="w")
        self.raw_label.pack(fill=tk.X)
        self.sel_bar = tk.Canvas(info, height=10, bg=BG1, highlightthickness=0, bd=0)
        self.sel_bar.pack(fill=tk.X, pady=(4, 0))

        btns = tk.Frame(inner, bg=BG1)
        btns.pack(fill=tk.X, padx=12, pady=(2, 6))
        FlatButton(btns, "Tepeyi Analog Max yap", self._peak_to_max, width=186, height=28,
                   style="ghost", font=(FONT, 8, "bold"), bg=BG1).pack(side=tk.LEFT)
        FlatButton(btns, "Sıfırla", self._reset_peak, width=70, height=28, style="ghost",
                   font=(FONT, 8), bg=BG1).pack(side=tk.LEFT, padx=6)

        tk.Frame(inner, bg=LINE, height=1).pack(fill=tk.X, padx=12, pady=(2, 4))

        cont = tk.Frame(inner, bg=BG1)
        cont.pack(fill=tk.BOTH, expand=True, padx=(8, 4), pady=(0, 8))
        self.list_canvas = tk.Canvas(cont, bg=BG1, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(cont, orient=tk.VERTICAL, command=self.list_canvas.yview,
                           style="Dark.Vertical.TScrollbar")
        lst = tk.Frame(self.list_canvas, bg=BG1)
        win = self.list_canvas.create_window((0, 0), window=lst, anchor=tk.NW)
        lst.bind("<Configure>",
                 lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.configure(yscrollcommand=sb.set)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        for gname, items in OUTPUT_GROUPS:
            gh = tk.Frame(lst, bg=BG1)
            gh.pack(fill=tk.X, pady=(10, 2))
            tk.Frame(gh, bg=ACC_DEEP, width=3, height=10).pack(side=tk.LEFT, padx=(6, 6))
            tk.Label(gh, text=gname, font=(FONT, 8, "bold"), fg=ACC_HI, bg=BG1).pack(side=tk.LEFT)
            for out_id, out_name in items:
                row = CheckRow(lst, out_name, lambda o=out_id: self._on_toggle(o))
                row.pack(fill=tk.X)
                self.out_vars[out_id] = row

    def _build_footer(self):
        foot = tk.Frame(self.root, bg=BG0)
        foot.pack(fill=tk.X, padx=16, pady=(6, 8))
        tk.Label(foot, text="Not: oyunun klavye atamalarında burada kullandığın tuşları boşalt / "
                            "başka tuşa taşı.", font=(FONT, 8), fg=MUTED, bg=BG0).pack(side=tk.LEFT)
        self.block_var = tk.BooleanVar(value=load_block_flag())
        self.block_switch = ToggleSwitch(foot, self.block_var, self._on_block_toggle, bg=BG0)
        self.block_switch.pack(side=tk.RIGHT)
        tk.Label(foot, text="BLOK (deneysel)", font=(FONT, 8, "bold"), fg=MUTED,
                 bg=BG0).pack(side=tk.RIGHT, padx=8)

    # -- profiller ----------------------------------------------------
    def _build_tabs(self):
        for w in self.tabs_frame.winfo_children():
            w.destroy()
        for name in self.profiles:
            active = (name == self.active_name)
            width = max(78, 26 + 8 * len(name))
            tab = FlatButton(self.tabs_frame, name, lambda n=name: self._switch_profile(n),
                             width=width, height=34, style="primary" if active else "ghost",
                             bg=BG0, font=(FONT, 9, "bold"))
            tab.pack(side=tk.LEFT, padx=3)
            tab.bind("<Button-3>", lambda e, n=name: self._tab_menu(e, n))
        FlatButton(self.tabs_frame, "+", self._new_profile, width=38, height=34, style="ghost",
                   bg=BG0, font=(FONT, 12, "bold")).pack(side=tk.LEFT, padx=3)

    def _tab_menu(self, event, name):
        m = tk.Menu(self.root, tearoff=0, bg=BG2, fg=TEXT, activebackground=ACC,
                    activeforeground="#ffffff", bd=0, relief="flat")
        m.add_command(label="Yeniden adlandır",
                      command=lambda: (self._switch_profile(name), self._rename_profile()))
        m.add_command(label="Sil",
                      command=lambda: (self._switch_profile(name), self._delete_profile()))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _ask_name(self, title, initial=""):
        return ask_text(self.root, title, "Profil adı", initial)

    def _apply_profile_to_ui(self):
        self._build_tabs()
        self._load_sliders()
        if self.selected_key:
            for out, row in self.out_vars.items():
                row.set(self.selected_key in (self.bindings.get(out) or []))
        self._refresh_key_visuals()

    # -- eksik olan fonksiyonlar eklendi --
    def _peak_to_max(self):
        if not self.selected_key:
            return
        pk = self.peaks.get(self.selected_key, 0)
        v = self.kb_state.get(self.selected_key, 0)
        val = max(pk, v)
        if val > 0:
            self.settings["analog_max"] = float(val)
            self._load_sliders()
            self._save()

    def _reset_peak(self):
        if self.selected_key:
            self.peaks[self.selected_key] = 0

    # -- ayar kaydiricilari -------------------------------------------
    def _on_slider(self, key, value):
        if not self._loading:
            self.settings[key] = float(value)

    def _load_sliders(self):
        self._loading = True
        try:
            for key, sl in self.slider_widgets.items():
                sl.set_value(float(self.settings.get(key, DEFAULT_SETTINGS[key])))
        finally:
            self._loading = False

    # -- tus secimi ve gorunum ----------------------------------------
    def _select_key(self, label):
        self.selected_key = label
        mapped = label in self.key_mapping
        self.sel_hint.config(text="Seçili tuş" if mapped else "Seçili tuş (haritalanmamış)")
        self._draw_sel_tile(label)
        for out, row in self.out_vars.items():
            row.set(label in (self.bindings.get(out) or []))
        self._refresh_key_visuals()

    def _draw_sel_tile(self, label):
        c = self.sel_tile
        c.delete("all")
        rrect(c, 4, 10, 66, 62, 12, fill=KEY_SHADOW, outline="")
        rrect(c, 4, 8, 66, 60, 12, fill=KEY_SIDE, outline="")
        rrect(c, 5, 4, 65, 50, 11, fill=KEY_TOP, outline=ACC_NEON, width=2)
        c.create_line(14, 7, 56, 7, fill=KEY_GLOSS)
        size = 20 if len(label) <= 2 else (13 if len(label) <= 4 else 10)
        c.create_text(35, 27, text=label, fill="#ffffff", font=(FONT, size, "bold"))

    def _key_ratio(self, label):
        amax = float(self.settings.get("analog_max", 350.0)) or 350.0
        return min(1.0, self.kb_state.get(label) / amax)

    def _refresh_key_visuals(self):
        assigned = {}
        for out, keys in self.bindings.items():
            for k in keys:
                assigned.setdefault(k, []).append(out)
        c = self.keys_canvas
        for label, it in self.key_items.items():
            outs = assigned.get(label, [])
            txt = " ".join(SHORT.get(o, o) for o in outs[:2]) + ("+" if len(outs) > 2 else "")
            c.itemconfig(it["ids"]["t2"], text=txt)
            it["sel"] = (label == self.selected_key)
            it["asg"] = bool(outs)
            self._paint_key(label, self._key_ratio(label) if label in self.key_mapping else 0.0,
                            force=True)
        self._refresh_block_set()

    def _paint_key(self, label, ratio, force=False):
        it = self.key_items[label]
        depth = int(round(ratio * 5))
        sig = (depth, int(ratio * 24), it["sel"], it["asg"])
        if not force and it["sig"] == sig:
            return
        it["sig"] = sig
        c = self.keys_canvas
        ids = it["ids"]
        x0, y0, x1, y1, cx = it["geom"]
        c.coords(ids["top"], *rr_points(x0 + 1, y0 + depth, x1 - 1, y1 - 8 + depth, 8))
        c.coords(ids["gloss"], x0 + 9, y0 + 2 + depth, x1 - 9, y0 + 2 + depth)
        c.coords(ids["t1"], cx, y0 + 14 + depth)
        c.coords(ids["t2"], cx, y0 + 31 + depth)
        lit = ratio > 0.02
        fill = blend(KEY_TOP, KEY_HOT, ratio) if lit else KEY_TOP
        if it["sel"]:
            edge = ACC_NEON
        elif lit:
            edge = blend(KEY_EDGE, ACC_NEON, ratio)
        else:
            edge = ASG_EDGE if it["asg"] else KEY_EDGE
        c.itemconfig(ids["top"], fill=fill, outline=edge)
        c.itemconfig(ids["shadow"], fill=blend(KEY_SHADOW, "#4c1d95", ratio) if lit else KEY_SHADOW)
        c.itemconfig(ids["ring"], state="normal" if it["sel"] else "hidden")

    # -- canli guncelleme ---------------------------------------------
    def _ui_loop(self):
        if not self.running:
            return
        try:
            amax = float(self.settings.get("analog_max", 350.0)) or 350.0
            for label in self.key_items:
                if label in self.key_mapping:
                    self._paint_key(label, min(1.0, self.kb_state.get(label) / amax))

            if self.selected_key:
                v = self.kb_state.get(self.selected_key)
                pk = max(self.peaks.get(self.selected_key, 0), v)
                self.peaks[self.selected_key] = pk
                self.raw_label.config(text="Ham %4d · %%%d · tepe %d" % (
                    v, min(100, int(v * 100 // max(1, int(amax)))), pk))
                self._draw_sel_bar(min(1.0, v / amax))

            d = self.display
            self._draw_stick(self.left_canvas, d["lx"], d["ly"])
            self._draw_stick(self.right_canvas, d["rx"], d["ry"])
            self.ls_label.config(text="X %+.2f   Y %+.2f" % (d["lx"], d["ly"]))
            self.rs_label.config(text="X %+.2f   Y %+.2f" % (d["rx"], d["ry"]))
            self._draw_triggers(d["lt"], d["rt"])
            self._update_chips(d["pressed"])
            self.block_switch.refresh()
        except Exception:
            traceback.print_exc()
        self.root.after(33, self._ui_loop)

    def _draw_sel_bar(self, ratio):
        c = self.sel_bar
        w = c.winfo_width()
        if w < 20:
            return
        c.delete("all")
        rrect(c, 0, 1, w, 9, 4, fill="#1c1933", outline="")
        if ratio > 0.01:
            rrect(c, 0, 1, max(8, w * ratio), 9, 4, fill=blend(ACC, PINK, ratio), outline="")

    def _draw_stick(self, canvas, x, y):
        canvas.delete("all")
        cx = cy = 75
        r = 62
        canvas.create_oval(cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5, outline="#17142b", width=4)
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=LINE, width=2, fill="#0d0b17")
        canvas.create_oval(cx - r * 0.66, cy - r * 0.66, cx + r * 0.66, cy + r * 0.66,
                           outline="#1d1a36")
        canvas.create_oval(cx - r * 0.33, cy - r * 0.33, cx + r * 0.33, cy + r * 0.33,
                           outline="#1d1a36")
        canvas.create_line(cx - r, cy, cx + r, cy, fill="#1d1a36")
        canvas.create_line(cx, cy - r, cx, cy + r, fill="#1d1a36")
        dz = float(self.settings.get("deadzone", 0.05)) * r
        if dz > 1:
            canvas.create_oval(cx - dz, cy - dz, cx + dz, cy + dz, outline="#4c1d95", dash=(2, 3))
        kx = cx + x * r
        ky = cy - y * r
        mag = min(1.0, math.sqrt(x * x + y * y))
        col = blend(ACC, PINK, mag)
        if mag > 0.02:
            canvas.create_line(cx, cy, kx, ky, fill=blend("#0d0b17", col, 0.6), width=3)
        for rad, t in ((17, 0.12), (13, 0.26)):
            canvas.create_oval(kx - rad, ky - rad, kx + rad, ky + rad,
                               fill=blend("#0d0b17", col, t), outline="")
        canvas.create_oval(kx - 8, ky - 8, kx + 8, ky + 8, fill=col, outline="#ede9fe", width=2)

    def _draw_triggers(self, lt, rt):
        c = self.trig_canvas
        c.delete("all")
        for off, name, val in ((0, "LT", lt), (140, "RT", rt)):
            c.create_text(off + 2, 15, text=name, anchor="w", fill=MUTED, font=(FONT, 9, "bold"))
            rrect(c, off + 26, 9, off + 128, 21, 5, fill="#1c1933", outline="")
            if val > 0.01:
                rrect(c, off + 26, 9, off + 26 + max(10, 102 * val), 21, 5,
                      fill=blend(ACC, PINK, val), outline="")

    def _update_chips(self, pressed):
        now = set(pressed)
        if now == self._chips_on:
            return
        cc = self.chip_canvas
        for out, (rect, txt) in self.chip_items.items():
            on = out in now
            cc.itemconfig(rect, fill=ACC if on else BG2, outline=ACC_NEON if on else LINE)
            cc.itemconfig(txt, fill="#ffffff" if on else MUTED)
        self._chips_on = now


def main():
    try:
        with open(KEY_CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        key_mapping = {k: int(v) for k, v in cfg["key_mapping"].items()}
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        gs.messagebox.showerror("key_config.json",
                                "key_config.json okunamadı:\n%s\n\n"
                                "Önce key_mapper_gui.py ile tuşları haritala." % e)
        return
    root = tk.Tk()
    ModernStudio(root, key_mapping)
    root.mainloop()


if __name__ == "__main__":
    main()