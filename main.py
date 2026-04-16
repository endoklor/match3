"""
Игра "Три в ряд" - Royal Kingdom Style (Enhanced Edition)
Автор: Claude

Управление:
  - Левая кнопка мыши: выбор фигуры / обмен с соседней
  - ESC: пауза
  - R: перезапуск (во время игры)

Структура кода:
  - КОНСТАНТЫ И ЦВЕТА
  - ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ (Button, Animation)
  - РЕНДЕРИНГ (загрузка изображений, отрисовка самоцветов)
  - СИСТЕМА ЧАСТИЦ
  - ВСПЛЫВАЮЩИЙ СЧЁТ
  - ПЛИТКА (один самоцвет)
  - ДОСКА (логика match-3)
  - МЕНЮ (главное, выбор режима, пауза)
  - ИГРА (основной класс)
  - ТОЧКА ВХОДА
"""

import pygame
import sys
import random
import math
import os

# ─────────────────────────────────────────
#  КОНСТАНТЫ
# ─────────────────────────────────────────

SCREEN_WIDTH   = 960
SCREEN_HEIGHT  = 780
COLUMNS        = 8
ROWS           = 8
CELL_SIZE      = 72
BOARD_OFFSET_X = (SCREEN_WIDTH - COLUMNS * CELL_SIZE) // 2
BOARD_OFFSET_Y = 130
FPS            = 60

# Режимы игры
MODE_LEVELS   = "levels"
MODE_ENDLESS  = "endless"

# Параметры режима уровней
MAX_MOVES_LEVEL   = 40
GOAL_ELEMENTS     = 20   # собрать 20 элементов gem_0 (тип 0)
GOAL_TYPE         = 0    # какой тип gem нужно собрать

# Типы бонусов
NO_BONUS    = 0
BONUS_LINE  = 1   # 4 в ряд
BONUS_BOMB  = 2   # 5 в ряд Г-образно или бомба
BONUS_COLOR = 3   # 5 в ряд: уничтожает все самоцветы одного цвета

# Скорость анимации
FALL_SPEED = 18

# Цвета
COLOR_BG         = (8, 10, 28)
COLOR_BOARD_BG   = (18, 22, 52)
COLOR_GRID       = (28, 36, 76)
COLOR_WHITE      = (255, 255, 255)
COLOR_GOLD       = (255, 210, 60)
COLOR_RED        = (230, 70, 70)
COLOR_GREEN      = (80, 220, 120)
COLOR_PANEL      = (14, 18, 46)
COLOR_TEXT_MAIN  = (220, 235, 255)
COLOR_TEXT_SUB   = (110, 135, 195)
COLOR_BTN_BG     = (36, 52, 120)
COLOR_BTN_HOV    = (58, 82, 185)
COLOR_BTN_ACT    = (80, 120, 220)
COLOR_BTN_TEXT   = (210, 230, 255)

GEM_COLORS = [
    (230,  65,  65),
    ( 55, 145, 235),
    ( 55, 210, 100),
    (235, 190,  45),
    (190,  60, 230),
    (235, 125,  45),
    ( 55, 220, 220),
    (230,  80, 150),
]


# ─────────────────────────────────────────
#  ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ
# ─────────────────────────────────────────

def ease_in_out(t: float) -> float:
    """Функция easing: плавный вход и выход."""
    return t * t * (3.0 - 2.0 * t)

def lerp(a: float, b: float, t: float) -> float:
    """Линейная интерполяция."""
    return a + (b - a) * t


