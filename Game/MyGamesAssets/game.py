import pygame
import os
import random
import sys

# --- تنظیمات کلی ---
WIDTH, HEIGHT = 800, 600
FPS = 60

class Game:
    def init(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Ultimate Project Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 36, bold=True)
        
        self.running = True
        self.game_over = False
        self.score = 0
        
        # مسیر پوشه عکس‌ها - اگر وجود نداشت بازی با رنگ اجرا می‌شود
        self.img_dir = "images"
        self.assets = {}
        self._load_assets()

        # ساخت پلیر و موانع
        self.player = Player(self)
        self.obstacles = []
        self.obstacle_timer = 0

    def _load_assets(self):
        """بارگذاری خودکار تمام عکس‌های موجود در پوشه images"""
        if os.path.exists(self.img_dir):
            for file in os.listdir(self.img_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    path = os.path.join(self.img_dir, file)
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        img = pygame.transform.scale(img, (50, 50))
                        self.assets[file] = img
                    except:
                        pass
        print(f"Loaded {len(self.assets)} images.")

    def run(self):
        while self.running:
            self.handle_events()
            if not self.game_over:
                self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if self.game_over:
                    self.__init__() # ریستارت بازی

    def update(self):
        self.player.update()
        
        # تولید موانع
        self.obstacle_timer += 1
        if self.obstacle_timer > 40:
            self.obstacles.append(Obstacle(self))
            self.obstacle_timer = 0

        # حرکت موانع و چک کردن برخورد
        for obs in self.obstacles[:]:
            obs.update()
            if obs.y > HEIGHT:
                self.obstacles.remove(obs)
                self.score += 1
            
            if self.player.rect.colliderect(obs.rect):
                self.game_over = True

    def draw(self):
        self.screen.fill((20, 20, 30)) # پس زمینه تیره شیک

        if not self.game_over:
            self.player.draw(self.screen)
            for obs in self.obstacles:
                obs.draw(self.screen)
            
            # نمایش امتیاز
            score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
            self.screen.blit(score_surf, (20, 20))
        else:
            # صفحه پایان بازی
            over_text = self.font.render("GAME OVER!", True, (255, 50, 50))
            restart_text = self.font.render("Press any key to Restart", True, (200, 200, 200))
            self.screen.blit(over_text, (WIDTH//2 - 80, HEIGHT//2 - 40))
            self.screen.blit(restart_text, (WIDTH//2 - 160, HEIGHT//2 + 20))

        pygame.display.flip()

class Player:
    def init(self, game):
        self.game = game
        self.size = 50
        self.x = WIDTH // 2
        self.y = HEIGHT - 70
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
        self.speed = 8
        # اگر عکسی پیدا شده باشد استفاده کن، وگرنه مربع آبی
        self.image = list(game.assets.values())[0] if game.assets else None

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.x > 0:
            self.x -= self.speed
        if keys[pygame.K_RIGHT] and self.x < WIDTH - self.size:
            self.x += self.speed
        self.rect.topleft = (self.x, self.y)
    def draw(self, screen):
        if self.image:
            screen.blit(self.image, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (0, 150, 255), self.rect)

class Obstacle:
    def init(self, game):
        self.game = game
        self.size = random.randint(40, 60)
        self.x = random.randint(0, WIDTH - self.size)
        self.y = -self.size
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
        self.speed = random.randint(5, 9)
        self.image = list(game.assets.values())[0] if game.assets else None

    def update(self):
        self.y += self.speed
        self.rect.topleft = (self.x, self.y)

    def draw(self, screen):
        if self.image:
            screen.blit(self.image, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (255, 50, 50), self.rect)

if __name__ == "__main__":
    game = Game()
    game.run()    