import pygame
import numpy as np
from pygame._sdl2 import Window, Renderer, Texture

pygame.init()
pygame.font.init()

WINDOW_SIZE = (pygame.display.Info().current_h/2, pygame.display.Info().current_w)
NUM_WINDOWS = 2
ORIGINAL_MAX_WINDOWS = 5
MAX_WINDOWS = ORIGINAL_MAX_WINDOWS
game_state = "playing"
font = pygame.font.Font(None, 28)

player_size = np.array([27, 37])
player_pos = np.array([200.0, 300.0])
player_vel = np.array([0.0, 0.0])
gravity = 0.7
jump_strength = -14
level = 1
on_ground = False
selected_window_index = 0
lenses = {}
hints = []
inverted = False

coyote_time_max = 0.15
coyote_timer = 0.0
import os
import easygui
import json
if os.path.exists("allowed.txt"):
    with open("allowed.txt") as f:
        allowed = bool(f.read())
else:allowed = easygui.boolbox("Do you want to use your desktop wallpaper as the in-game background?", choices=["Yes", "No"])
with open("allowed.txt", "w") as f:
    f.write(str(allowed))
if allowed: backgroundImage = pygame.image.load(os.path.expandvars(r"%AppData%\Microsoft\Windows\Themes\TranscodedWallpaper"))
else: backgroundImage = pygame.image.load(r"assets\img0_1920x1200.jpg")
backgroundImage = pygame.transform.scale(backgroundImage, np.array(backgroundImage.get_rect().size)/20)

def player_animations_template(folder:str):
    return {
        "idleleft": [pygame.image.load(fr'assets\{folder}\idle\playeridle{i}.png') for i in range(5)],
        "idleright": [pygame.image.load(fr'assets\{folder}\idleright\playeridle{i}.png') for i in range(5)],
        "left": [pygame.image.load(fr"assets\{folder}\left\left{i}.png") for i in range(4)],
        "right": [pygame.image.load(fr"assets\{folder}\right\right{i}.png") for i in range(4)],
        "jumpleft": [pygame.image.load(fr"assets\{folder}\jumpleft\jumpleft{i}.png") for i in range(4)],
        "jumpright": [pygame.image.load(fr"assets\{folder}\jumpright\jumpright{i}.png") for i in range(4)],
        "jumpidleleft": [pygame.image.load(fr'assets\{folder}\jumpidleleft\jumpidleleft{i}.png') for i in range(4)],
        "jumpidleright": [pygame.image.load(fr'assets\{folder}\jumpidleright\jumpidleright{i}.png') for i in range(4)],
    }

player_animations = {
    None: player_animations_template("player"),
    "zoom": player_animations_template("zoom"),
    "gravity_flip": player_animations_template("gravity_flip"),
    "wide angle": player_animations_template("wide angle")
}
player_state = "idleleft"
player_lens = None
frame = 0

obstacles = [
    pygame.Rect(500, 380, 80, 20),
    pygame.Rect(700, 300, 80, 20),
    pygame.Rect(900, 250, 80, 20),
    pygame.Rect(-10000, 450, 30000, 40)
]

import json

def load_level(level):
    with open(fr"levels\level-{level}.json", "r") as f:
        data = json.load(f)
    global player_pos, obstacles, game_windows, goal_rect, ORIGINAL_MAX_WINDOWS, MAX_WINDOWS, lenses, player_vel
    for gw in game_windows:
        gw.window.destroy()
    game_windows = []
    player_vel = np.array((0.0, 0.0))
    player_pos = np.array(data["player_start"], dtype=float)

    obstacles = [pygame.Rect(*p) for p in data["platforms"]]

    game_windows = []
    for i, w in enumerate(data["windows"]):
        win = GameWindow(f"Camera {i+1}", size=tuple(w["size"]))
        win.window.position = tuple(w["position"])
        win.locked = w["locked"]
        if win.locked:
            win.locked_position = tuple(w["position"])
            win.window.resizable = False
        win.lens = w.get("lens", None)
        win.settings_locked = w.get("settings_locked", False)
        game_windows.append(win)
    global hints
    hints = []
    if "hints" in data:
        for h in data["hints"]:
            hints.append(Hint(h["text"], h["position"], h.get("duration", 5.0)))
    ORIGINAL_MAX_WINDOWS = MAX_WINDOWS = data.get("ORIGINAL_MAX_WINDOWS", 5)
    lenses = data.get("lenses", {None: ORIGINAL_MAX_WINDOWS})
    lenses = dict(lenses)
    lenses[None] = ORIGINAL_MAX_WINDOWS
    goal_rect = pygame.Rect(*data["goal"], 40, 40)
    MAX_WINDOWS -= len(game_windows)

    return player_pos, obstacles, game_windows, goal_rect

