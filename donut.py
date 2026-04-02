"""
Spinning 3D Donut in Python
Classic algorithm by Andy Sloane (donut.c), ported to Python with ANSI color.

Run: python3 donut.py
Press Ctrl+C to exit.
"""

import math
import time
import sys
import os

# ANSI color codes (brightness gradient)
COLORS = [
    "\033[90m",  # dark gray
    "\033[34m",  # blue
    "\033[36m",  # cyan
    "\033[32m",  # green
    "\033[33m",  # yellow
    "\033[31m",  # red
    "\033[35m",  # magenta
    "\033[37m",  # white
    "\033[97m",  # bright white
]
RESET = "\033[0m"
CLEAR = "\033[H"  # move cursor to top-left (no flicker)

LUMINANCE = ".,-~:;=!*#$@"

WIDTH, HEIGHT = 80, 24

def render_frame(A: float, B: float) -> str:
    """Render one frame of the donut given rotation angles A and B."""
    output = [" "] * (WIDTH * HEIGHT)
    zbuf = [0.0] * (WIDTH * HEIGHT)
    color_buf = [0] * (WIDTH * HEIGHT)

    cos_A, sin_A = math.cos(A), math.sin(A)
    cos_B, sin_B = math.cos(B), math.sin(B)

    for theta_deg in range(0, 628, 7):       # theta: tube circle (0..2pi * 100)
        theta = theta_deg / 100.0
        cos_t, sin_t = math.cos(theta), math.sin(theta)

        for phi_deg in range(0, 628, 2):     # phi: revolution around z-axis
            phi = phi_deg / 100.0
            cos_p, sin_p = math.cos(phi), math.sin(phi)

            # Circle of radius 1 centered at distance 2 from origin
            h = cos_t + 2          # distance from center
            D = 1.0 / (sin_t * h * sin_A - sin_p * cos_A + 5)  # depth

            # Project onto screen
            x = int(WIDTH / 2  + 30 * D * (cos_t * h * cos_B - sin_p * (sin_t * h * cos_A + sin_p * sin_A) * sin_B))
            y = int(HEIGHT / 2 + 12 * D * (cos_t * h * sin_B + sin_p * (sin_t * h * cos_A + sin_p * sin_A) * cos_B))

            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                idx = y * WIDTH + x
                if D > zbuf[idx]:
                    zbuf[idx] = D

                    # Luminance calculation
                    L = (sin_t * h * sin_A - sin_p * cos_A) * cos_B - sin_p * sin_A - cos_t * h * sin_B
                    lum = int(L * 8)
                    lum_char = LUMINANCE[max(0, lum)] if lum > 0 else "."
                    output[idx] = lum_char
                    color_buf[idx] = min(lum + 1, len(COLORS) - 1) if lum > 0 else 0

    # Build the frame string
    rows = []
    for row in range(HEIGHT):
        line = ""
        for col in range(WIDTH):
            idx = row * WIDTH + col
            ch = output[idx]
            if ch != " ":
                ci = max(0, min(color_buf[idx], len(COLORS) - 1))
                line += COLORS[ci] + ch + RESET
            else:
                line += " "
        rows.append(line)
    return "\n".join(rows)


def main():
    A, B = 0.0, 0.0

    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        while True:
            frame = render_frame(A, B)
            sys.stdout.write(CLEAR + frame)
            sys.stdout.flush()
            A += 0.07
            B += 0.03
            time.sleep(0.033)  # ~30 fps
    except KeyboardInterrupt:
        pass
    finally:
        # Restore cursor, reset colors
        sys.stdout.write(RESET + "\033[?25h\n")
        sys.stdout.flush()
        print("Goodbye! 🍩")


if __name__ == "__main__":
    # Clear screen once before starting
    os.system("clear")
    print("\033[1mSpinning 3D Donut — Press Ctrl+C to exit\033[0m")
    time.sleep(1)
    main()
