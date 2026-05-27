#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════╗
║      ASCII 花火ジェネレーター  🎆      ║
║   Enter / Space  : 花火を打ち上げる   ║
║   Q / Esc        : 終了              ║
╚══════════════════════════════════════╝
"""

import sys
import os
import time
import random
import math
import msvcrt  # Windows 専用キー入力

# Windows 10+ で ANSI カラーを有効化
os.system("")

# ─── ANSI エスケープ ─────────────────────────────────
RESET       = "\033[0m"
DIM         = "\033[2m"
REVERSE     = "\033[7m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# 花火の色パレット
COLORS = [
    "\033[91m",  # 明るい赤
    "\033[92m",  # 明るい緑
    "\033[93m",  # 明るい黄色
    "\033[94m",  # 明るい青
    "\033[95m",  # 明るいマゼンタ
    "\033[96m",  # 明るいシアン
    "\033[97m",  # 明るい白
    "\033[33m",  # 橙黄色
    "\033[35m",  # マゼンタ
    "\033[36m",  # シアン
    "\033[31m",  # 赤
    "\033[32m",  # 緑
]

# 爆発の文字パレット
BURST_CHARS = ["*", "+", "x", "o", "@", "#", "X", "0"]


# ─── 星空の背景 ──────────────────────────────────────
class StarField:
    """静止した星を表示するクラス"""

    def __init__(self, width: int, height: int, density: float = 0.008):
        self.stars: list[tuple[int, int, str]] = []
        for y in range(height - 1):
            for x in range(width):
                if random.random() < density:
                    char = random.choice([".", "'", "`", ","])
                    self.stars.append((x, y, char))

    def get_pixels(self) -> list[tuple[int, int, str, str]]:
        return [(x, y, DIM + "\033[37m", c) for x, y, c in self.stars]


# ─── パーティクル ────────────────────────────────────
class Particle:
    """花火の爆発後に飛び散る一粒"""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: str,
        char: str,
        lifetime: int,
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.char = char
        self.age = 0
        self.lifetime = lifetime

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.055   # 重力
        self.vx *= 0.97    # 横方向の空気抵抗
        self.vy *= 0.99    # 縦方向の空気抵抗
        self.age += 1

    def is_alive(self) -> bool:
        return self.age < self.lifetime

    @property
    def ratio(self) -> float:
        """残り寿命の割合 (1.0 → 0.0)"""
        return 1.0 - (self.age / self.lifetime)

    def get_char(self) -> str:
        r = self.ratio
        if r > 0.55:
            return self.char
        elif r > 0.35:
            return "+"
        elif r > 0.18:
            return "."
        else:
            return "`"

    def get_color(self) -> str:
        if self.ratio < 0.25:
            return DIM + self.color
        return self.color

    def get_pixel(self) -> tuple[int, int, str, str]:
        return int(self.x), int(self.y), self.get_color(), self.get_char()


# ─── ロケット ────────────────────────────────────────
class Rocket:
    """打ち上げ中のロケット本体"""

    SPEED = 1.6
    TRAIL_LEN = 7

    def __init__(self, x: float, target_y: float, start_y: float, color: str):
        self.x = x
        self.y = float(start_y)
        self.target_y = float(target_y)
        self.color = color
        self.trail: list[tuple[int, int]] = []
        self.exploded = False

    def update(self) -> None:
        if not self.exploded:
            self.trail.append((int(self.x), int(self.y)))
            if len(self.trail) > self.TRAIL_LEN:
                self.trail.pop(0)
            self.y -= self.SPEED
            if self.y <= self.target_y:
                self.exploded = True

    def get_pixels(self) -> list[tuple[int, int, str, str]]:
        if self.exploded:
            return []
        px = int(self.x)
        py = int(self.y)
        pixels: list[tuple[int, int, str, str]] = [
            (px, py, self.color, "|")
        ]
        for i, (tx, ty) in enumerate(self.trail):
            alpha = i / max(len(self.trail), 1)
            c = "|" if alpha > 0.65 else (":" if alpha > 0.35 else ".")
            pixels.append((tx, ty, DIM + "\033[33m", c))
        return pixels


# ─── 花火 ────────────────────────────────────────────
class Firework:
    """ロケット + 爆発 + パーティクル全体の管理"""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

        # ランダムな位置・色を決定
        x = random.randint(width // 7, 6 * width // 7)
        target_y = random.randint(height // 8, height * 2 // 5)
        self._color = random.choice(COLORS)

        self.rocket = Rocket(x, target_y, height - 2, self._color)
        self.particles: list[Particle] = []
        self._done = False

    def _explode(self) -> None:
        cx = self.rocket.x
        cy = self.rocket.target_y
        color = self._color
        char = random.choice(BURST_CHARS)
        count = random.randint(28, 52)

        # 多色爆発 (40% の確率)
        multi = random.random() < 0.4
        color2 = random.choice(COLORS)

        # ─ 放射状パーティクル
        for i in range(count):
            angle = 2 * math.pi * i / count
            speed = random.uniform(0.5, 2.4)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed * 0.42   # 縦横比補正
            c = color2 if (multi and i % 2 == 0) else color
            lt = random.randint(18, 38)
            self.particles.append(Particle(cx, cy, vx, vy, c, char, lt))

        # ─ 中心バースト（白い光）
        for _ in range(10):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.05, 0.6)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(
                Particle(cx, cy, vx, vy, "\033[97m", "*", random.randint(10, 20))
            )

        # ─ 流れ星（長い尾）
        for _ in range(random.randint(0, 5)):
            angle = random.uniform(math.pi * 0.3, math.pi * 0.7)  # 下向きに偏らせる
            speed = random.uniform(1.5, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed * 0.4
            self.particles.append(
                Particle(cx, cy, vx, vy, color, "+", random.randint(25, 45))
            )

    def update(self) -> None:
        if not self.rocket.exploded:
            self.rocket.update()
            if self.rocket.exploded:
                self._explode()
        else:
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.is_alive()]
            if not self.particles:
                self._done = True

    def is_done(self) -> bool:
        return self._done

    def get_pixels(self) -> list[tuple[int, int, str, str]]:
        pixels = self.rocket.get_pixels()
        w, h = self.width, self.height
        for p in self.particles:
            x, y, color, char = p.get_pixel()
            if 0 <= x < w and 0 <= y < h:
                pixels.append((x, y, color, char))
        return pixels


# ─── レンダリング ────────────────────────────────────
def get_size() -> tuple[int, int]:
    try:
        s = os.get_terminal_size()
        return s.columns, max(s.lines - 2, 10)
    except OSError:
        return 80, 24


def render(
    fireworks: list[Firework],
    stars: StarField,
    width: int,
    height: int,
    count: int,
) -> None:
    # キャンバスをピクセル辞書で構築（後から書いたものが優先）
    canvas: dict[tuple[int, int], tuple[str, str]] = {}

    # 背景の星
    for x, y, color, char in stars.get_pixels():
        canvas[(x, y)] = (color, char)

    # 花火（前の花火の上に重ねる）
    for fw in fireworks:
        for x, y, color, char in fw.get_pixels():
            if 0 <= x < width and 0 <= y < height:
                canvas[(x, y)] = (color, char)

    # フレームを文字列に変換
    buf = ["\033[H"]  # カーソルをホームへ
    for y in range(height):
        row = ""
        for x in range(width):
            if (x, y) in canvas:
                color, char = canvas[(x, y)]
                row += color + char + RESET
            else:
                row += " "
        buf.append(row + "\n")

    # ステータスバー（反転表示）
    msg = (
        f"  [Enter/Space] 花火を打ち上げる  "
        f"[Q/Esc] 終了  "
        f"|  打ち上げ: {count} 発  "
    )
    bar = msg[:width].ljust(width)
    buf.append(f"\033[{height + 1};1H")
    buf.append(REVERSE + bar + RESET)

    sys.stdout.write("".join(buf))
    sys.stdout.flush()


# ─── メインループ ────────────────────────────────────
def main() -> None:
    sys.stdout.write(HIDE_CURSOR)
    os.system("cls")

    width, height = get_size()
    stars = StarField(width, height)
    fireworks: list[Firework] = []
    count = 0

    # 最初の花火を自動打ち上げ
    fireworks.append(Firework(width, height))
    count += 1

    try:
        while True:
            # ── キー入力（ノンブロッキング）──────────
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b"q", b"Q", b"\x1b"):          # Q / Esc → 終了
                    break
                elif key in (b"\r", b" ", b"\n"):          # Enter / Space → 打ち上げ
                    if len(fireworks) < 12:
                        fireworks.append(Firework(width, height))
                        count += 1

            # ── 状態更新 ───────────────────────────
            for fw in fireworks:
                fw.update()
            fireworks = [fw for fw in fireworks if not fw.is_done()]

            # ── 自動打ち上げ（花火がなくなったとき、またはたまに）──
            if not fireworks or (random.random() < 0.012 and len(fireworks) < 3):
                fireworks.append(Firework(width, height))
                count += 1

            # ── 描画 ───────────────────────────────
            render(fireworks, stars, width, height, count)
            time.sleep(0.05)  # 約 20 FPS

    finally:
        sys.stdout.write(SHOW_CURSOR)
        os.system("cls")
        print("🎆 花火大会、終了！楽しんでいただけましたか？")
        print(f"   合計 {count} 発の花火を打ち上げました！")


if __name__ == "__main__":
    main()