clock = pygame.time.Clock()

def collide_platforms(rect, velocity, obstacles):
    on_ground = False

    rect.x += velocity[0]
    for block in obstacles:
        if rect.colliderect(block):
            if velocity[0] > 0 and rect.left < block.left:
                rect.right = block.left
            elif velocity[0] < 0 and rect.right > block.right:
                rect.left = block.right
            velocity[0] = 0

    rect.y += velocity[1]
    for block in obstacles:
        if not gravity_flip:
            if rect.colliderect(block):
                if velocity[1] > 0:
                    rect.bottom = block.top
                    velocity[1] = 0
                    on_ground = True
                elif velocity[1] < 0:
                    rect.top = block.bottom
                    velocity[1] = 0
        else:
            if rect.colliderect(block):
                if velocity[1] > 0:
                    rect.bottom = block.top
                    velocity[1] = 0
                elif velocity[1] < 0:
                    rect.top = block.bottom
                    velocity[1] = 0
                    on_ground = True

    return rect, velocity, on_ground




lens_handlers = {}

def lens_handler(name):
    def decorator(func):
        lens_handlers[name] = func
        return func
    return decorator

@lens_handler("gravity_flip")
def handle_gravity_flip(player_inside):
    global gravity, jump_strength, gravity_flip
    if player_inside:
        gravity = -abs(gravity)
        jump_strength = abs(jump_strength)
        gravity_flip = True
        return "gravity_flip"
    else: return player_lens

@lens_handler("zoom (player)")
def handle_zoom_player(player_inside, gw):
    global player_pos, player_size
    if player_inside and not gw.player_inside_last_frame:
        player_pos[1] -= 10
        return "zoom"

    if player_inside:
        new_size = np.array([gw.window.size[0] / 10, gw.window.size[1] / 10])
        bottomcenter = np.array((player_pos[0] + player_size[0] / 2, player_pos[1] - player_size[1]))
        player_size = new_size
        player_pos = np.array((bottomcenter[0] - player_size[0] / 2, bottomcenter[1] + player_size[1]))
        gw._zoom_applied = True
        return "zoom"
    
    else: return player_lens

@lens_handler("collision disabled")
def handle_no_collision(player_inside):
    global collision
    if player_inside:
        collision = False
    else: return player_lens

@lens_handler("wide angle (player)")
def handle_antizoom_player(player_inside, gw: 'GameWindow'):
    global player_pos, player_size
    if player_inside and not gw.player_inside_last_frame:
        if (gw.window.size[0] > player_size[0]*30 and gw.window.size[1]>player_size[1]*30): player_pos[1] -= 5
        return "wide angle"

    if player_inside:
        MIN_SIZE = 15
        new_size = np.maximum(np.array([gw.window.size[0] / 30, gw.window.size[1] / 30]), MIN_SIZE)
        bottomcenter = np.array((player_pos[0] + player_size[0] / 2, player_pos[1] - player_size[1]))
        player_size = new_size
        player_pos = np.array((bottomcenter[0] - player_size[0] / 2, bottomcenter[1] + player_size[1]))
        gw._zoom_applied = True
        return "wide angle"
    else: return player_lens

@lens_handler("inverted controls")
def handle_inverted_control(player_inside):
    global inverted
    if player_inside:
        inverted = True
    else: return player_lens
        
        

