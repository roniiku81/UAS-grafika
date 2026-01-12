"""
Aplikasi Pembelajaran Interaktif Pengenalan Bentuk Geometri
File: main.py
Bahasa: Python 3
Library: pygame

Deskripsi singkat:
- Aplikasi sederhana untuk anak SD mengenal bentuk geometri dasar.
- Terdapat 3 mode: Belajar (Learn), Kuis (Quiz), dan Seret & Cocokkan (Drag & Match).
- Dibuat agar mudah dipahami, besar teks, warna kontras, umpan balik suara sederhana (bunyi), animasi halus.

Cara menjalankan:
1. Pastikan Python 3.8+ terpasang.
2. Pasang pygame: pip install pygame
3. Jalankan: python main.py

Catatan: Tidak memerlukan file eksternal. Semua bentuk digambar dengan primitives.

"""

import pygame
import sys
import random
import math
from pygame.locals import *

# -------------------- Konfigurasi --------------------
WIDTH, HEIGHT = 1000, 700
FPS = 60
FONT_NAME = None
BG_COLOR = (245, 245, 250)
PRIMARY = (40, 120, 200)
ACCENT = (233, 94, 94)
BUTTON_COLOR = (80, 160, 100)

SHAPES = [
    'Lingkaran',
    'Persegi',
    'Persegi Panjang',
    'Segitiga',
    'Jajargenjang',
    'Layang-layang'
]

# -------------------- Helper functions --------------------

def load_font(size):
    try:
        return pygame.font.Font(FONT_NAME, size)
    except Exception:
        return pygame.font.SysFont('Arial', size)


def draw_text(surface, text, size, x, y, center=True, color=(20,20,20)):
    font = load_font(size)
    r = font.render(text, True, color)
    rect = r.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(r, rect)


# -------------------- Shapes drawing --------------------

def draw_lingkaran(surface, center, radius, color, width=0):
    pygame.draw.circle(surface, color, center, radius, width)


def draw_persegi(surface, topleft, size, color, width=0):
    pygame.draw.rect(surface, color, (*topleft, size, size), width)


def draw_persegi_panjang(surface, topleft, w, h, color, width=0):
    pygame.draw.rect(surface, color, (*topleft, w, h), width)


def draw_segitiga(surface, points, color, width=0):
    pygame.draw.polygon(surface, color, points, width)


def draw_jajargenjang(surface, topleft, w, h, skew, color, width=0):
    x, y = topleft
    points = [(x+skew, y), (x+skew+w, y), (x+w, y+h), (x, y+h)]
    pygame.draw.polygon(surface, color, points, width)


