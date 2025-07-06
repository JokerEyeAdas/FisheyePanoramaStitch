# -*- coding: utf-8 -*-
"""
Created on Sat Jul  5 19:16:29 2025

@author: Joker.Mao
"""

import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image
import numpy as np
import math

# 视角参数
yaw, pitch = 0.0, 0.0
lastX, lastY = 400, 300
fov = 60.0
first_mouse = True
left_button_pressed = False

# 相机参数
camera_pos = np.array([0.0, 0.0, 0.0], dtype=np.float32)  # 默认在球心
camera_front = np.array([0.0, 0.0, -1.0], dtype=np.float32)  # 默认朝 -Z
camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
camera_speed = 2.5  # 移动速度，单位：每秒

def load_texture(path):
    img = Image.open(path)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img_data = np.array(img.convert("RGB"), np.uint8)

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.width, img.height, 0,
                 GL_RGB, GL_UNSIGNED_BYTE, img_data)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    return tex_id

def sphere(radius, slices, stacks):
    for i in range(stacks):
        lat0 = math.pi * (-0.5 + float(i) / stacks)
        z0 = radius * math.sin(lat0)
        zr0 = radius * math.cos(lat0)

        lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
        z1 = radius * math.sin(lat1)
        zr1 = radius * math.cos(lat1)

        glBegin(GL_QUAD_STRIP)
        for j in range(slices + 1):
            lng = 2 * math.pi * float(j) / slices
            x = math.cos(lng)
            y = math.sin(lng)

            # 纹理坐标，u,v对应经纬度映射
            u = float(j) / slices

            glTexCoord2f(u, 1 - float(i) / stacks)
            glNormal3f(-x * zr0, -y * zr0, -z0)  # 贴内面，法线朝内
            glVertex3f(x * zr0, y * zr0, z0)

            glTexCoord2f(u, 1 - float(i + 1) / stacks)
            glNormal3f(-x * zr1, -y * zr1, -z1)
            glVertex3f(x * zr1, y * zr1, z1)
        glEnd()

def mouse_callback(window, xpos, ypos):
    global lastX, lastY, yaw, pitch, first_mouse

    if not left_button_pressed:
        first_mouse = True
        return

    if first_mouse:
        lastX, lastY = xpos, ypos
        first_mouse = False

    xoffset = xpos - lastX
    yoffset = lastY - ypos  # 上下反向
    lastX, lastY = xpos, ypos

    sensitivity = 0.1
    xoffset *= sensitivity
    yoffset *= sensitivity

    global yaw, pitch
    yaw += xoffset
    pitch += yoffset

    if pitch > 89.0:
        pitch = 89.0
    if pitch < -89.0:
        pitch = -89.0

def scroll_callback(window, xoffset, yoffset):
    global fov
    fov -= yoffset
    if fov < 20.0:
        fov = 20.0
    if fov > 90.0:
        fov = 90.0

def mouse_button_callback(window, button, action, mods):
    global left_button_pressed
    if button == glfw.MOUSE_BUTTON_LEFT:
        if action == glfw.PRESS:
            left_button_pressed = True
        elif action == glfw.RELEASE:
            left_button_pressed = False

def process_input(window, delta_time):
    global camera_pos, camera_front, camera_up, camera_speed, yaw, pitch

    velocity = camera_speed * delta_time

    # 计算右向量
    right = np.cross(camera_front, camera_up)
    right /= np.linalg.norm(right)

    # WASD移动
    if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
        camera_pos += camera_front * velocity
    if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        camera_pos -= camera_front * velocity
    if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
        camera_pos -= right * velocity
    if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
        camera_pos += right * velocity

def main():
    global camera_front

    if not glfw.init():
        return

    window = glfw.create_window(800, 600, "PanoramaViewer", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)

    glfw.set_cursor_pos_callback(window, mouse_callback)
    glfw.set_scroll_callback(window, scroll_callback)
    glfw.set_mouse_button_callback(window, mouse_button_callback)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    #需要注意图像分辨率，需要偶数分辨率，尽量是4的倍数
    texture_id = load_texture("output/panorama.jpg")

    last_frame_time = glfw.get_time()

    while not glfw.window_should_close(window):
        current_frame_time = glfw.get_time()
        delta_time = current_frame_time - last_frame_time
        last_frame_time = current_frame_time

        process_input(window, delta_time)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        width, height = glfw.get_framebuffer_size(window)
        aspect_ratio = width / height if height > 0 else 1

        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(fov, aspect_ratio, 0.1, 100.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # 计算相机方向（根据yaw/pitch）
        front_x = math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))
        front_y = math.sin(math.radians(pitch))
        front_z = math.sin(math.radians(yaw)) * math.cos(math.radians(pitch))
        camera_front = np.array([front_x, front_y, front_z], dtype=np.float32)
        camera_front /= np.linalg.norm(camera_front)

        # 视点从camera_pos看向 camera_pos + camera_front
        center = camera_pos + camera_front

        gluLookAt(camera_pos[0], camera_pos[1], camera_pos[2],
                  center[0], center[1], center[2],
                  camera_up[0], camera_up[1], camera_up[2])

        glBindTexture(GL_TEXTURE_2D, texture_id)
        sphere(1.0, 50, 50)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()
