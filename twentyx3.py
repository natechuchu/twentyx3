"""twentyx3: a tiny 20-20-20 eye-break companion that grows a plant.

Every 20 minutes, look at something 20 feet away for 20 seconds.
Run with --demo for 10-second cycles while trying it out.
"""
import json
import math
import sys
import time
import tkinter as tk
from pathlib import Path

try:
    import winsound
except ImportError:
    winsound = None

DEMO = "--demo" in sys.argv
WORK = 10 if DEMO else 20 * 60  # seconds between breaks
LOOK = 5 if DEMO else 20        # seconds to look away
GRACE = 5 if DEMO else 30       # seconds to tap Done after looking, or the streak breaks
SAVE = Path(__file__).with_name("twentyx3.json")
DEFAULT = {"streak": 0, "best": 0, "total": 0, "wilted": False}

BG, INK, SOFT, IDLE = "#F4F1E6", "#2F4A2F", "#7D8F69", "#CFCDBF"
LEAF, LEAF2, WILT = "#6A994E", "#A7C957", "#B5A770"
POT, RIM, SOIL = "#C26A3D", "#D07A4A", "#6B4226"
BLOOM, BLOOM_WILT, CENTER, SUN = "#F4A6A6", "#D8B4A0", "#F6BD60", "#F6D365"
STAGES = [(80, "Flourishing"), (40, "Blooming"), (15, "Young plant"),
          (5, "Seedling"), (1, "Sprout"), (0, "Seed")]


def load():
    try:
        return {**DEFAULT, **json.loads(SAVE.read_text())}
    except (OSError, ValueError):
        return dict(DEFAULT)


def chime(kind=0x40):  # 0x40 = asterisk, 0 = default beep
    if winsound:
        winsound.MessageBeep(kind)


def leaf(c, x, y, side, ang, length, color):
    dx, dy = side * math.cos(ang), -math.sin(ang)
    nx, ny, w = -dy, dx, length * 0.22
    mx, my = x + dx * length / 2, y + dy * length / 2
    tx, ty = x + dx * length, y + dy * length
    # repeated points keep the base and tip pointed when smoothed
    c.create_polygon(x, y, x, y, mx + nx * w, my + ny * w, tx, ty, tx, ty,
                     mx - nx * w, my - ny * w, fill=color, outline="", smooth=True)


def flower(c, x, y, r, color):
    for k in range(5):
        a = k * 2 * math.pi / 5
        px, py = x + r * math.cos(a), y + r * math.sin(a)
        c.create_oval(px - r * .7, py - r * .7, px + r * .7, py + r * .7, fill=color, outline="")
    c.create_oval(x - r * .5, y - r * .5, x + r * .5, y + r * .5, fill=CENTER, outline="")


