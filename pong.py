#!/usr/bin/python

import pygame
import random
import cv2
import numpy as np
import math

pygame.init()

WIDTH, HEIGHT = 1440, 1080
screen = pygame.display.set_mode(
    (WIDTH, HEIGHT),
     pygame.DOUBLEBUF
)

clock = pygame.time.Clock()

WHITE = (255,255,255)
BLACK = (0,0,0)

PADDLE_WIDTH, PADDLE_HEIGHT = 10, 100
BALL_SIZE = 15

BASE_SPEED = 200  #  改为“像素/秒”

TOP, BOTTOM = 145, 450 # 摄像头看到的屏幕高度范围


left_paddle = pygame.Rect(20, HEIGHT//2 - 40, PADDLE_WIDTH, PADDLE_HEIGHT)
right_paddle = pygame.Rect(WIDTH-30, HEIGHT//2 - 40, PADDLE_WIDTH, PADDLE_HEIGHT)

# ===== 球（浮点位置）=====
ball_x = WIDTH / 2
ball_y = HEIGHT / 2

angle = random.uniform(-0.5, 0.5)
ball_speed_x = BASE_SPEED * random.choice([-1,1])
ball_speed_y = BASE_SPEED * angle

# 拖尾
trail = []

left_score = 0
right_score = 0
font = pygame.font.SysFont(None, 160)

# ===== 摄像头 =====
cap = cv2.VideoCapture(0)
cv2.namedWindow("Threshold")
cv2.createTrackbar("T","Threshold",60,255,lambda x:None)

ret, bg_frame = cap.read()
bg_frame = cv2.flip(bg_frame,1)
bg_gray = cv2.cvtColor(bg_frame,cv2.COLOR_BGR2GRAY)

smoothed_y = HEIGHT//2


def init_ball():
    global ball_x, ball_y, angle, ball_speed_x, ball_speed_y
    ball_x = WIDTH / 2
    ball_y = HEIGHT / 2

    angle = random.uniform(-0.5, 0.5)
    ball_speed_x = BASE_SPEED * random.choice([-1,1])
    ball_speed_y = BASE_SPEED * angle


def get_hand_position():
    global bg_gray, smoothed_y

    ret, frame = cap.read()
    if not ret:
        return None

    frame = cv2.flip(frame,1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    bg_gray = cv2.addWeighted(gray,0.05,bg_gray,0.95,0)

    diff = cv2.absdiff(gray,bg_gray)
    t = cv2.getTrackbarPos("T","Threshold")
    _,thresh = cv2.threshold(diff,t,255,cv2.THRESH_BINARY)

    h,w = thresh.shape
    roi = thresh[:,w//2:]

    contours,_ = cv2.findContours(roi,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    best=None
    min_dist=1e9

    for c in contours:
        area = cv2.contourArea(c)
        if 500 < area < 5000:
            x,y,wc,hc = cv2.boundingRect(c)
            cy = y+hc//2
            dist = abs(cy-smoothed_y)
            if dist<min_dist:
                min_dist=dist
                best=(x,y,wc,hc)

    if best:
        x,y,wc,hc = best
        cy = y+hc//2

        cv2.rectangle(frame,(x+w//2,y),(x+w//2+wc,y+hc),(0,0,255),2)

        cv2.imshow("Camera",frame)
        cv2.imshow("Threshold",thresh)
        cv2.waitKey(1)

        return int((cy - TOP) / (BOTTOM - TOP) * HEIGHT)

    cv2.imshow("Camera",frame)
    cv2.imshow("Threshold",thresh)
    cv2.waitKey(1)

    return None

# ===== 反弹 =====
def paddle_bounce():
    global ball_speed_x, ball_speed_y

    relative = (ball_y - right_paddle.centery) / (PADDLE_HEIGHT/2)
    relative = max(-1,min(1,relative))

    angle = relative * math.radians(60)

    #speed = math.hypot(ball_speed_x, ball_speed_y) * 1.2
    speed = math.hypot(ball_speed_x, ball_speed_y) + 30
	
    direction = -1 if ball_speed_x > 0 else 1

    ball_speed_x = direction * speed * math.cos(angle)
    ball_speed_y = speed * math.sin(angle)

# ================= 主循环 =================
running = True

while running:
    dt = clock.tick(60) / 1000.0  # 秒

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running=False

    if pygame.key.get_pressed()[pygame.K_ESCAPE]:
        running=False

    if pygame.key.get_pressed()[pygame.K_r]:
        right_score = 0
        left_score = 0
        init_ball()


    # 手控制
    cam_y = get_hand_position()
    if cam_y:
        smoothed_y = int(0.3*cam_y + 0.7*smoothed_y)

    right_paddle.y = smoothed_y - PADDLE_HEIGHT//2
    right_paddle.y = max(0,min(HEIGHT-PADDLE_HEIGHT,right_paddle.y))

    # AI
    if left_paddle.centery < ball_y:
        left_paddle.y += 300 * dt
    else:
        left_paddle.y -= 300 * dt

    # ===== 球运动（核心改进）=====
    ball_x += ball_speed_x * dt
    ball_y += ball_speed_y * dt

    # 拖尾
    trail.append((ball_x, ball_y))
    if len(trail) > 8:
        trail.pop(0)

    # 上下反弹
    if ball_y <= 0 or ball_y >= HEIGHT:
        ball_speed_y *= -1

    ball_rect = pygame.Rect(int(ball_x), int(ball_y), BALL_SIZE, BALL_SIZE)

    if ball_rect.colliderect(right_paddle) or ball_rect.colliderect(left_paddle):
        paddle_bounce()

    # 得分
    if ball_x < 0:
        right_score += 1
        init_ball()
		
    if ball_x > WIDTH:
        left_score += 1
        init_ball()

    # ===== 绘制 =====
    screen.fill(WHITE)

    pygame.draw.rect(screen,BLACK,left_paddle)
    pygame.draw.rect(screen,BLACK,right_paddle)

    # 拖尾绘制（丝滑关键）
    for i,pos in enumerate(trail):
        alpha = int(255 * (i/len(trail)))
        pygame.draw.circle(screen,(200,200,200),(int(pos[0]),int(pos[1])),BALL_SIZE * (i/len(trail)))

    pygame.draw.circle(screen,BLACK,(int(ball_x),int(ball_y)),BALL_SIZE)

    pygame.draw.aaline(screen,BLACK,(WIDTH//2,0),(WIDTH//2,HEIGHT))

    screen.blit(font.render(str(left_score),True,BLACK),(WIDTH//4-40,10))
    screen.blit(font.render(str(right_score),True,BLACK),(WIDTH*3//4-40,10))

    pygame.display.flip()

pygame.quit()
cap.release()
cv2.destroyAllWindows()