def draw_layang(surface, center, w, h, color, width=0):
    cx, cy = center
    points = [(cx, cy-h//2), (cx+w//2, cy), (cx, cy+h//2), (cx-w//2, cy)]
    pygame.draw.polygon(surface, color, points, width)


# silhouette versions (outline only) for match mode

def draw_silhouette(surface, kind, rect):
    x, y, w, h = rect
    cx = x + w//2
    cy = y + h//2
    if kind == 'Lingkaran':
        draw_lingkaran(surface, (cx, cy), min(w,h)//3, (200,200,200), 5)
    elif kind == 'Persegi':
        draw_persegi(surface, (cx-w//4, cy-h//4), min(w,h)//2, (200,200,200), 5)
    elif kind == 'Persegi Panjang':
        draw_persegi_panjang(surface, (cx-w//3, cy-h//4), w//1.5, h//2, (200,200,200), 5)
    elif kind == 'Segitiga':
        pts = [(cx, cy-h//4), (cx-w//4, cy+h//6), (cx+w//4, cy+h//6)]
        draw_segitiga(surface, pts, (200,200,200), 5)
    elif kind == 'Jajargenjang':
        draw_jajargenjang(surface, (cx-w//4, cy-h//4), w//2, h//2, w//8, (200,200,200), 5)
    elif kind == 'Layang-layang':
        draw_layang(surface, (cx, cy), w//2, h//2, (200,200,200), 5)


# -------------------- Button --------------------
class Button:
    def __init__(self, rect, text, action=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action

    

    def draw(self, surf):
        pygame.draw.rect(surf, BUTTON_COLOR, self.rect, border_radius=12)
        draw_text(surf, self.text, 22, self.rect.centerx, self.rect.centery, color=(255,255,255))

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.action:
                    self.action()


# -------------------- App --------------------
class GeometryApp:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Belajar Bentuk Geometri - Anak SD')
        self.clock = pygame.time.Clock()
        self.mode = 'menu'
        self.running = True
        self.current_index = 0
        self.anim_t = 0


                # Tombol kembali ke menu (dipakai di banyak mode)
        self.btn_back = Button(
            (WIDTH-190, HEIGHT-120, 120, 60),
            'Menu',
            lambda: self.change_mode('menu')
        )


        # Sounds
        self.correct_sound = pygame.mixer.Sound(self._beep(440, 0.08))
        self.wrong_sound = pygame.mixer.Sound(self._beep(220, 0.12))

        # Menu buttons
        self.btn_learn = Button((70, 120, 220, 70), 'Belajar', lambda: self.change_mode('learn'))
        self.btn_quiz = Button((70, 220, 220, 70), 'Kuis', lambda: self.change_mode('quiz'))
        self.btn_drag = Button((70, 320, 220, 70), 'Seret & Cocokkan', lambda: self.change_mode('drag'))
        self.btn_exit = Button((70, 420, 220, 70), 'Keluar', self.exit)
        

        # Quiz state
        self.quiz_question = None
        self.quiz_options = []
        self.quiz_correct = None
        self.make_quiz()

        # Drag state
        self.drag_items = []
        self.targets = []
        self.reset_drag()

    def _beep(self, freq, duration):
        """Generate short beep sound for feedback (pygame requires bytes)."""
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buf = bytearray()
        max_amp = 127
        for s in range(n_samples):
            t = float(s)/sample_rate
            val = int(max_amp * math.sin(2*math.pi*freq*t)) + 128
            buf.append(max(0, min(255, val)))
        return bytes(buf)

    def change_mode(self, m):
        self.mode = m
        if m == 'quiz':
            self.make_quiz()
        if m == 'drag':
            self.reset_drag()

    def exit(self):
        self.running = False

    # -------------------- Quiz --------------------
    def make_quiz(self):
        self.quiz_question = random.choice(SHAPES)
        others = [s for s in SHAPES if s != self.quiz_question]
        opts = random.sample(others, 2)
        opts.append(self.quiz_question)
        random.shuffle(opts)
        self.quiz_options = opts
        self.quiz_correct = self.quiz_question

    def check_quiz(self, choice):
        if choice == self.quiz_correct:
            self.correct_sound.play()
            self.make_quiz()
        else:
            self.wrong_sound.play()

    # -------------------- Drag & Match --------------------
    def reset_drag(self):
        self.drag_items = []
        self.targets = []
        kinds = random.sample(SHAPES, 4)
        start_x = 150
        for i,k in enumerate(kinds):
            item = {
                'kind': k,
                'rect': pygame.Rect(start_x, 470 + i*0, 120, 120),
                'pos': [start_x, 470 + i*0],
                'dragging': False,
            }
            start_x += 150
            self.drag_items.append(item)

        # targets
        t_x = 150
        for i,k in enumerate(kinds):
            trect = pygame.Rect(120 + i*180, 150, 140, 140)
            self.targets.append({'kind': k, 'rect': trect, 'done': False})

    # -------------------- Draw screen --------------------
    def draw_menu(self):
        self.screen.fill(BG_COLOR)
        draw_text(self.screen, 'Aplikasi Pengenalan Bentuk Geometri', 34, WIDTH//2, 60)
        draw_text(self.screen, 'Pilih mode yang ingin dimainkan', 20, WIDTH//2, 95)
        self.btn_learn.draw(self.screen)
        self.btn_quiz.draw(self.screen)
        self.btn_drag.draw(self.screen)
        self.btn_exit.draw(self.screen)

        # small tip
        draw_text(self.screen, 'Cocok untuk anak SD ', 16, WIDTH//2, HEIGHT-30)

    def draw_learn(self):
        self.screen.fill(BG_COLOR)
        draw_text(self.screen, 'Mode Belajar', 30, WIDTH//2, 40)
        shape = SHAPES[self.current_index]
        draw_text(self.screen, shape, 40, WIDTH//2, 120, color=PRIMARY)

        # animate shape
        cx, cy = WIDTH//2, HEIGHT//2
        t = self.anim_t
        size = 80 + int(10*math.sin(t*2))
        if shape == 'Lingkaran':
            draw_lingkaran(self.screen, (cx, cy), size, PRIMARY)
        elif shape == 'Persegi':
            draw_persegi(self.screen, (cx-size//2, cy-size//2), size, PRIMARY)
        elif shape == 'Persegi Panjang':
            draw_persegi_panjang(self.screen, (cx-size, cy-size//2), size*2, size, PRIMARY)
        elif shape == 'Segitiga':
            pts = [(cx, cy-size), (cx-size, cy+size//2), (cx+size, cy+size//2)]
            draw_segitiga(self.screen, pts, PRIMARY)
        elif shape == 'Jajargenjang':
            draw_jajargenjang(self.screen, (cx-size, cy-size//2), size*2, size, size//4, PRIMARY)
        elif shape == 'Layang-layang':
            draw_layang(self.screen, (cx, cy), size*2, size*2, PRIMARY)

        # next/prev buttons
        prev_btn = Button((70, HEIGHT-120, 120, 60), 'Sebelum', lambda: self.prev_shape())
        next_btn = Button((WIDTH-190, HEIGHT-120, 120, 60), 'Berikut', lambda: self.next_shape())
        back_btn = Button((WIDTH-360, HEIGHT-120, 120, 60), 'Menu', lambda: self.change_mode('menu'))
        prev_btn.draw(self.screen)
        next_btn.draw(self.screen)
        back_btn.draw(self.screen)

    def prev_shape(self):
        self.current_index = (self.current_index - 1) % len(SHAPES)

    def next_shape(self):
        self.current_index = (self.current_index + 1) % len(SHAPES)

    def draw_quiz(self):
        self.screen.fill(BG_COLOR)
        draw_text(self.screen, 'Mode Kuis: Pilih nama yang benar', 26, WIDTH//2, 50)
        # draw target picture
        cx, cy = WIDTH//2, 220
        shape = self.quiz_question
        if shape == 'Lingkaran':
            draw_lingkaran(self.screen, (cx, cy), 70, PRIMARY)
        elif shape == 'Persegi':
            draw_persegi(self.screen, (cx-70//2, cy-70//2), 70, PRIMARY)
        elif shape == 'Persegi Panjang':
            draw_persegi_panjang(self.screen, (cx-110, cy-45), 220, 90, PRIMARY)
        elif shape == 'Segitiga':
            pts = [(cx, cy-80), (cx-70, cy+40), (cx+70, cy+40)]
            draw_segitiga(self.screen, pts, PRIMARY)
        elif shape == 'Jajargenjang':
            draw_jajargenjang(self.screen, (cx-90, cy-45), 180, 90, 30, PRIMARY)
        elif shape == 'Layang-layang':
            draw_layang(self.screen, (cx, cy), 140, 120, PRIMARY)

        # option buttons
        btns = []
        start_x = WIDTH//2 - 320
        for i,opt in enumerate(self.quiz_options):
            b = Button((start_x + i*220, 420, 200, 80), opt, lambda o=opt: self.check_quiz(o))
            b.draw(self.screen)
            btns.append(b)

        back_btn = Button((WIDTH-190, HEIGHT-120, 120, 60), 'Menu', lambda: self.change_mode('menu'))
        back_btn.draw(self.screen)

    def draw_drag(self):
        self.screen.fill(BG_COLOR)
        draw_text(self.screen, 'Seret & Cocokkan: Seret bentuk ke siluet yang sesuai', 22, WIDTH//2, 40)

        # draw targets
        for t in self.targets:
            pygame.draw.rect(self.screen, (230,230,230), t['rect'], border_radius=12)
            draw_silhouette(self.screen, t['kind'], t['rect'])
            draw_text(self.screen, t['kind'], 16, t['rect'].centerx, t['rect'].bottom+18)

        # draw drag items
        for item in self.drag_items:
            r = item['rect']
            kind = item['kind']
            # background box
            pygame.draw.rect(self.screen, (255,255,255), r, border_radius=8)
            pygame.draw.rect(self.screen, (200,200,200), r, 2, border_radius=8)
            cx = r.x + r.w//2
            cy = r.y + r.h//2
            if kind == 'Lingkaran':
                draw_lingkaran(self.screen, (cx, cy), 40, PRIMARY)
            elif kind == 'Persegi':
                draw_persegi(self.screen, (cx-40, cy-40), 80, PRIMARY)
            elif kind == 'Persegi Panjang':
                draw_persegi_panjang(self.screen, (cx-70, cy-30), 140, 60, PRIMARY)
            elif kind == 'Segitiga':
                pts = [(cx, cy-50), (cx-50, cy+30), (cx+50, cy+30)]
                draw_segitiga(self.screen, pts, PRIMARY)
            elif kind == 'Jajargenjang':
                draw_jajargenjang(self.screen, (cx-60, cy-40), 120, 80, 20, PRIMARY)
            elif kind == 'Layang-layang':
                draw_layang(self.screen, (cx, cy), 100, 80, PRIMARY)

            draw_text(self.screen, kind, 14, cx, r.bottom+14)

        self.btn_back.draw(self.screen)


    # -------------------- Event loop --------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)/1000.0
            self.anim_t += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if self.mode == 'menu':
                    for b in [self.btn_learn, self.btn_quiz, self.btn_drag, self.btn_exit]:
                        b.handle(event)
                elif self.mode == 'learn':
                    # buttons recreated each frame; handle mouse click by recreating and calling handle
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mx,my = event.pos
                        # prev
                        if 70 <= mx <= 190 and HEIGHT-120 <= my <= HEIGHT-60:
                            self.prev_shape()
                        # next
                        if WIDTH-190 <= mx <= WIDTH-70 and HEIGHT-120 <= my <= HEIGHT-60:
                            self.next_shape()
                        # menu
                        if WIDTH-360 <= mx <= WIDTH-240 and HEIGHT-120 <= my <= HEIGHT-60:
                            self.change_mode('menu')
                elif self.mode == 'quiz':
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mx,my = event.pos
                        # option buttons region
                        start_x = WIDTH//2 - 320
                        for i,opt in enumerate(self.quiz_options):
                            rect = pygame.Rect(start_x + i*220, 420, 200, 80)
                            if rect.collidepoint((mx,my)):
                                self.check_quiz(opt)
                        # menu
                        if WIDTH-190 <= mx <= WIDTH-70 and HEIGHT-120 <= my <= HEIGHT-60:
                            self.change_mode('menu')
                elif self.mode == 'drag':
                    self.btn_back.handle(event)
                    
                    
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for item in self.drag_items:
                            if item['rect'].collidepoint(event.pos) and not getattr(item, 'locked', False):
                                item['dragging'] = True
                                mx,my = event.pos
                                item['offset'] = (item['rect'].x - mx, item['rect'].y - my)
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        for item in self.drag_items:
                            if item.get('dragging'):
                                item['dragging'] = False
                                # check if dropped on correct target
                                placed = False
                                for t in self.targets:
                                    if t['rect'].collidepoint(item['rect'].center) and not t['done'] and t['kind'] == item['kind']:
                                        t['done'] = True
                                        item['rect'].topleft = (t['rect'].x + (t['rect'].w-item['rect'].w)//2, t['rect'].y + (t['rect'].h-item['rect'].h)//2)
                                        item['locked'] = True
                                        placed = True
                                        self.correct_sound.play()
                                        break
                                if not placed:
                                    # snap back
                                    item['rect'].topleft = tuple(item['pos'])
                                    self.wrong_sound.play()
                    if event.type == pygame.MOUSEMOTION:
                        for item in self.drag_items:
                            if item.get('dragging'):
                                mx,my = event.pos
                                ox,oy = item['offset']
                                item['rect'].x = mx + ox
                                item['rect'].y = my + oy

            # draw
            if self.mode == 'menu':
                self.draw_menu()
            elif self.mode == 'learn':
                self.draw_learn()
            elif self.mode == 'quiz':
                self.draw_quiz()
            elif self.mode == 'drag':
                self.draw_drag()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == '__main__':
    app = GeometryApp()
    app.run()