def draw_plant(c, total, wilted, t, pop):
    c.delete("all")
    cx, base = 160, 237
    c.create_oval(250, 22, 290, 62, fill=SUN, outline="")
    if wilted:  # a little cloud drifts over the sun
        for x, y, r in ((258, 52, 14), (276, 46, 18), (296, 54, 13)):
            c.create_oval(x - r, y - r, x + r, y + r, fill="#DADBD0", outline="")
    c.create_polygon(118, 248, 202, 248, 192, 294, 128, 294, fill=POT, outline="")
    c.create_rectangle(110, 236, 210, 252, fill=RIM, outline="")
    c.create_oval(116, 230, 204, 244, fill=SOIL, outline="")
    if total == 0:
        c.create_oval(cx - 6, base - 7, cx + 6, base + 1, fill="#8B5E3C", outline="")
        return

    g = 1 - math.exp(-total / 25)  # 0 -> 1 growth curve
    h = 20 + 170 * g
    sway = math.sin(t * 1.3) * (1 if wilted else 4)

    def stem(f):
        x = cx + sway * f * f + (35 * f ** 3 if wilted else 0)
        y = base - h * f + (30 * f ** 4 if wilted else 0)
        return x, y

    pts = [v for i in range(13) for v in stem(i / 12)]
    c.create_line(*pts, fill=WILT if wilted else LEAF, width=2 + 6 * g, smooth=True, capstyle="round")

    droop = -1 if wilted else 1
    n = min(1 + total // 2, 14)
    for i in range(n):
        f = (i + 1) / (n + 1) * 0.9
        ang = droop * 0.6 + 0.1 * math.sin(t * 1.6 + i)
        color = WILT if wilted else (LEAF, LEAF2)[i % 2]
        leaf(c, *stem(f), 1 if i % 2 else -1, ang, (12 + 26 * g) * (1.1 - 0.4 * f), color)

    tx, ty = stem(1)
    for side in (-1, 1):
        leaf(c, tx, ty, side, droop * 0.9, 8 + 10 * g, WILT if wilted else LEAF2)

    if total >= 40:
        color = BLOOM_WILT if wilted else BLOOM
        flower(c, tx, ty - 4, 5 + 4 * g, color)
        for j in range(min((total - 40) // 10, 5)):
            x, y = stem(0.8 - j * 0.14)
            flower(c, x + (14 if j % 2 else -14), y - 4, 4 + 3 * g, color)

    if pop > 0:  # floating +1 after a completed break
        c.create_text(tx + 24, ty - 10 - 30 * (1 - pop), text="+1", fill=LEAF,
                      font=("Segoe UI Semibold", 14))


class App:
    def __init__(self, root):
        self.root, self.data = root, load()
        self.state, self.deadline, self.pop_end = "idle", 0, 0

        root.title("twentyx3")
        root.configure(bg=BG, padx=20, pady=12)
        root.resizable(False, False)
        tk.Label(root, text="20 · 20 · 20", font=("Segoe UI Semibold", 18), bg=BG, fg=INK).pack()
        tk.Label(root, text="every 20 min, look 20 ft away for 20 s",
                 font=("Segoe UI", 9), bg=BG, fg=SOFT).pack()
        self.canvas = tk.Canvas(root, width=320, height=300, bg=BG, highlightthickness=0)
        self.canvas.pack(pady=(4, 0))
        self.stage = tk.Label(root, font=("Segoe UI", 10, "italic"), bg=BG, fg=SOFT)
        self.stage.pack()

        stats = tk.Frame(root, bg=BG)
        stats.pack(pady=10)
        self.stats = {}
        for col, (key, name) in enumerate((("streak", "streak"), ("best", "best"), ("total", "breaks"))):
            tk.Label(stats, text=name, font=("Segoe UI", 9), bg=BG, fg=SOFT).grid(row=1, column=col, padx=22)
            self.stats[key] = tk.Label(stats, font=("Segoe UI Semibold", 20), bg=BG, fg=INK)
            self.stats[key].grid(row=0, column=col)

        self.status = tk.Label(root, font=("Segoe UI", 12), bg=BG, fg=INK, width=34)
        self.status.pack()
        bar = tk.Frame(root, bg=BG)
        bar.pack(pady=(10, 4))
        self.main = self.button(bar, "Start", self.toggle, LEAF)
        self.done = self.button(bar, "Done", self.complete, LEAF)

        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.refresh()
        self.tick()

    def button(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd, bg=color, fg="white", activebackground=INK,
                         activeforeground="white", disabledforeground="#E6E9DC", relief="flat", bd=0,
                         font=("Segoe UI Semibold", 11), padx=20, pady=6, cursor="hand2")

    def save(self):
        SAVE.write_text(json.dumps(self.data))

    def quit(self):
        self.save()
        self.root.destroy()

    def refresh(self):
        d = self.data
        name = next(n for limit, n in STAGES if d["total"] >= limit)
        self.stage.config(text=f"{name}" + (" · a little droopy" if d["wilted"] else ""))
        for key, label in self.stats.items():
            label.config(text=d[key])
        for b in (self.main, self.done):
            b.pack_forget()
        if self.state in ("break", "confirm"):
            ready = self.state == "confirm"  # grayed out while looking away
            self.done.config(state="normal" if ready else "disabled", bg=LEAF if ready else IDLE,
                             cursor="hand2" if ready else "arrow")
            self.done.pack()
        else:
            self.main.config(text="Pause" if self.state == "work" else "Start",
                             bg=SOFT if self.state == "work" else LEAF)
            self.main.pack()

    def set_state(self, state, seconds=0):
        self.state, self.deadline = state, time.monotonic() + seconds
        self.refresh()

    def toggle(self):
        self.set_state("idle" if self.state == "work" else "work", WORK)

    def start_break(self):
        self.set_state("break", LOOK)
        r = self.root
        r.deiconify()
        r.lift()
        r.attributes("-topmost", True)
        r.focus_force()
        chime()

    def finish_break(self):
        self.root.attributes("-topmost", False)
        self.save()
        self.set_state("work", WORK)

    def complete(self):
        d = self.data
        d["total"] += 1
        d["streak"] += 1
        d["best"] = max(d["best"], d["streak"])
        d["wilted"] = False
        self.pop_end = time.monotonic() + 1.5
        self.finish_break()

    def miss(self):
        self.data["streak"] = 0
        self.data["wilted"] = self.data["total"] > 0
        self.finish_break()

    def tick(self):
        now = time.monotonic()
        left = max(0, math.ceil(self.deadline - now))
        if self.state == "work" and left == 0:
            self.start_break()
        elif self.state == "break" and left == 0:
            self.set_state("confirm", GRACE)
            chime(0)
        elif self.state == "confirm" and left == 0:
            self.miss()

        text = {
            "idle": "Your plant missed you. Try again?" if self.data["wilted"] else "Press start when you're ready",
            "work": f"Next break in {left // 60:02d}:{left % 60:02d}",
            "break": f"Look 20 feet away…  {left}",
            "confirm": f"Did you look away? Tap Done · {left}",
        }[self.state]
        self.status.config(text=text)
        draw_plant(self.canvas, self.data["total"], self.data["wilted"], now, (self.pop_end - now) / 1.5)
        self.root.after(80, self.tick)


if __name__ == "__main__":
    if winsound:  # Windows: render crisply on high-DPI screens
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root = tk.Tk()
    App(root)
    root.mainloop()