class Button:
    """
    Универсальная кнопка с hover-эффектами и анимацией нажатия.
    """
    def __init__(self, x: int, y: int, w: int, h: int, text: str,
                 font: pygame.font.Font,
                 color_normal=COLOR_BTN_BG,
                 color_hover=COLOR_BTN_HOV,
                 color_text=COLOR_BTN_TEXT):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.color_normal = color_normal
        self.color_hover  = color_hover
        self.color_text   = color_text
        self.hover        = False
        self.pressed      = False
        self.press_anim   = 0.0   # 0..1, плавное нажатие
        self.alpha        = 255   # для fade-in

    def update(self, mx: int, my: int):
        self.hover = self.rect.collidepoint(mx, my)
        if self.pressed:
            self.press_anim = min(1.0, self.press_anim + 0.15)
        else:
            self.press_anim = max(0.0, self.press_anim - 0.1)
        self.pressed = False

    def check_click(self, mx: int, my: int) -> bool:
        if self.rect.collidepoint(mx, my):
            self.pressed = True
            return True
        return False

    def draw(self, screen: pygame.Surface):
        # Цвет с учётом hover
        if self.hover:
            color = self.color_hover
        else:
            color = self.color_normal

        # Смещение при нажатии
        offset = int(self.press_anim * 2)
        rect = self.rect.move(0, offset)

        # Тень
        shadow = pygame.Surface((rect.w + 4, rect.h + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 80),
                         (2, 4, rect.w, rect.h), border_radius=12)
        screen.blit(shadow, (rect.x - 2, rect.y - 2))

        # Фон кнопки
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*color, self.alpha),
                         (0, 0, rect.w, rect.h), border_radius=12)

        # Блик сверху
        glare = pygame.Surface((rect.w, rect.h // 2), pygame.SRCALPHA)
        pygame.draw.rect(glare, (255, 255, 255, 25),
                         (0, 0, rect.w, rect.h // 2), border_radius=12)
        surf.blit(glare, (0, 0))

        # Рамка
        pygame.draw.rect(surf, (255, 255, 255, 40 if self.hover else 20),
                         (0, 0, rect.w, rect.h), border_radius=12, width=1)

        screen.blit(surf, (rect.x, rect.y))

        # Текст
        txt = self.font.render(self.text, True, self.color_text)
        screen.blit(txt, (
            rect.x + (rect.w - txt.get_width()) // 2,
            rect.y + (rect.h - txt.get_height()) // 2))


class FadeOverlay:
    """Плавное появление/исчезновение экрана (fade-in / fade-out)."""
    def __init__(self, from_alpha: int = 255, to_alpha: int = 0, speed: float = 8.0):
        self.alpha    = float(from_alpha)
        self.target   = float(to_alpha)
        self.speed    = speed
        self.finished = False

    def update(self):
        diff = self.target - self.alpha
        if abs(diff) < 1.0:
            self.alpha    = self.target
            self.finished = True
        else:
            self.alpha += diff * 0.12

    def draw(self, screen: pygame.Surface):
        if self.alpha > 0:
            s = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            s.fill((0, 0, 0, int(self.alpha)))
            screen.blit(s, (0, 0))


# ─────────────────────────────────────────
#  ЗАГРУЗКА ИЗОБРАЖЕНИЙ / СОЗДАНИЕ ФИГУР
# ─────────────────────────────────────────

def create_gem_surface(gem_type: int, size: int) -> pygame.Surface:
    """
    Пытается загрузить assets/gem_{gem_type}.png.
    Если файл не найден — создаёт процедурную фигуру.
    """
    path = os.path.join("assets", f"gem_{gem_type}.png")
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(img, (size, size))
        except Exception:
            pass
    # Fallback: процедурная отрисовка
    return _create_procedural_gem(gem_type, size)


def _create_procedural_gem(gem_type: int, size: int) -> pygame.Surface:
    """Процедурная отрисовка самоцвета (fallback)."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    color = GEM_COLORS[gem_type]
    cx, cy = size // 2, size // 2
    r = size // 2 - 5

    shapes = ["circle", "square", "diamond", "hexagon",
              "triangle", "star", "cross", "rounded_square"]
    shape = shapes[gem_type % len(shapes)]

    shadow = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(shadow, (0, 0, 0, 55), (cx + 2, cy + 3), r)
    surf.blit(shadow, (0, 0))

    darker  = tuple(max(0, c - 50) for c in color)
    lighter = tuple(min(255, c + 70) for c in color)

    if shape == "circle":
        pygame.draw.circle(surf, darker, (cx, cy), r)
        pygame.draw.circle(surf, color, (cx, cy), r - 2)
    elif shape == "square":
        rect = pygame.Rect(5, 5, size - 10, size - 10)
        pygame.draw.rect(surf, darker, rect, border_radius=8)
        pygame.draw.rect(surf, color, rect.inflate(-4, -4), border_radius=6)
    elif shape == "diamond":
        pts = [(cx, 5), (size - 5, cy), (cx, size - 5), (5, cy)]
        pygame.draw.polygon(surf, darker, pts)
        inner = [(cx, 10), (size - 10, cy), (cx, size - 10), (10, cy)]
        pygame.draw.polygon(surf, color, inner)
    elif shape == "hexagon":
        pts = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        pygame.draw.polygon(surf, darker, pts)
        inner_pts = [(cx + (r-4)*math.cos(math.radians(60*i-30)),
                      cy + (r-4)*math.sin(math.radians(60*i-30))) for i in range(6)]
        pygame.draw.polygon(surf, color, inner_pts)
    elif shape == "triangle":
        pts = [(cx, 5), (size - 5, size - 5), (5, size - 5)]
        pygame.draw.polygon(surf, darker, pts)
        inner = [(cx, 12), (size - 12, size - 12), (12, size - 12)]
        pygame.draw.polygon(surf, color, inner)
    elif shape == "star":
        outer, inner_r = r, r // 2
        pts  = [(cx + (outer if i%2==0 else inner_r)*math.cos(math.radians(36*i-90)),
                 cy + (outer if i%2==0 else inner_r)*math.sin(math.radians(36*i-90))) for i in range(10)]
        pts2 = [(cx + ((outer-3) if i%2==0 else (inner_r-2))*math.cos(math.radians(36*i-90)),
                 cy + ((outer-3) if i%2==0 else (inner_r-2))*math.sin(math.radians(36*i-90))) for i in range(10)]
        pygame.draw.polygon(surf, darker, pts)
        pygame.draw.polygon(surf, color, pts2)
    elif shape == "cross":
        w = size // 3
        pygame.draw.rect(surf, darker, (cx - w//2 - 1, 4, w+2, size-8))
        pygame.draw.rect(surf, darker, (4, cy - w//2 - 1, size-8, w+2))
        pygame.draw.rect(surf, color,  (cx - w//2, 5, w, size-10))
        pygame.draw.rect(surf, color,  (5, cy - w//2, size-10, w))
    elif shape == "rounded_square":
        rect = pygame.Rect(5, 5, size - 10, size - 10)
        pygame.draw.rect(surf, darker, rect, border_radius=16)
        pygame.draw.rect(surf, color, rect.inflate(-4, -4), border_radius=14)

    glare = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.ellipse(glare, (255, 255, 255, 65),
                        (cx - r//2, cy - r//2, r, r//2))
    surf.blit(glare, (0, 0))
    return surf


# ─────────────────────────────────────────
#  СИСТЕМА ЧАСТИЦ
# ─────────────────────────────────────────

class Particle:
    def __init__(self, x: float, y: float, color: tuple):
        self.x = x
        self.y = y
        speed = random.uniform(2.0, 7.0)
        angle = random.uniform(0, 2 * math.pi)
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.life     = random.randint(25, 50)
        self.max_life = self.life
        self.color    = color
        self.size     = random.randint(3, 7)

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.25
        self.life -= 1

    def draw(self, screen: pygame.Surface):
        if self.life <= 0:
            return
        alpha = int(255 * self.life / self.max_life)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha),
                           (self.size, self.size), self.size)
        screen.blit(s, (int(self.x - self.size), int(self.y - self.size)))

    @property
    def alive(self):
        return self.life > 0


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def emit(self, x: float, y: float, color: tuple, count: int = 12):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def update(self):
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update()

    def draw(self, screen: pygame.Surface):
        for p in self.particles:
            p.draw(screen)


# ─────────────────────────────────────────
#  ВСПЛЫВАЮЩИЙ СЧЁТ
# ─────────────────────────────────────────

class FloatingScore:
    def __init__(self, x: float, y: float, value: int, combo: int = 1):
        self.x        = x
        self.y        = y
        self.value    = value
        self.combo    = combo
        self.life     = 70
        self.max_life = 70

    def update(self):
        self.y    -= 1.2
        self.life -= 1

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        if self.life <= 0:
            return
        alpha = int(255 * self.life / self.max_life)
        text  = f"+{self.value}"
        if self.combo > 1:
            text += f"   x{self.combo} COMBO!"
        color   = COLOR_GOLD if self.combo > 1 else COLOR_WHITE
        label   = font.render(text, True, color)
        s = pygame.Surface(label.get_size(), pygame.SRCALPHA)
        s.blit(label, (0, 0))
        s.set_alpha(alpha)
        screen.blit(s, (int(self.x - label.get_width() // 2), int(self.y)))

    @property
    def alive(self):
        return self.life > 0


# ─────────────────────────────────────────
#  ПЛИТКА (один самоцвет)
# ─────────────────────────────────────────

class Tile:
    """
    Один самоцвет на доске.
    Использует easing для плавного перемещения (без jitter/shake).
    Бонус хранится как отдельное состояние; активируется при следующем совпадении.
    """

    def __init__(self, gem_type: int, row: int, col: int):
        self.type   = gem_type
        self.row    = row
        self.col    = col
        self.bonus  = NO_BONUS
        self.bonus_active = False   # бонус-фигура создана, ждёт активации

        self.target_x  = float(col * CELL_SIZE + BOARD_OFFSET_X)
        self.target_y  = float(row * CELL_SIZE + BOARD_OFFSET_Y)
        self.pixel_x   = self.target_x
        self.pixel_y   = self.target_y

        self.alpha      = 255
        self.scale      = 1.0
        self.destroying = False
        self.falling    = False
        self.selected   = False

        # easing: сохраняем начальную позицию для интерполяции
        self._start_x:    float = self.pixel_x
        self._start_y:    float = self.pixel_y
        self._progress:   float = 1.0   # 0..1, 1 = достигли цели

    def update_target(self):
        """Пересчитать целевую позицию; сбросить easing-прогресс."""
        new_x = float(self.col * CELL_SIZE + BOARD_OFFSET_X)
        new_y = float(self.row * CELL_SIZE + BOARD_OFFSET_Y)
        if new_x != self.target_x or new_y != self.target_y:
            self._start_x   = self.pixel_x
            self._start_y   = self.pixel_y
            self.target_x   = new_x
            self.target_y   = new_y
            self._progress  = 0.0

    def move_to_target(self, speed: float = FALL_SPEED) -> bool:
        """
        Плавное easing-перемещение к цели.
        Возвращает True, если достигли цели.
        """
        if self._progress >= 1.0:
            self.pixel_x = self.target_x
            self.pixel_y = self.target_y
            self.falling = False
            return True

        # Мягкая динамическая скорость (уменьшенная резкость)
        dist = math.hypot(self.target_x - self.pixel_x,
                          self.target_y - self.pixel_y)
        step = max(0.03, min(0.18, dist / 320.0))
        self._progress = min(1.0, self._progress + step)

        t = ease_in_out(self._progress)
        self.pixel_x = lerp(self._start_x, self.target_x, t)
        self.pixel_y = lerp(self._start_y, self.target_y, t)

        if self._progress >= 1.0:
            self.pixel_x = self.target_x
            self.pixel_y = self.target_y
            self.falling = False
            return True
        return False

    @property
    def in_place(self) -> bool:
        return self._progress >= 1.0

    def draw(self, screen: pygame.Surface,
             surfaces: list, tick: int):
        if self.alpha <= 0:
            return

        base_surf = surfaces[self.type]
        size      = int(CELL_SIZE * self.scale)
        if size <= 2:
            return

        # Покачивание УДАЛЕНО — фигуры стоят идеально ровно

        if size != base_surf.get_width():
            rendered = pygame.transform.smoothscale(base_surf, (size, size))
        else:
            rendered = base_surf.copy()

        if self.alpha < 255:
            rendered.set_alpha(self.alpha)

        draw_x = int(self.pixel_x + (CELL_SIZE - size) // 2)
        draw_y = int(self.pixel_y + (CELL_SIZE - size) // 2)

        # Рамка выбора
        if self.selected:
            frame = pygame.Surface((CELL_SIZE + 8, CELL_SIZE + 8), pygame.SRCALPHA)
            pygame.draw.rect(frame, (255, 245, 80, 210),
                             (0, 0, CELL_SIZE + 8, CELL_SIZE + 8),
                             border_radius=12, width=3)
            screen.blit(frame, (int(self.pixel_x) - 4,
                                int(self.pixel_y) - 4))

        screen.blit(rendered, (draw_x, draw_y))

        # Значок бонуса (отображается поверх изображения)
        if self.bonus == BONUS_LINE:
            self._draw_badge(screen, draw_x, draw_y, size, "L", (80, 220, 255))
        elif self.bonus == BONUS_BOMB:
            self._draw_badge(screen, draw_x, draw_y, size, "B", (255, 90, 90))
        elif self.bonus == BONUS_COLOR:
            self._draw_badge(screen, draw_x, draw_y, size, "C", (255, 240, 80))

    @staticmethod
    def _draw_badge(screen, x, y, size, letter: str, color: tuple):
        font  = pygame.font.SysFont("Arial", 13, bold=True)
        badge = pygame.Surface((22, 22), pygame.SRCALPHA)
        pygame.draw.circle(badge, (*color, 230), (11, 11), 11)
        txt = font.render(letter, True, (10, 10, 10))
        badge.blit(txt, (11 - txt.get_width()//2, 11 - txt.get_height()//2))
        screen.blit(badge, (x + size - 14, y))


# ─────────────────────────────────────────
#  ДОСКА (логика match-3)
# ─────────────────────────────────────────

class Board:
    """
    Управляет сеткой 8x8: поиск совпадений, гравитация, бонусы.
    Бонусные плитки создаются, но активируются только при следующем совпадении.
    """

    def __init__(self):
        self.grid: list[list["Tile | None"]] = []
        self._initialize()

    def _initialize(self):
        self.grid = [[None] * COLUMNS for _ in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLUMNS):
                self.grid[r][c] = self._create_tile(r, c, avoid_match=True)

    def _random_type(self) -> int:
        return random.randint(0, len(GEM_COLORS) - 1)

    def _create_tile(self, row: int, col: int,
                     avoid_match: bool = False) -> Tile:
        attempts = 0
        while True:
            gem_type = self._random_type()
            if avoid_match and attempts < 25:
                if (col >= 2
                        and self.grid[row][col-1] is not None
                        and self.grid[row][col-2] is not None
                        and self.grid[row][col-1].type == gem_type
                        and self.grid[row][col-2].type == gem_type):
                    attempts += 1; continue
                if (row >= 2
                        and self.grid[row-1][col] is not None
                        and self.grid[row-2][col] is not None
                        and self.grid[row-1][col].type == gem_type
                        and self.grid[row-2][col].type == gem_type):
                    attempts += 1; continue
            break
        return Tile(gem_type, row, col)

    def get(self, r: int, c: int) -> "Tile | None":
        if 0 <= r < ROWS and 0 <= c < COLUMNS:
            return self.grid[r][c]
        return None

    def swap(self, r1: int, c1: int, r2: int, c2: int):
        a = self.grid[r1][c1]
        b = self.grid[r2][c2]
        self.grid[r1][c1] = b
        self.grid[r2][c2] = a
        if a:
            a.row, a.col = r2, c2
            a.update_target()
            a.falling = True
        if b:
            b.row, b.col = r1, c1
            b.update_target()
            b.falling = True

    # ── Поиск совпадений ──

    def find_matches(self) -> set:
        """
        Возвращает множество (r,c) всех ячеек, участвующих в совпадении.
        Назначает бонус в центральную плитку серии, но НЕ активирует немедленно.
        """
        matched = set()

        def _process_run(run: list, horizontal: bool, fixed: int):
            if len(run) < 3:
                return
            for pos in run:
                if horizontal:
                    matched.add((fixed, pos))
                else:
                    matched.add((pos, fixed))
            # Назначение бонуса центральной плитке
            mid = run[len(run) // 2]
            if horizontal:
                center = self.grid[fixed][mid]
            else:
                center = self.grid[mid][fixed]
            if center:
                if len(run) >= 5:
                    center.bonus = BONUS_COLOR
                elif len(run) == 4:
                    center.bonus = BONUS_LINE

        # По горизонтали
        for r in range(ROWS):
            c = 0
            while c < COLUMNS:
                tile = self.get(r, c)
                if tile is None:
                    c += 1; continue
                run = [c]
                while (c + 1 < COLUMNS
                       and self.get(r, c+1) is not None
                       and self.get(r, c+1).type == tile.type):
                    c += 1
                    run.append(c)
                _process_run(run, True, r)
                c += 1

        # По вертикали
        for c in range(COLUMNS):
            r = 0
            while r < ROWS:
                tile = self.get(r, c)
                if tile is None:
                    r += 1; continue
                run = [r]
                while (r + 1 < ROWS
                       and self.get(r+1, c) is not None
                       and self.get(r+1, c).type == tile.type):
                    r += 1
                    run.append(r)
                _process_run(run, False, c)
                r += 1

        return matched

    def expand_with_bonuses(self, cells: set) -> set:
        """
        Активирует бонусы плиток, попавших в набор совпадений.
        Бонус активируется только если плитка уже помечена как бонусная (из предыдущего хода).
        """
        extra: set = set()
        color_types: set[int] = set()

        for (r, c) in list(cells):
            tile = self.get(r, c)
            if tile is None:
                continue

            # Активируем только те бонусы, что были созданы ранее
            if not tile.bonus_active:
                continue

            if tile.bonus == BONUS_BOMB:
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < ROWS and 0 <= nc < COLUMNS:
                            extra.add((nr, nc))

            elif tile.bonus == BONUS_LINE:
                for dc in range(COLUMNS):
                    extra.add((r, dc))
                for dr in range(ROWS):
                    extra.add((dr, c))

            elif tile.bonus == BONUS_COLOR:
                color_types.add(tile.type)

        for gem_type in color_types:
            for r in range(ROWS):
                for c in range(COLUMNS):
                    t = self.get(r, c)
                    if t and t.type == gem_type:
                        extra.add((r, c))

        return cells | extra

    def activate_bonuses_in_matches(self, cells: set):
        """
        После поиска совпадений: новые бонусы (созданные в этом ходу)
        помечаются как активные для следующего хода.
        """
        for (r, c) in cells:
            tile = self.get(r, c)
            if tile and tile.bonus != NO_BONUS:
                tile.bonus_active = True

    def mark_destroying(self, cells: set):
        for (r, c) in cells:
            tile = self.get(r, c)
            if tile:
                tile.destroying = True

    def remove_destroyed(self) -> list:
        """Возвращает список (px, py, тип) для частиц."""
        removed = []
        for r in range(ROWS):
            for c in range(COLUMNS):
                tile = self.grid[r][c]
                if tile and tile.destroying:
                    cx = int(tile.pixel_x) + CELL_SIZE // 2
                    cy = int(tile.pixel_y) + CELL_SIZE // 2
                    removed.append((cx, cy, tile.type))
                    self.grid[r][c] = None
        return removed

    def apply_gravity(self) -> bool:
        moved = False
        for c in range(COLUMNS):
            dst = ROWS - 1
            for r in range(ROWS - 1, -1, -1):
                if self.grid[r][c] is not None:
                    if r != dst:
                        self.grid[dst][c] = self.grid[r][c]
                        self.grid[r][c]   = None
                        tile = self.grid[dst][c]
                        tile.row = dst
                        tile.update_target()
                        tile.falling = True
                        moved = True
                    dst -= 1
        return moved

    def fill_empty(self):
        for c in range(COLUMNS):
            offset = -1
            for r in range(ROWS):
                if self.grid[r][c] is None:
                    gem_type = self._random_type()
                    tile = Tile(gem_type, r, c)
                    tile.pixel_y = BOARD_OFFSET_Y + offset * CELL_SIZE
                    tile.pixel_x = tile.target_x
                    # Старт easing от текущей позиции
                    tile._start_x   = tile.pixel_x
                    tile._start_y   = tile.pixel_y
                    tile._progress  = 0.0
                    tile.falling    = True
                    self.grid[r][c] = tile
                    offset -= 1

    def all_in_place(self) -> bool:
        for r in range(ROWS):
            for c in range(COLUMNS):
                t = self.grid[r][c]
                if t and not t.in_place:
                    return False
        return True

    def has_valid_move(self) -> bool:
        for r in range(ROWS):
            for c in range(COLUMNS):
                for dr, dc in [(0, 1), (1, 0)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < ROWS and 0 <= nc < COLUMNS:
                        self.swap(r, c, nr, nc)
                        matched = self.find_matches()
                        self.swap(r, c, nr, nc)
                        if matched:
                            return True
        return False

    def update_fall_animation(self):
        for r in range(ROWS):
            for c in range(COLUMNS):
                t = self.grid[r][c]
                if t and t.falling:
                    t.move_to_target()

    def update_destroy_animation(self) -> bool:
        all_done = True
        for r in range(ROWS):
            for c in range(COLUMNS):
                t = self.grid[r][c]
                if t and t.destroying:
                    t.scale = max(0.0, t.scale - 0.09)
                    t.alpha = max(0, t.alpha - 22)
                    if t.scale > 0.05:
                        all_done = False
        return all_done

    def shuffle(self):
        flat = [self.grid[r][c] for r in range(ROWS)
                for c in range(COLUMNS) if self.grid[r][c]]
        random.shuffle(flat)
        idx = 0
        for r in range(ROWS):
            for c in range(COLUMNS):
                if idx < len(flat):
                    flat[idx].row = r
                    flat[idx].col = c
                    flat[idx].update_target()
                    flat[idx].falling = True
                    self.grid[r][c] = flat[idx]
                    idx += 1


# ─────────────────────────────────────────
#  СОСТОЯНИЯ ИГРЫ
# ─────────────────────────────────────────

class State:
    MENU        = "menu"
    MODE_SELECT = "mode_select"
    WAITING     = "waiting"
    SWAP        = "swap"
    DESTROY     = "destroy"
    FALL        = "fall"
    CHECK       = "check"
    PAUSE       = "pause"
    GAME_OVER   = "game_over"
    VICTORY     = "victory"


# ─────────────────────────────────────────
#  МЕНЮ
# ─────────────────────────────────────────

class MainMenu:
    """Главное меню с анимацией появления."""

    def __init__(self, font_big: pygame.font.Font,
                 font_mid: pygame.font.Font,
                 font_sm: pygame.font.Font):
        cx = SCREEN_WIDTH // 2
        self.buttons = [
            Button(cx - 110, 370, 220, 58, "ИГРАТЬ",  font_mid,
                   (40, 100, 55), (55, 145, 75)),
            Button(cx - 110, 450, 220, 58, "ВЫХОД",   font_mid,
                   (100, 40, 40), (150, 55, 55)),
        ]
        self.font_big = font_big
        self.font_mid = font_mid
        self.font_sm  = font_sm
        self.fade     = FadeOverlay(255, 0, 10.0)
        self.tick     = 0

    def update(self, mx: int, my: int):
        self.tick += 1
        self.fade.update()
        for btn in self.buttons:
            btn.update(mx, my)

    def handle_click(self, mx: int, my: int) -> str | None:
        for btn in self.buttons:
            if btn.check_click(mx, my):
                return btn.text
        return None

    def draw(self, screen: pygame.Surface):
        screen.fill(COLOR_BG)
        # Звёзды
        for i in range(60):
            x = (i * 139 + 70) % SCREEN_WIDTH
            y = (i * 103 + 50) % SCREEN_HEIGHT
            blink = 0.5 + 0.5 * math.sin(self.tick * 0.022 + i * 0.85)
            alpha = int(80 * blink)
            r = 1 + (i % 3)
            s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (180, 205, 255, alpha), (r+1, r+1), r)
            screen.blit(s, (x, y))

        # Заголовок с тенью
        title  = self.font_big.render("ТРИ В РЯД", True, COLOR_GOLD)
        shadow = self.font_big.render("ТРИ В РЯД", True, (60, 40, 0))
        cx = SCREEN_WIDTH // 2
        screen.blit(shadow, (cx - title.get_width()//2 + 3, 203))
        screen.blit(title,  (cx - title.get_width()//2, 200))

        # Подзаголовок
        sub = self.font_sm.render("Royal Kingdom Style", True, COLOR_TEXT_SUB)
        screen.blit(sub, (cx - sub.get_width()//2, 275))

        # Декоративная линия
        pygame.draw.line(screen, COLOR_GOLD, (cx - 150, 320), (cx + 150, 320), 2)

        for btn in self.buttons:
            btn.draw(screen)

        self.fade.draw(screen)


class ModeSelectMenu:
    """Меню выбора режима игры."""

    def __init__(self, font_big, font_mid, font_sm):
        cx = SCREEN_WIDTH // 2
        self.buttons = [
            Button(cx - 160, 330, 320, 68, "РЕЖИМ УРОВНЕЙ",     font_mid,
                   (55, 80, 155), (75, 110, 210)),
            Button(cx - 160, 420, 320, 68, "БЕСКОНЕЧНЫЙ РЕЖИМ", font_mid,
                   (55, 115, 60), (75, 155, 80)),
            Button(cx - 110, 520, 220, 52, "← НАЗАД",           font_sm,
                   (70, 70, 70), (100, 100, 100)),
        ]
        self.font_big = font_big
        self.font_mid = font_mid
        self.font_sm  = font_sm
        self.fade     = FadeOverlay(255, 0)
        self.tick     = 0

    def update(self, mx, my):
        self.tick += 1
        self.fade.update()
        for btn in self.buttons:
            btn.update(mx, my)

    def handle_click(self, mx, my) -> str | None:
        for btn in self.buttons:
            if btn.check_click(mx, my):
                return btn.text
        return None

    def draw(self, screen):
        screen.fill(COLOR_BG)
        draw_stars(screen, self.tick, 40)

        title = self.font_big.render("ВЫБОР РЕЖИМА", True, COLOR_GOLD)
        cx    = SCREEN_WIDTH // 2
        screen.blit(title, (cx - title.get_width()//2, 200))
        pygame.draw.line(screen, COLOR_GOLD, (cx - 160, 265), (cx + 160, 265), 2)

        desc_levels  = self.font_sm.render(
            f"Цель: собрать {GOAL_ELEMENTS} красных самоцветов за {MAX_MOVES_LEVEL} ходов", True, COLOR_TEXT_SUB)
        desc_endless = self.font_sm.render(
            "Играй бесконечно — набирай очки без ограничений", True, COLOR_TEXT_SUB)

        screen.blit(desc_levels,  (cx - desc_levels.get_width()//2,  292))
        screen.blit(desc_endless, (cx - desc_endless.get_width()//2, 392))

        for btn in self.buttons:
            btn.draw(screen)
        self.fade.draw(screen)


class PauseMenu:
    """Меню паузы, накладывается поверх игры."""

    def __init__(self, font_big, font_mid, font_sm):
        cx = SCREEN_WIDTH // 2
        self.buttons = [
            Button(cx - 130, 340, 260, 58, "ПРОДОЛЖИТЬ",   font_mid,
                   (40, 100, 55), (55, 145, 75)),
            Button(cx - 130, 420, 260, 58, "ВЫЙТИ В МЕНЮ", font_mid,
                   (100, 40, 40), (150, 55, 55)),
        ]
        self.font_big   = font_big
        self.font_mid   = font_mid
        self.bg_alpha   = 0
        self.target_alpha = 170

    def update(self, mx, my):
        self.bg_alpha = min(self.target_alpha, self.bg_alpha + 12)
        for btn in self.buttons:
            btn.update(mx, my)

    def handle_click(self, mx, my) -> str | None:
        for btn in self.buttons:
            if btn.check_click(mx, my):
                return btn.text
        return None

    def draw(self, screen):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self.bg_alpha))
        screen.blit(overlay, (0, 0))

        cx = SCREEN_WIDTH  // 2
        cy = SCREEN_HEIGHT // 2

        # Панель
        panel = pygame.Surface((360, 280), pygame.SRCALPHA)
        pygame.draw.rect(panel, (14, 18, 50, 230), (0, 0, 360, 280), border_radius=20)
        pygame.draw.rect(panel, (255, 255, 255, 30), (0, 0, 360, 280), border_radius=20, width=2)
        screen.blit(panel, (cx - 180, cy - 160))

        title = self.font_big.render("ПАУЗА", True, COLOR_GOLD)
        screen.blit(title, (cx - title.get_width()//2, cy - 145))

        for btn in self.buttons:
            btn.draw(screen)


# ─────────────────────────────────────────
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ РЕНДЕРИНГА
# ─────────────────────────────────────────

def draw_stars(screen: pygame.Surface, tick: int, count: int = 35):
    """Рисует анимированные звёзды на фоне."""
    for i in range(count):
        x = (i * 139 + 60) % SCREEN_WIDTH
        y = (i * 101 + 40) % SCREEN_HEIGHT
        blink = 0.5 + 0.5 * math.sin(tick * 0.025 + i * 0.9)
        alpha = int(55 * blink)
        r = 1 + (i % 3)
        s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (180, 205, 255, alpha), (r+1, r+1), r)
        screen.blit(s, (x, y))


# ─────────────────────────────────────────
#  ОСНОВНОЙ КЛАСС ИГРЫ
# ─────────────────────────────────────────

class Game:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock  = pygame.time.Clock()
        self.tick   = 0

        # Шрифты
        self.font_big  = pygame.font.SysFont("Segoe UI", 44, bold=True)
        self.font_mid  = pygame.font.SysFont("Segoe UI", 28, bold=True)
        self.font_sm   = pygame.font.SysFont("Segoe UI", 18)
        self.font_pop  = pygame.font.SysFont("Segoe UI", 22, bold=True)

        # Изображения самоцветов
        self.surfaces = [
            create_gem_surface(i, CELL_SIZE - 8)
            for i in range(len(GEM_COLORS))
        ]

        # Состояние верхнего уровня
        self.state     = State.MENU
        self.game_mode = MODE_LEVELS

        # Меню
        self.main_menu    = MainMenu(self.font_big, self.font_mid, self.font_sm)
        self.mode_menu    = ModeSelectMenu(self.font_big, self.font_mid, self.font_sm)
        self.pause_menu   = PauseMenu(self.font_big, self.font_mid, self.font_sm)
        self.prev_state   = None  # состояние до паузы

        # Игровые переменные (инициализируются при запуске игры)
        self.board          = None
        self.score          = 0    # обычный int, без ограничений
        self.moves_left     = MAX_MOVES_LEVEL
        self.combo          = 0
        self.selected       = None
        self.particles      = ParticleSystem()
        self.floating       = []
        self.goal_collected = 0   # для режима уровней

        # Фейд переходов
        self.fade_in = None

    # ── Запуск новой игры ──

    def _start_game(self, mode: str):
        self.game_mode      = mode
        self.board          = Board()
        self.score          = 0
        self.moves_left     = MAX_MOVES_LEVEL
        self.combo          = 0
        self.selected       = None
        self.particles      = ParticleSystem()
        self.floating       = []
        self.goal_collected = 0
        self.pause_menu     = PauseMenu(self.font_big, self.font_mid, self.font_sm)
        self.state          = State.WAITING
        self.fade_in        = FadeOverlay(255, 0)

    def _return_to_menu(self):
        self.state    = State.MENU
        self.main_menu = MainMenu(self.font_big, self.font_mid, self.font_sm)

    # ── Главный цикл ──

    def run(self):
        while True:
            self.clock.tick(FPS)
            self.tick += 1
            mx, my = pygame.mouse.get_pos()
            self._handle_events(mx, my)
            self._update(mx, my)
            self._draw()
            pygame.display.flip()

    # ── Обработка событий ──

    def _handle_events(self, mx: int, my: int):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # Пауза по ESC
                if event.key == pygame.K_ESCAPE:
                    if self.state == State.PAUSE:
                        self.state = self.prev_state
                    elif self.state not in (State.MENU, State.MODE_SELECT,
                                            State.GAME_OVER, State.VICTORY):
                        self.prev_state = self.state
                        self.state = State.PAUSE

                # Перезапуск по R (только в игре)
                if event.key == pygame.K_r:
                    if self.state not in (State.MENU, State.MODE_SELECT):
                        self._start_game(self.game_mode)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(mx, my)

    def _handle_click(self, mx: int, my: int):
        # ── Главное меню ──
        if self.state == State.MENU:
            result = self.main_menu.handle_click(mx, my)
            if result == "ИГРАТЬ":
                self.state     = State.MODE_SELECT
                self.mode_menu = ModeSelectMenu(
                    self.font_big, self.font_mid, self.font_sm)
            elif result == "ВЫХОД":
                pygame.quit()
                sys.exit()
            return

        # ── Выбор режима ──
        if self.state == State.MODE_SELECT:
            result = self.mode_menu.handle_click(mx, my)
            if result == "РЕЖИМ УРОВНЕЙ":
                self._start_game(MODE_LEVELS)
            elif result == "БЕСКОНЕЧНЫЙ РЕЖИМ":
                self._start_game(MODE_ENDLESS)
            elif result == "← НАЗАД":
                self._return_to_menu()
            return

        # ── Пауза ──
        if self.state == State.PAUSE:
            result = self.pause_menu.handle_click(mx, my)
            if result == "ПРОДОЛЖИТЬ":
                self.state = self.prev_state
            elif result == "ВЫЙТИ В МЕНЮ":
                self._return_to_menu()
            return

        # ── Конец / Победа — клик перезапускает ──
        if self.state in (State.GAME_OVER, State.VICTORY):
            self._start_game(self.game_mode)
            return

        # ── Игровой экран ──
        if self.state != State.WAITING:
            return

        # Кнопка рестарта
        if pygame.Rect(SCREEN_WIDTH - 148, 32, 128, 46).collidepoint(mx, my):
            self._start_game(self.game_mode)
            return

        # Клик по доске
        col = (mx - BOARD_OFFSET_X) // CELL_SIZE
        row = (my - BOARD_OFFSET_Y) // CELL_SIZE

        if not (0 <= row < ROWS and 0 <= col < COLUMNS):
            self._deselect()
            return

        if self.selected is None:
            tile = self.board.get(row, col)
            if tile:
                self.selected  = (row, col)
                tile.selected  = True
        else:
            sr, sc = self.selected
            prev = self.board.get(sr, sc)
            if prev:
                prev.selected = False

            if (abs(row - sr) == 1 and col == sc) or \
               (abs(col - sc) == 1 and row == sr):
                self._try_swap(sr, sc, row, col)
            elif row == sr and col == sc:
                pass
            else:
                new_tile = self.board.get(row, col)
                if new_tile:
                    self.selected     = (row, col)
                    new_tile.selected = True
                    return
            self.selected = None

    def _deselect(self):
        if self.selected is not None:
            sr, sc = self.selected
            t = self.board.get(sr, sc)
            if t:
                t.selected = False
            self.selected = None

    def _try_swap(self, r1: int, c1: int, r2: int, c2: int):
        self.board.swap(r1, c1, r2, c2)
        matched = self.board.find_matches()
        if matched:
            if self.game_mode == MODE_LEVELS:
                self.moves_left -= 1
            self.combo = 0
            self.state = State.SWAP
        else:
            # Откат
            self.board.swap(r1, c1, r2, c2)
            for r, c in [(r1, c1), (r2, c2)]:
                t = self.board.get(r, c)
                if t:
                    t.update_target()
                    t.falling = True

    # ── Обновление состояния ──

    def _update(self, mx: int, my: int):
        if self.state == State.MENU:
            self.main_menu.update(mx, my)
            return
        if self.state == State.MODE_SELECT:
            self.mode_menu.update(mx, my)
            return
        if self.state == State.PAUSE:
            self.pause_menu.update(mx, my)
            return

        # Фейд при переходе в игру
        if self.fade_in and not self.fade_in.finished:
            self.fade_in.update()

        if self.board is None:
            return

        self.board.update_fall_animation()
        self.particles.update()
        self.floating = [v for v in self.floating if v.alive]
        for v in self.floating:
            v.update()

        if self.state == State.SWAP:
            if self.board.all_in_place():
                self.state = State.CHECK

        elif self.state == State.CHECK:
            matched = self.board.find_matches()
            if matched:
                expanded = self.board.expand_with_bonuses(matched)
                # Помечаем новые бонусы как активные для следующего хода
                self.board.activate_bonuses_in_matches(matched)
                self.board.mark_destroying(expanded)
                self._add_score(expanded)
                # Подсчёт для режима уровней
                if self.game_mode == MODE_LEVELS:
                    for (r, c) in expanded:
                        t = self.board.get(r, c)
                        if t and t.type == GOAL_TYPE:
                            self.goal_collected += 1
                self.state = State.DESTROY
            else:
                self.combo = 0
                self.state = State.WAITING
                self._check_end()

        elif self.state == State.DESTROY:
            done = self.board.update_destroy_animation()
            if done:
                removed = self.board.remove_destroyed()
                for (px, py, gem_type) in removed:
                    self.particles.emit(px, py, GEM_COLORS[gem_type], count=14)
                self.board.apply_gravity()
                self.board.fill_empty()
                self.state = State.FALL

        elif self.state == State.FALL:
            if self.board.all_in_place():
                self.state = State.CHECK

    def _add_score(self, cells: set):
        self.combo += 1
        base  = len(cells) * 55
        total = base * self.combo
        self.score += total   # обычный int, без ограничений

        cx = BOARD_OFFSET_X + COLUMNS * CELL_SIZE // 2
        cy = BOARD_OFFSET_Y + ROWS    * CELL_SIZE // 2
        self.floating.append(FloatingScore(cx, cy - 50, total, self.combo))

    def _check_end(self):
        if self.game_mode == MODE_LEVELS:
            if self.goal_collected >= GOAL_ELEMENTS:
                self.state = State.VICTORY
            elif self.moves_left <= 0:
                self.state = State.GAME_OVER
            elif not self.board.has_valid_move():
                self.board.shuffle()
                self.state = State.FALL
        else:
            # Бесконечный режим — только перемешивание если нет ходов
            if not self.board.has_valid_move():
                self.board.shuffle()
                self.state = State.FALL

    # ── Отрисовка ──

    def _draw(self):
        if self.state == State.MENU:
            self.main_menu.draw(self.screen)
            return
        if self.state == State.MODE_SELECT:
            self.mode_menu.draw(self.screen)
            return

        # Игровой экран
        self.screen.fill(COLOR_BG)
        draw_stars(self.screen, self.tick)

        if self.board:
            self._draw_board_bg()
            self._draw_tiles()
            self.particles.draw(self.screen)

        self._draw_ui()
        self._draw_floating()

        # Пауза поверх всего
        if self.state == State.PAUSE:
            self.pause_menu.draw(self.screen)

        # Экраны конца/победы
        if self.state == State.GAME_OVER:
            self._draw_overlay("КОНЕЦ ИГРЫ",
                               "Нажмите R или кликните для перезапуска",
                               COLOR_RED)
        elif self.state == State.VICTORY:
            self._draw_overlay("ПОБЕДА!",
                               "Нажмите R или кликните для перезапуска",
                               COLOR_GOLD)

        # Фейд появления
        if self.fade_in and not self.fade_in.finished:
            self.fade_in.draw(self.screen)

    def _draw_board_bg(self):
        w = COLUMNS * CELL_SIZE
        h = ROWS    * CELL_SIZE
        rect = pygame.Rect(BOARD_OFFSET_X - 10, BOARD_OFFSET_Y - 10, w + 20, h + 20)
        pygame.draw.rect(self.screen, COLOR_BOARD_BG, rect, border_radius=16)
        pygame.draw.rect(self.screen, COLOR_GRID, rect, width=2, border_radius=16)
        for r in range(ROWS):
            for c in range(COLUMNS):
                cell_rect = pygame.Rect(BOARD_OFFSET_X + c * CELL_SIZE,
                                        BOARD_OFFSET_Y + r * CELL_SIZE,
                                        CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, COLOR_GRID, cell_rect, width=1)

    def _draw_tiles(self):
        for r in range(ROWS):
            for c in range(COLUMNS):
                tile = self.board.get(r, c)
                if tile:
                    tile.draw(self.screen, self.surfaces, self.tick)

    def _draw_ui(self):
        # Верхняя панель
        panel = pygame.Surface((SCREEN_WIDTH, 112), pygame.SRCALPHA)
        panel.fill((*COLOR_PANEL, 215))
        self.screen.blit(panel, (0, 0))

        # Режим
        mode_text = "УРОВЕНЬ" if self.game_mode == MODE_LEVELS else "∞ БЕСКОНЕЧНЫЙ"
        self.screen.blit(
            self.font_sm.render(mode_text, True, COLOR_GOLD), (24, 12))

        # Очки
        self.screen.blit(self.font_sm.render("ОЧКИ", True, COLOR_TEXT_SUB), (24, 34))
        score_label = self.font_mid.render(f"{self.score:,}", True, COLOR_TEXT_MAIN)
        self.screen.blit(score_label, (24, 54))

        # Прогресс
        if self.game_mode == MODE_LEVELS:
            bx, by, bw, bh = 24, 94, 260, 8
            pygame.draw.rect(self.screen, COLOR_GRID, (bx, by, bw, bh), border_radius=4)
            fill = min(1.0, self.goal_collected / GOAL_ELEMENTS)
            if fill > 0:
                pygame.draw.rect(self.screen, COLOR_GREEN,
                                 (bx, by, int(bw * fill), bh), border_radius=4)
            goal_label = self.font_sm.render(
                f"Цель: {self.goal_collected}/{GOAL_ELEMENTS} 🔴", True, COLOR_TEXT_SUB)
            self.screen.blit(goal_label, (bx + bw + 10, by - 4))

        # Ходы
        cx = SCREEN_WIDTH // 2
        if self.game_mode == MODE_LEVELS:
            self.screen.blit(
                self.font_sm.render("ХОДОВ ОСТАЛОСЬ", True, COLOR_TEXT_SUB),
                (cx - 60, 18))
            moves_color = COLOR_RED if self.moves_left <= 5 else COLOR_TEXT_MAIN
            moves_label = self.font_big.render(str(self.moves_left), True, moves_color)
            self.screen.blit(moves_label,
                             (cx - moves_label.get_width() // 2, 44))
        else:
            self.screen.blit(
                self.font_sm.render("БЕСКОНЕЧНАЯ ИГРА", True, COLOR_TEXT_SUB),
                (cx - 72, 18))
            inf_label = self.font_big.render("∞", True, COLOR_GREEN)
            self.screen.blit(inf_label, (cx - inf_label.get_width()//2, 40))

        # Комбо
        if self.combo >= 2:
            combo_label = self.font_mid.render(
                f"COMBO x{self.combo}!", True, COLOR_GOLD)
            self.screen.blit(combo_label,
                             (cx - combo_label.get_width() // 2, 88))

        # Кнопка рестарта
        btn_rect = pygame.Rect(SCREEN_WIDTH - 148, 32, 128, 46)
        mx, my   = pygame.mouse.get_pos()
        btn_color = COLOR_BTN_HOV if btn_rect.collidepoint(mx, my) else COLOR_BTN_BG
        pygame.draw.rect(self.screen, btn_color, btn_rect, border_radius=10)
        btn_txt = self.font_sm.render("РЕСТАРТ (R)", True, COLOR_BTN_TEXT)
        self.screen.blit(btn_txt, (
            btn_rect.x + (btn_rect.w - btn_txt.get_width()) // 2,
            btn_rect.y + (btn_rect.h - btn_txt.get_height()) // 2))

        # Подсказка ESC
        esc_txt = self.font_sm.render("ESC — пауза", True, COLOR_TEXT_SUB)
        self.screen.blit(esc_txt, (SCREEN_WIDTH - 148, 82))

        # Легенда бонусов
        lx = BOARD_OFFSET_X + COLUMNS * CELL_SIZE + 18
        ly = BOARD_OFFSET_Y
        self.screen.blit(self.font_sm.render("БОНУСЫ:", True, COLOR_TEXT_SUB), (lx, ly))
        for text, color, dy in [
            ("L = Линия (4 в ряд)",       (80, 220, 255), 26),
            ("B = Бомба 3x3",              (255, 100, 100), 50),
            ("C = Цвет (5 в ряд)",         (255, 245, 80),  74),
            ("(активны со след. хода)",    COLOR_TEXT_SUB,  102),
        ]:
            label = self.font_sm.render(text, True, color)
            self.screen.blit(label, (lx, ly + dy))

    def _draw_floating(self):
        for v in self.floating:
            v.draw(self.screen, self.font_pop)

    def _draw_overlay(self, title: str, subtitle: str, color: tuple):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 22, 205))
        self.screen.blit(overlay, (0, 0))

        title_surf = self.font_big.render(title, True, color)
        score_surf = self.font_mid.render(f"Итоговые очки: {self.score:,}", True, COLOR_TEXT_MAIN)
        if self.game_mode == MODE_LEVELS:
            extra = self.font_mid.render(
                f"Собрано: {self.goal_collected}/{GOAL_ELEMENTS}", True, COLOR_TEXT_SUB)
        else:
            extra = self.font_mid.render(
                f"Набрано очков: {self.score:,}", True, COLOR_TEXT_SUB)
        sub_surf = self.font_mid.render(subtitle, True, COLOR_TEXT_SUB)

        cx = SCREEN_WIDTH  // 2
        cy = SCREEN_HEIGHT // 2
        self.screen.blit(title_surf, (cx - title_surf.get_width()//2,  cy - 110))
        self.screen.blit(score_surf, (cx - score_surf.get_width()//2,  cy - 50))
        self.screen.blit(extra,      (cx - extra.get_width()//2,       cy))
        self.screen.blit(sub_surf,   (cx - sub_surf.get_width()//2,    cy + 55))


# ─────────────────────────────────────────
#  ТОЧКА ВХОДА
# ─────────────────────────────────────────

def main():
    pygame.init()
    pygame.display.set_caption("Три в ряд - Royal Kingdom Style")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    try:
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(icon, (255, 210, 60), (16, 16), 14)
        pygame.display.set_icon(icon)
    except Exception:
        pass

    game = Game(screen)
    game.run()


if __name__ == "__main__":
    main()
