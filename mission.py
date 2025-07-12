import turtle
import logging

initial_position = (0, 0)
target_depth = -200
target_position = (100, -150)
square_size = 100


class LevelColorFormatter(logging.Formatter):
    COLORS = {'DEBUG': '\033[36m', 'INFO': '\033[34m',
              'WARNING': '\033[33m', 'ERROR': '\033[31m', 'CRITICAL': '\033[41m'}
    RESET = '\033[0m'

    def format(self, record):
        original_levelname, color = record.levelname, self.COLORS.get(
            record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        formatted = super().format(record)
        record.levelname = original_levelname
        return formatted


logger, handler, formatter = logging.getLogger(), logging.StreamHandler(
), LevelColorFormatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.bgcolor("lightblue")
screen.title("CALROV Otonom Görev")
logging.info("Görev başlangıcı: Sahne ve temel ayarlar yapıldı.")

target_drawer = turtle.Turtle()
target_drawer.hideturtle()
target_drawer.penup()

target_drawer.goto(target_position)
target_drawer.dot(20, "red")
logging.info("Hedef kırmızı nokta (100, -150) koordinatına yerleştirildi.")

rov = turtle.Turtle()
rov.hideturtle()
rov.shape("turtle")
rov.color("black")
rov.speed(1)
rov.penup()
rov.setposition(initial_position)
rov.showturtle()

rov.goto(rov.xcor(), target_depth)
logging.info(f"DALIŞ aşaması tamamlandı. Güncel derinlik: {rov.ycor()}")

rov.pendown()
rov.pencolor("white")
for _ in range(4):
    rov.forward(square_size)
    rov.left(90)
rov.penup()
logging.info("ARAMA aşaması tamamlandı.")

rov.goto(target_position)
logging.info(
    f"KIRMIZI NOKTAYA VARIŞ aşaması tamamlandı. Varış konumu: {rov.pos()}")

rov.setheading(0)
rov.pendown()
rov.pencolor("black")
rov.circle(40)
rov.penup()
logging.info(
    f"ÇEMBERİN ÇİZİLİŞİ aşaması tamamlandı. Çember, kırmızı noktanın üzerine çizildi.")

rov.goto(initial_position)
rov.setheading(0)
logging.info(
    f"BAŞLANGIÇ YERİNE DÖNÜŞ aşaması tamamlandı. Son konum: {rov.pos()}")

turtle.done()
