
import os
import pgzrun
from pygame import Rect #não é utilizado diretamente
import random
import time

# ===================== ÁUDIO tolerante =====================
AUDIO_OK = False
def log(msg): print("[JOGO]", msg)
MUSICA_ARQ = os.path.join("sounds", "musica.ogg")  # usado no fallback

try:
    import pygame
    try:
        pygame.mixer.init()
        AUDIO_OK = True
        log("Áudio OK (mixer inicializado).")
    except Exception:
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        try:
            pygame.mixer.init()
            AUDIO_OK = False
            log("Sem dispositivo de áudio; usando driver 'dummy' (sem som).")
        except Exception as e2:
            log(f"Áudio indisponível: {e2}")
except Exception as e:
    log(f"Falha importando pygame: {e}")

def tocar_som(nome):
    if not efeitos_ligados or not AUDIO_OK:
        return
    try:
        getattr(sounds, nome).play()
    except Exception as e:
        log(f"Falha som '{nome}': {e}")

def tocar_musica(nome):
    if not musica_ligada or not AUDIO_OK:
        return
    ok = False
    try:
        music.set_volume(0.7)
        music.play(nome)
        ok = True
        log("PgZero music.play chamado.")
    except Exception as e:
        log(f"Falha PgZero music.play('{nome}'): {e}")
    if not ok:
        try:
            import pygame
            if os.path.exists(MUSICA_ARQ):
                pygame.mixer.music.load(MUSICA_ARQ)
                pygame.mixer.music.set_volume(0.7)
                pygame.mixer.music.play(-1)  # loop
                log("Fallback: pygame.mixer.music tocando em loop.")
            else:
                log(f"Arquivo não encontrado para fallback: {MUSICA_ARQ}")
        except Exception as e:
            log(f"Falha no fallback pygame.mixer.music: {e}")

def parar_musica():
    if not AUDIO_OK:
        return
    try: music.stop()
    except Exception as e: log(f"PgZero music.stop falhou: {e}")
    try:
        import pygame
        pygame.mixer.music.stop()
    except Exception as e:
        log(f"pygame.mixer.music.stop falhou: {e}")

# ===================== Janela =====================
LARGURA = 800
ALTURA  = 600
TITLE   = ""

# ===================== Estados =====================
ESTADO_MENU = "menu"
ESTADO_JOGO = "jogo"
ESTADO_FIM  = "fim"
estado_atual = ESTADO_MENU

musica_ligada   = True     # controla música
efeitos_ligados = True     # controla efeitos (sons)
pontuacao = 0
vidas     = 3

gravidade  = 0.55
forca_pulo = -11.0
vel_heroi  = 4.0

bg_surface = None

# ===================== Partículas =====================
particulas = []