class GameWindow:
    def __init__(self, title="Game Window", size=(640, 480)):
        self.window = Window(title, size=size, resizable=True)
        self.renderer = Renderer(self.window)
        self.last_window_pos = np.array(self.window.position)
        self.id = self.window.id
        self.locked = False
        self.locked_position = None
        self.lens = None
        self.player_inside_last_frame = False
        self.settings_locked = False

    def get_camera_offset(self):
        current_pos = np.array(self.window.position)
        return current_pos

    def draw(self, player_pos, player_size, obstacles, is_selected=False):
        cam_offset = self.get_camera_offset()
        size = ((self.window.size[0]/pygame.display.Info().current_w)*1280, (self.window.size[1]/pygame.display.Info().current_h)*960)

        self.renderer.draw_color = (30, 30, 30, 255)
        self.renderer.clear()
        self.renderer.blit(Texture.from_surface(self.renderer, backgroundImage), pygame.Rect(-self.window.position[0],-self.window.position[1],pygame.display.Info().current_w,pygame.display.Info().current_h))
        
        global frame, player_state
        frame %= len(player_animations[player_lens][player_state])
        player_draw = pygame.Rect((player_pos[0] - cam_offset[0]), ((player_pos[1] - cam_offset[1]) - 2), player_size[0], player_size[1]+2)
        player_texture = Texture.from_surface(self.renderer, player_animations[player_lens][player_state][int(np.floor(frame))])
        frame = (frame + 1/20) % len(player_animations[player_lens][player_state])
        if "jump" in player_state and int(np.floor(frame)) == 3:
            frame = 3
            player_state = player_state.removeprefix("jump")
        self.renderer.draw_color = (255, 200, 100, 255)
        self.renderer.blit(player_texture, player_draw)

        self.renderer.draw_color = (100, 255, 100, 255)
        for block in obstacles:
            draw_block = block.move(-cam_offset)
            self.renderer.fill_rect(draw_block)
            
        self.renderer.draw_color = (200, 200, 255, 255)
        goal_draw = goal_rect.move(-cam_offset)
        goal_surf = pygame.Surface(goal_draw.size, pygame.SRCALPHA)
        pygame.draw.circle(goal_surf, (200, 200, 255), (goal_draw.size[0]/2, goal_draw.size[1]/2), goal_draw.size[0]/2)
        goal_texture = Texture.from_surface(self.renderer, goal_surf)
        self.renderer.blit(goal_texture, goal_draw)
        
        global game_state
        if is_selected and game_state == "window_manager":
            self.renderer.draw_color = (255, 255, 0, 255) if not self.settings_locked else (255, 0, 0, 255)
            self.renderer.draw_rect(pygame.Rect(0, 0, self.window.size[0], self.window.size[1]))

class Hint:
    def __init__(self, text, position, duration=5.0):
        self.text = text
        self.position = position
        self.duration = duration
        self.timer = 0.0
        self.active = True

    def update(self, dt):
        if self.active:
            self.timer += dt
            if self.timer >= self.duration:
                self.active = False

    def draw(self, renderer, font, camera_offset=np.array([0, 0])):
        if self.active:
            text_surf = font.render(self.text, True, (255, 255, 255))
            text_texture = Texture.from_surface(renderer, text_surf)
            draw_pos = (self.position[0] - camera_offset[0], self.position[1] - camera_offset[1])
            renderer.blit(text_texture, pygame.Rect(*draw_pos, *text_surf.get_size()))


class ManagerWindow:
    def __init__(self):
        self.scaler = 1.5
        self.window = Window("Window Manager", size=np.array((480, 368))*self.scaler, resizable=False)
        self.renderer = Renderer(self.window)
        self.font = pygame.font.SysFont("helvetica", 11)
        self.visible = False
        self.window.hide()
        self.background_image = Texture.from_surface(self.renderer, pygame.image.load(r"assets\newcamera.png"))
        self.lens_case = Window("Lens Case", size=np.array((200, 200)), resizable = False)
        self.lens_font = pygame.font.SysFont("helvetica", 28)
        self.lens_case_renderer = Renderer(self.lens_case)
    def show(self):
        self.visible = True
        self.window.show()

    def hide(self):
        self.visible = False
        self.window.hide()

    def draw(self, selected_window: 'GameWindow'):
        self.lens_case_renderer.draw_color = (20, 20, 20, 255)
        self.lens_case_renderer.clear()
        lens_text = str(lenses) + " " + str(player_pos)
        words = lens_text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            test_surf = self.lens_font.render(test_line, False, (255,255,255))
            if test_surf.get_width() > 200 and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)

        y_offset = 0
        for line in lines:
            lens_text_surf = self.lens_font.render(line, False, (255,255,255))
            lens_text_texture = Texture.from_surface(self.lens_case_renderer, lens_text_surf)
            self.lens_case_renderer.blit(
                lens_text_texture,
                pygame.Rect(0, y_offset, *lens_text_surf.get_size())
            )
            y_offset += lens_text_surf.get_height()
        self.lens_case_renderer.present()
        if not self.visible:
            return
        viewport = selected_window.renderer.to_surface()
        viewport = Texture.from_surface(self.renderer, viewport)
        self.renderer.draw_color = (20, 20, 20, 255)
        self.renderer.clear()
        self.renderer.blit(viewport, pygame.Rect(173*self.scaler, 83*self.scaler, 50*self.scaler, 41*self.scaler))
        self.renderer.blit(self.background_image, pygame.Rect(0,0, *self.window.size))
        lines = [
            f"Managing Window ID {selected_window.id}",
            f"[L] Lock: {'Yes' if selected_window.locked else 'No'}",
            f"[</>] Lens: {selected_window.lens if selected_window.lens else 'None'}",
            f"[C] Close Window",
            f"[Tab] Switch Window",
            f"[N] New Window ({ORIGINAL_MAX_WINDOWS - MAX_WINDOWS}/{ORIGINAL_MAX_WINDOWS})",
            f"[E] Exit"
        ]

        for i, line in enumerate(lines):
            text_surf = self.font.render(line, False, (255, 255, 255))
            text_surf = pygame.transform.scale(text_surf, np.array(text_surf.get_size())*self.scaler)
            text_texture = Texture.from_surface(self.renderer, text_surf)
            self.renderer.blit(text_texture, pygame.Rect(*np.array((43, 199 + i * 18.5))*self.scaler, *(np.array(text_surf.get_size()))))
        self.renderer.present()

