# -*- coding: utf-8 -*-
"""
Created on Fri Jul  4 21:09:01 2025

@author: Joker.Mao
"""

import cv2
import numpy as np

def fisheye_to_equirectangular(image, f, center_x, center_y, out_width, out_height):
    """
    鱼眼图像展开为等距矩形图像（经纬度展开）

    参数：
    - image: 输入鱼眼图像
    - f: 鱼眼相机焦距（以像素为单位）
    - center_x, center_y: 鱼眼图像的光心坐标
    - out_width, out_height: 输出图像的尺寸

    返回：
    - 等距矩形展开图像
    """
    # 构建输出图像的像素坐标网格
    longitude = np.linspace(-np.pi, np.pi, out_width)
    latitude = np.linspace(-np.pi / 2, np.pi / 2, out_height)
    longitude_map, latitude_map = np.meshgrid(longitude, latitude)

    # 球面角度 -> 3D点
    x = np.cos(latitude_map) * np.sin(longitude_map)
    y = np.sin(latitude_map)
    z = np.cos(latitude_map) * np.cos(longitude_map)

    # 计算入射角 theta
    theta = np.arccos(z)  # 鱼眼相机中的入射角

    # 鱼眼等距模型: r = f * theta
    r = f * theta

    # 计算原图中的像素坐标
    # atan2(y, x) 是当前点相对相机光心的方位角
    phi = np.arctan2(y, x)

    src_x = center_x + r * np.cos(phi)
    src_y = center_y + r * np.sin(phi)

    # 将坐标映射到有效图像范围
    src_x = src_x.astype(np.float32)
    src_y = src_y.astype(np.float32)

    # 使用 remap 进行像素插值
    equirect_image = cv2.remap(image, src_x, src_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    return equirect_image

def warp_image_fast(img, Xd, Yd):
    """
    Faster warping using scipy.ndimage.map_coordinates
    Note: This version uses 0-based indexing for coordinates
    """
    from scipy.ndimage import map_coordinates
    # Convert to 0-based coordinates (subtract 1)
    Xd_0 = Xd - 1
    Yd_0 = Yd - 1
    
    # Initialize output image
    I_deform = np.zeros_like(img)
    
    # Warp each channel separately
    for channel in range(3):
        I_deform[:, :, channel] = map_coordinates(img[:, :, channel], 
                                                [Yd_0.ravel(), Xd_0.ravel()],
                                                order=1,
                                                mode='constant',
                                                cval=0).reshape(img.shape[:2])
    return I_deform

def stitch_dual_fisheye(pano_left, pano_right, blend_width=100):
    
    Xd_Yd=np.load('input/calibration/mls.npz')
    Xd = Xd_Yd["arr1"]
    Yd = Xd_Yd["arr2"]
    
    src_height, src_width = pano_left.shape[:2]
    out_width=pano_left.shape[1]
    out_height=pano_left.shape[0]
    #print (out_width, out_height)
    roi_pos = out_width >> 2
    pano = np.zeros_like(pano_left)

    center = out_width // 2
    left_half = out_width // 4
    right_half = 3 * out_width // 4

    left_width = left_half
    center_width = center - left_half
    right_width = right_half - center
    end_width = out_width - right_half

    # 线性权重融合
    #blend = np.linspace(0, 1, blend_width)[None, :, None] 

    # 左图中心区域
    pano_left = warp_image_fast(pano_left, Xd, Yd)

    pano[:, left_half:right_half] = pano_left[:, left_half:right_half]

    pano[:, right_half: out_width] = pano_right[:, left_half:center]
    pano[:, 0:left_half] = pano_right[:, center:right_half]
    
    return pano

if __name__ == "__main__":
    back_image = cv2.imread('input/images/back_fish.png')
    front_image = cv2.imread('input/images/front_fish.png')
    center_x = back_image.shape[1] / 2
    center_y = back_image.shape[0] / 2
    fov = 192
    f = back_image.shape[0] / (fov * np.pi / 180)  # 焦距（像素）

        
    out_width = back_image.shape[0]
    out_height = back_image.shape[0] // 2

    back_equirect_image = fisheye_to_equirectangular(back_image, f, center_x, center_y, out_width, out_height)
    front_equirect_image = fisheye_to_equirectangular(front_image, f, center_x, center_y, out_width, out_height)

    #cv2.imwrite("./output/l.png", back_equirect_image)
    #cv2.imwrite("./output/r.png", front_equirect_image)
    
    stitch = stitch_dual_fisheye(front_equirect_image, back_equirect_image)
    cv2.imshow('panorama', stitch)

    cv2.imwrite('output/panorama.jpg', stitch)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