class Particula:
    def __init__(self, x, y, vx, vy, vida, raio, cor):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.vida = vida     # frames restantes
        self.raio = raio
        self.cor = cor
    def atualizar(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15  # leve gravidade
        self.vida -= 1
        if self.raio > 0.5:
            self.raio *= 0.96
    def desenhar(self):
        screen.draw.filled_circle((self.x, self.y), max(1, int(self.raio)), self.cor)

def spawn_particulas_pulo(x, y):
    # sobe do pé do herói
    for _ in range(8):
        vx = random.uniform(-0.8, 0.8)
        vy = random.uniform(-2.8, -1.0)
        particulas.append(Particula(x, y, vx, vy, vida=28, raio=4, cor=(230,230,230)))

def spawn_particulas_pouso(x, y):
    for _ in range(14):
        ang = random.uniform(0, 3.1415)   # espalha para os lados
        vel = random.uniform(0.5, 2.2)
        vx = vel * (1 if random.random()<0.5 else -1) * random.random()
        vy = -abs(vel) * random.uniform(0.2, 0.9)
        particulas.append(Particula(x + random.uniform(-6,6), y, vx, vy, vida=22, raio=5, cor=(210,210,210)))

def atualizar_particulas():
    for p in particulas[:]:
        p.atualizar()
        if p.vida <= 0 or p.y > ALTURA + 50:
            particulas.remove(p)

def desenhar_particulas():
    for p in particulas:
        p.desenhar()

# ===================== Helpers =====================
def ator(imagem, pos):
    try:
        a = Actor(imagem, pos)
        return a
    except Exception as e:
        log(f"ERRO carregando imagem '{imagem}': {e}")
        raise

def desenhar_botao_imagem(caixa: Rect, texto: str):
    try:
        import pygame
        surf = images.botao.surf
        btn  = pygame.transform.smoothscale(surf, (caixa.w, caixa.h))
        screen.blit(btn, caixa.topleft)
    except Exception:
        screen.draw.filled_rect(caixa, (25, 45, 90))
    screen.draw.rect(caixa, (230, 230, 255))
    screen.draw.textbox(texto, caixa, color="white", align="center")

# ===================== Classes =====================
class Botao:
    def __init__(self, texto, x, y, largura=300, altura=66, acao=None):
        self.texto = texto
        self.caixa = Rect((x, y), (largura, altura))
        self.acao  = acao
    def desenhar(self):
        desenhar_botao_imagem(self.caixa, self.texto)
    def checar_clique(self, pos):
        if self.caixa.collidepoint(pos) and self.acao:
            self.acao()

class Plataforma:
    def __init__(self, x, y, largura, altura):
        self.ret = Rect((x, y), (largura, altura))
    def atualizar(self): pass
    def desenhar(self):
        screen.draw.filled_rect(self.ret, (60,150,80))
        screen.draw.rect(self.ret, (40,100,60))

class PlataformaMovel(Plataforma):
    def __init__(self, x, y, largura, altura, eixo="x", alcance=100, vel=1.5):
        super().__init__(x, y, largura, altura)
        self.eixo = eixo  # "x" ou "y"
        self.centro = (x, y)
        self.alcance = alcance
        self.vel = vel
        self.dir = 1
    def atualizar(self):
        if self.eixo == "x":
            self.ret.x += self.vel * self.dir
            if self.ret.x > self.centro[0] + self.alcance or self.ret.x < self.centro[0] - self.alcance:
                self.dir *= -1
        else:
            self.ret.y += self.vel * self.dir
            if self.ret.y > self.centro[1] + self.alcance or self.ret.y < self.centro[1] - self.alcance:
                self.dir *= -1

class Heroi:
    def __init__(self, x, y):
        self.ator = ator("player_stand", (x, y))
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.no_chao = False
        self.virado_esq = False

        self.frames_parado  = ["player_stand", "player_walk1"]
        self.frames_andando = ["player_walk1", "player_walk2"]
        self.frame_pulando  = "player_jump"
        self.ind_anim = 0.0

        self.coyote_frames = 0
        self.COYOTE_MAX    = 10  # ~0,16s a 60 FPS

    def atualizar(self):
        self.vel_x = 0.0
        if keyboard.left:
            self.vel_x = -vel_heroi; self.virado_esq = True
        if keyboard.right:
            self.vel_x =  vel_heroi; self.virado_esq = False
        # estado anterior para detectar pouso
        no_chao_antes = self.no_chao
        if keyboard.space or keyboard.up or keyboard.w:
            if self.no_chao or self.coyote_frames > 0:
                self.pular()
                spawn_particulas_pulo(self.ator.x, self.ator.bottom)

        self.vel_y += gravidade
        self.ator.x += self.vel_x
        self.ator.y += self.vel_y

        self.no_chao = False
        self._resolver_colisoes()
        self._sonda_pe()

        if self.no_chao and not no_chao_antes:
            # acabou de pousar
            spawn_particulas_pouso(self.ator.x, self.ator.bottom)

        if self.no_chao:
            self.coyote_frames = self.COYOTE_MAX
        else:
            self.coyote_frames = max(0, self.coyote_frames - 1)

        self.ator.x = max(16, min(LARGURA - 16, self.ator.x))
        self.ator.y = min(ALTURA + 200, self.ator.y)

        self._animar()

    def _resolver_colisoes(self):
        caixa = self.ator._rect
        for p in plataformas:
            if caixa.colliderect(p.ret):
                if self.vel_y > 0 and caixa.bottom - self.vel_y <= p.ret.top:
                    self.ator.y = p.ret.top - caixa.h/2
                    self.vel_y = 0
                    self.no_chao = True
        if self.ator.y >= 520:
            self.ator.y = 520
            self.vel_y = 0
            self.no_chao = True

    def _sonda_pe(self):
        if self.vel_y >= 0:
            caixa = self.ator._rect.move(0, 4)
            for p in plataformas:
                if caixa.colliderect(p.ret) and self.ator._rect.bottom <= p.ret.top + 6:
                    self.ator.y = p.ret.top - self.ator._rect.h/2
                    self.vel_y = 0
                    self.no_chao = True
                    break

    def _animar(self):
        if self.no_chao and abs(self.vel_x) < 0.01:
            self.ind_anim = (self.ind_anim + 0.10) % len(self.frames_parado)
            self.ator.image = self.frames_parado[int(self.ind_anim)]
        elif not self.no_chao:
            self.ator.image = self.frame_pulando
        else:
            self.ind_anim = (self.ind_anim + 0.22) % len(self.frames_andando)
            self.ator.image = self.frames_andando[int(self.ind_anim)]
        self.ator.flip_x = self.virado_esq

    def pular(self):
        self.vel_y = forca_pulo
        self.no_chao = False
        tocar_som("jump")

    def desenhar(self):
        self.ator.draw()

    @property
    def ret(self):
        return self.ator._rect

class Inimigo:
    def __init__(self, x, y, alcance=90, vel=2.0):
        self.ator = ator("enemy_walk1", (x, y))
        self.frames = ["enemy_walk1", "enemy_walk2"]
        self.ind_anim = 0.0
        self.lim_esq = x - alcance
        self.lim_dir = x + alcance
        self.vel = vel * random.choice([-1, 1])

    def atualizar(self):
        self.ator.x += self.vel
        if self.ator.x <= self.lim_esq or self.ator.x >= self.lim_dir:
            self.vel *= -1

        self.ator.y += 6
        caixa = self.ator._rect
        for p in plataformas:
            if caixa.colliderect(p.ret) and caixa.bottom <= p.ret.bottom:
                self.ator.y = p.ret.top - caixa.h/2
        if self.ator.y >= 520:
            self.ator.y = 520

        self.ind_anim = (self.ind_anim + 0.20) % len(self.frames)
        self.ator.image = self.frames[int(self.ind_anim)]
        self.ator.flip_x = self.vel < 0

    def desenhar(self):
        self.ator.draw()

    @property
    def ret(self):
        return self.ator._rect

# ===================== Mundo/Fase =====================
def criar_fase():
    global plataformas, heroi, inimigos, pontuacao, vidas
    pontuacao = 0
    vidas = 3

    plataformas = [
        Plataforma(0,   560, LARGURA, 40),                     # chão
        Plataforma(80,  430, 140, 22),
        Plataforma(330, 360, 120, 22),
        Plataforma(220, 500, 100, 22),

        # --- Plataformas móveis (encurtadas) ---
        PlataformaMovel(520, 300, 110, 22, eixo="x", alcance=90, vel=1.6),  # esquerda-direita
        PlataformaMovel(650, 420, 90,  22, eixo="y", alcance=70, vel=1.3),  # sobe-desce
    ]

    heroi = Heroi(100, 520)
    inimigos = [
        Inimigo(360, 520, alcance=110, vel=2.2),
        Inimigo(580, 520, alcance=120, vel=1.8),
        Inimigo(560, 270, alcance=70,  vel=1.6),
    ]
    return heroi, inimigos


def iniciar_partida():
    global estado_atual, heroi, inimigos
    criar_fase()
    estado_atual = ESTADO_JOGO

def alternar_audio():
    global musica_ligada, efeitos_ligados
    if musica_ligada or efeitos_ligados:
        musica_ligada = False
        efeitos_ligados = False
        parar_musica()
        log("Áudio: OFF (música e efeitos)")
    else:
        musica_ligada = True
        efeitos_ligados = True
        tocar_musica("musica")
        log("Áudio: ON (música e efeitos)")

def sair_jogo():
    raise SystemExit

def voltar_menu():
    global estado_atual
    estado_atual = ESTADO_MENU

# ===================== UI (menu/fim) =====================
botoes_menu = [
    Botao("Começar jogo",          250, 240, acao=iniciar_partida),
    Botao("Música e sons ON/OFF",  250, 320, acao=alternar_audio),
    Botao("Sair",                  310, 400, largura=180, acao=sair_jogo),
]

botoes_fim = [
    Botao("Jogar novamente", 260, 300, acao=iniciar_partida),
    Botao("Voltar ao menu",  260, 380, acao=voltar_menu),
]

heroi, inimigos = criar_fase()

# ===================== Ciclo PgZero =====================
def on_show():
    global bg_surface
    log("Janela aberta às " + time.strftime("%H:%M:%S"))
    try:
        import pygame
        surf = images.background.surf
        bg_surface = pygame.transform.smoothscale(surf, (LARGURA, ALTURA))
    except Exception as e:
        log(f"Falha ao preparar background: {e}")
        bg_surface = None
    tocar_musica("musica")

def update():
    global estado_atual, pontuacao, vidas
    if estado_atual == ESTADO_JOGO:
        # atualiza plataformas móveis
        for p in plataformas:
            p.atualizar()

        heroi.atualizar()
        for inim in inimigos:
            inim.atualizar()

        for inim in inimigos[:]:
            if heroi.ret.colliderect(inim.ret):
                if heroi.vel_y > 0 and heroi.ret.bottom <= inim.ret.centery:
                    pontuacao += 100
                    inimigos.remove(inim)
                    heroi.vel_y = forca_pulo * 0.6
                else:
                    if vidas > 0:
                        vidas -= 1
                    tocar_som("hit")
                    heroi.ator.x += -60 if heroi.virado_esq else 60
                    heroi.vel_y = forca_pulo * 0.8
                    if vidas <= 0:
                        estado_atual = ESTADO_FIM

        if not inimigos and estado_atual == ESTADO_JOGO:
            pontuacao += 500
            estado_atual = ESTADO_FIM

        atualizar_particulas()

def draw():
    screen.clear()
    if bg_surface:
        screen.blit(bg_surface, (0, 0))
    else:
        try:
            screen.blit("background", (0, 0))
        except:
            screen.fill((190, 230, 235))

    if estado_atual == ESTADO_MENU:
        _desenhar_titulo()
        for p in plataformas: p.desenhar()
        for b in botoes_menu: b.desenhar()
        _desenhar_dicas()

    elif estado_atual == ESTADO_JOGO:
        for p in plataformas: p.desenhar()
        for inim in inimigos: inim.desenhar()
        heroi.desenhar()
        desenhar_particulas()
        _desenhar_hud()

    elif estado_atual == ESTADO_FIM:
        for p in plataformas: p.desenhar()
        for inim in inimigos: inim.desenhar()
        heroi.desenhar()
        desenhar_particulas()
        _desenhar_hud()
        caixa = Rect((140, 180), (520, 180))
        screen.draw.filled_rect(caixa, (0, 0, 0, 120))
        screen.draw.textbox(
            f"FIM DE JOGO!\nPontuação: {pontuacao}\nVidas: {max(vidas,0)}",
            caixa, color="white", align="center"
        )
        for b in botoes_fim: b.desenhar()

def on_mouse_down(pos):
    if estado_atual == ESTADO_MENU:
        for b in botoes_menu: b.checar_clique(pos)
    elif estado_atual == ESTADO_FIM:
        for b in botoes_fim: b.checar_clique(pos)

def on_key_down(key):
    if key == keys.M:
        alternar_audio()
    if key == keys.ESCAPE:
        voltar_menu()
    if estado_atual == ESTADO_JOGO and (key == keys.SPACE or key == keys.UP or key == keys.W):
        # o spawn de partículas de pulo também é chamado dentro de Heroi.atualizar()
        heroi.pular()

# ===================== HUD / textos =====================
def _desenhar_titulo():
    screen.draw.text(
        "",
        topleft=(40, 30), fontsize=36, color="white",
        owidth=1, ocolor="black"
    )

def _desenhar_hud():
    screen.draw.text(
        f"Pontos: {pontuacao}    Vidas: {max(vidas,0)}",
        topleft=(16, 12), fontsize=28, color="white",
        owidth=1, ocolor="black"
    )

def _desenhar_dicas():
    dica = "Controles: Setas do teclado.  Pular: Espaço.  ESC: menu.  Música: M (ON/OFF)."
    screen.draw.textbox(dica, Rect((80, 520), (LARGURA - 160, 56)), color="white")

# ===================== Início =====================
pgzrun.go()


