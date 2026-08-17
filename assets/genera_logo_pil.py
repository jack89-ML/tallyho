#!/usr/bin/env python3
"""Logo vettoriale TallyHo (deterministico, PIL): seggiovia con urne,
montagna a gradoni, scheda di spoglio e wordmark TallyHo."""
from PIL import Image, ImageDraw, ImageFont
import os

W = H = 1024
BLU = (15, 27, 45)        # sfondo notte
BIANCO = (255, 255, 255)
ROSSO = (230, 57, 70)     # T e H
VERDE_SCURO = (30, 107, 78)
VERDE_CHIARO = (62, 155, 110)
GRIGIO_FUNE = (200, 210, 225)

FONT_PATH = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"
if not os.path.isfile(FONT_PATH):
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

img = Image.new("RGB", (W, H), BLU)
d = ImageDraw.Draw(img)

# --- sfondo: quadrato arrotondato con bordo sottile ---
d.rounded_rectangle([24, 24, W - 24, H - 24], radius=48, outline=GRIGIO_FUNE, width=4)

# --- montagna a gradoni (base) ---
d.polygon([(60, 640), (60, 560), (240, 440), (420, 530), (620, 460),
           (820, 540), (964, 470), (964, 640)], fill=VERDE_SCURO)
d.polygon([(240, 440), (350, 480), (560, 430), (620, 460), (420, 530)], fill=VERDE_CHIARO)

# --- fune della seggiovia ---
x1, y1, x2, y2 = 180, 590, 840, 250
d.line([(x1, y1), (x2, y2)], fill=GRIGIO_FUNE, width=10)

# --- urne-cabina (3, appese alla fune) ---
def urna(t):
    x = x1 + (x2 - x1) * t
    y = y1 + (y2 - y1) * t
    # connettore alla fune
    d.line([(x, y), (x, y + 34)], fill=GRIGIO_FUNE, width=8)
    # corpo urna
    d.rounded_rectangle([x - 52, y + 34, x + 52, y + 164], radius=10, fill=BIANCO)
    # fessura verticale
    d.rounded_rectangle([x - 10, y + 58, x + 10, y + 108], radius=5, fill=BLU)
    return x, y

for t in (0.30, 0.50, 0.70):
    urna(t)

# --- scheda di spoglio in alto a destra (piccola, secondaria) ---
sx, sy = 700, 120
d.rounded_rectangle([sx, sy, sx + 150, sy + 190], radius=12, fill=BIANCO)
# tre barre di spoglio crescenti + matita rossa
d.rectangle([sx + 24, sy + 150, sx + 48, sy + 170], fill=VERDE_CHIARO)
d.rectangle([sx + 58, sy + 120, sx + 82, sy + 170], fill=VERDE_SCURO)
d.rectangle([sx + 92, sy + 88, sx + 116, sy + 170], fill=VERDE_SCURO)
d.rectangle([sx + 126, sy + 138, sx + 134, sy + 148], fill=ROSSO)  # punta matita

# --- wordmark TallyHo (T e H rosse) ---
font = ImageFont.truetype(FONT_PATH, 148)
font_piccolo = ImageFont.truetype(FONT_PATH, 54)
testo = "TallyHo"
larghezze = {}
for ch in testo:
    larghezze[ch] = d.textlength(ch, font=font)
tot = sum(larghezze.values())
x0 = (W - tot) / 2
y_txt = 700
colori = {"T": ROSSO, "H": ROSSO}
for ch in testo:
    d.text((x0, y_txt), ch, font=font, fill=colori.get(ch, BIANCO))
    x0 += larghezze[ch]

# sottotitolo: "ti porta a spasso nella storia elettorale"
sotto = "TI PORTA A SPASSO NELLA STORIA ELETTORALE"
sw = d.textlength(sotto, font=font_piccolo)
d.text(((W - sw) / 2, y_txt + 185), sotto, font=font_piccolo, fill=GRIGIO_FUNE)

img.save("logo_tallyho.png")
print("logo_tallyho.png salvato")