game_windows = [GameWindow(f"Camera {i+1}", WINDOW_SIZE) for i in range(NUM_WINDOWS)]
window_manager = ManagerWindow()
window_manager.window.position = (640, 480)
window_manager.hide()
load_level(level)

running = True
while running:
    dt = clock.tick(60) / 1000
    for gw in game_windows:
        if gw.locked:
            gw.window.position = gw.locked_position
            
    if game_state == "playing":
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.WINDOWCLOSE:
                closed_id = event.window.id
                game_windows = [w for w in game_windows if w.id != closed_id]
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    game_state = "window_manager"
                    window_manager.show()
                elif event.key == pygame.K_LCTRL:
                    load_level(level)

        keys = pygame.key.get_pressed()
        move_x = (keys[pygame.K_d] - keys[pygame.K_a]) * 5
        if inverted: move_x *= -1
        player_vel[0] = move_x
        if not on_ground:
            player_vel[1] += gravity
            
        for gw in game_windows:
            gw._zoom_applied = False
        collision = True
        inverted = False
        zoom_reset_needed = True
        gravity = abs(gravity)
        jump_strength = -abs(jump_strength)
        gravity_flip = False

        player_rect = pygame.Rect(*player_pos, *player_size)
        player_lens = None

        for gw in game_windows:
            view_rect = pygame.Rect(gw.get_camera_offset(), gw.window.size)
            player_inside = view_rect.collidepoint(*player_rect.center)
            if gw.lens in lens_handlers:
                if gw.lens in ["wide angle (player)", "zoom (player)"]:
                    gw._zoom_applied = False
                    player_lens = lens_handlers[gw.lens](player_inside, gw)
                    if gw._zoom_applied:
                        zoom_reset_needed = False
                else:
                    player_lens = lens_handlers[gw.lens](player_inside)

            gw.player_inside_last_frame = player_inside

        if zoom_reset_needed and not np.allclose(player_size, [40, 40]):
            player_pos[1] -= 30
            bottomcenter = np.array((player_pos[0] + player_size[0] / 2, player_pos[1] - player_size[1]))
            player_size = np.array([40.0, 40.0])
            player_pos = np.array((bottomcenter[0] - player_size[0] / 2, bottomcenter[1] + player_size[0]))
        player_rect = pygame.Rect(int(player_pos[0]), int(player_pos[1]), int(player_size[0]), int(player_size[1]))
        locked_windows = []
        for gw in game_windows:
            if gw.locked:
                view_rect = pygame.Rect(gw.get_camera_offset(), gw.window.size)
                locked_windows.append(pygame.Rect(view_rect.bottomleft[0], view_rect.bottomleft[1] - 5, view_rect.size[0], 10))
        if collision: player_rect, player_vel, on_ground = collide_platforms(player_rect, player_vel, [*obstacles, *locked_windows])
        else: player_rect, player_vel, on_ground = collide_platforms(player_rect, player_vel, locked_windows)
        player_pos = np.array([player_rect.x, player_rect.y])                   


        if on_ground:
            coyote_timer = coyote_time_max
        else:
            coyote_timer -= dt
            if coyote_timer < 0:
                coyote_timer = 0

        if ("jump" not in player_state) or on_ground:
            if player_vel[0] > 0:
                player_state = "right"
            elif player_vel[0] < 0:
                player_state = "left"
            elif player_vel.all() == 0:
                player_state = "idleleft" if "left" in player_state else "idleright"
        elif "jump" in player_state:
            if player_vel[0] > 0:
                player_state = "jumpright"
            elif player_vel[0] < 0:
                player_state = "jumpleft"

        if keys[pygame.K_SPACE] and coyote_timer > 0:
            player_state = "jump" + player_state
            player_vel[1] = jump_strength
            on_ground = False
            coyote_timer = 0
            
        if player_rect.colliderect(goal_rect):
            level += 1
            selected_window_index = 0
            try: load_level(level)
            except: running = False
    elif game_state == "window_manager":
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    game_state = "playing"
                    window_manager.hide()
                elif event.key == pygame.K_l:
                    selected = game_windows[selected_window_index]
                    if not selected.settings_locked:
                        if not selected.locked:
                            selected.locked = not selected.locked
                            selected.locked_position = selected.window.position if selected.locked else None
                            selected.window.resizable = not selected.locked
                elif event.key == pygame.K_c:
                    closed_id = game_windows[selected_window_index].id
                    game_windows[selected_window_index].window.destroy()
                    game_windows = [w for w in game_windows if w.id != closed_id]
                    try:
                        selected_window_index %= len(game_windows)
                    except ZeroDivisionError:
                        running = False
                elif event.key == pygame.K_TAB:
                    selected_window_index = (selected_window_index + 1) % len(game_windows)
                elif event.key == pygame.K_LEFT:
                    lenses_list = []
                    selected_window = game_windows[selected_window_index]
                    for k in lenses.keys():
                        if lenses[k] > 0 or selected_window.lens == k:
                            lenses_list.append(k)
                    # if selected_window.lens in lenses_list: lenses_list.remove(selected_window.lens)
                    if lenses_list != [] and not selected_window.settings_locked:
                        selected_window = game_windows[selected_window_index]
                        current_lens_index = lenses_list.index(selected_window.lens) if selected_window.lens in lenses_list else -1
                        lenses[selected_window.lens] += 1
                        new_lens_index = (current_lens_index - 1) % len(lenses_list)
                        selected_window.lens = lenses_list[new_lens_index]
                        lenses[selected_window.lens] -= 1
                elif event.key == pygame.K_RIGHT:
                    lenses_list = []
                    selected_window = game_windows[selected_window_index]
                    for k in lenses.keys():
                        if lenses[k] > 0 or selected_window.lens == k:
                            lenses_list.append(k)
                    # if selected_window.lens in lenses_list: lenses_list.remove(selected_window.lens)
                    if lenses_list != [] and not selected_window.settings_locked:
                        selected_window = game_windows[selected_window_index]
                        current_lens_index = lenses_list.index(selected_window.lens) if selected_window.lens in lenses_list else -1
                        lenses[selected_window.lens] += 1
                        new_lens_index = (current_lens_index + 1) % len(lenses_list)
                        selected_window.lens = lenses_list[new_lens_index]
                        lenses[selected_window.lens] -= 1
                elif event.key == pygame.K_n and MAX_WINDOWS > 0:
                    MAX_WINDOWS -= 1
                    game_windows.append(GameWindow()) 
                elif event.key == pygame.K_LCTRL:
                    load_level(level)
    if game_state == "playing":
        new_hints = []
        for hint in hints:  
            hint.update(dt)
            if hint.active:
                new_hints.append(hint)
        hints = new_hints
    selected_window_index %= len(game_windows)
    window_manager.draw(game_windows[selected_window_index])
    for i, gw in enumerate(game_windows):
        is_selected = (i == selected_window_index)
        gw.draw(player_pos, player_size, obstacles, is_selected=is_selected)
        for hint in hints:
            if game_state == "playing":
                gw.renderer.draw_color = (0, 0, 0, 0)
                hint.draw(gw.renderer, font, camera_offset=gw.get_camera_offset())
        gw.renderer.present()

