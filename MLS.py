# -*- coding: utf-8 -*-
"""
Created on Fri Jul  4 21:09:01 2025

@author: Joker.Mao
"""
import numpy as np
from numba import jit, prange
import time
import cv2
from scipy.interpolate import griddata

def mls_rigid(p, q, H, W):
    """
    Moving Least Squares rigid transformation
    
    Parameters:
    p : numpy array (n, 2)
        Source control points
    q : numpy array (n, 2)
        Target control points
    H : int
        Height of output grid
    W : int
        Width of output grid
    
    Returns:
    Xd : numpy array (H, W)
        Deformed X coordinates
    Yd : numpy array (H, W)
        Deformed Y coordinates
    """
    no_ctp = p.shape[0]  # number of control points
    
    # Construct coordinate grids
    X, Y = np.meshgrid(np.arange(1, W+1), np.arange(1, H+1))
    Xd = np.zeros((H, W), dtype=np.float64)
    Yd = np.zeros((H, W), dtype=np.float64)
    
    # Process each pixel
    for r in prange(H):
        if r % 100 == 0:
            print(f'processing line = {r+1} / {H}')
        
        for c in range(W):
            wm = np.zeros(no_ctp)
            
            for idx in range(no_ctp):
                a = X[r, c] - p[idx, 0]
                b = Y[r, c] - p[idx, 1]
                
                # Weights
                if a == 0 and b == 0:
                    wm[idx] = 1e6
                else:
                    wm[idx] = 1.0 / (a*a + b*b)
            
            # Centroids
            s = np.sum(wm)
            pCenX = np.dot(wm, p[:, 0]) / s
            pCenY = np.dot(wm, p[:, 1]) / s
            qCenX = np.dot(wm, q[:, 0]) / s
            qCenY = np.dot(wm, q[:, 1]) / s
            
            pHatX = p[:, 0] - pCenX
            pHatY = p[:, 1] - pCenY
            qHatX = q[:, 0] - qCenX
            qHatY = q[:, 1] - qCenY
            
            pHat = np.column_stack((pHatX, pHatY))
            qHat = np.column_stack((qHatX, qHatY))
            qCen = np.array([qCenX, qCenY])
            pCen = np.array([pCenX, pCenY])
            
            pHatPen = np.column_stack((pHat[:, 1], -pHat[:, 0]))  # -(pHat)#, (x,y)# = (-y,x)
            qHatPen = np.column_stack((qHat[:, 1], -qHat[:, 0]))
            
            a = 0.0
            b = 0.0
            fs = np.zeros(2, dtype=np.float64)
            
            for idx in range(no_ctp):
                a += wm[idx] * np.dot(qHat[idx, :], pHat[idx, :])
                b += wm[idx] * np.dot(qHat[idx, :], -pHatPen[idx, :])
                
                mat1 = np.array([X[r, c] - pCenX, Y[r, c] - pCenY]).dot(
                    np.vstack([pHat[idx, :], pHatPen[idx, :]]))
                mat2 = np.column_stack([qHat[idx, :], qHatPen[idx, :]]).T
                fs += wm[idx] * mat1.dot(mat2)
            
            mur = np.sqrt(a*a + b*b)
            #print(mur)
            fs = fs / mur  # scale fs by mur before going to final scaling by len_vp & len_fs
            
            len_vp = np.sqrt((X[r, c] - pCenX)**2 + (Y[r, c] - pCenY)**2)  # |v - pCen|
            len_fs = np.sqrt(fs[0]**2 + fs[1]**2)
            
            if len_fs > 0:
                fs = len_vp * fs / len_fs + qCen
            else:
                fs = qCen
            
            # Update coordinate
            Xd[r, c] = fs[0]
            Yd[r, c] = fs[1]
    
    return Xd, Yd


# Alternative version using map_coordinates (faster but requires different coordinate handling)
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

if __name__ == "__main__":
    
    img = cv2.imread("input/images/Mona_Lisa_crop.jpg")
    rest_pts   = np.array([[219,276],[147,282],[158,254],[193,255],[179,338],[274,291],[121,286],[107,214],[146,185],[227,185],[284,217],[287,121],[113,125]]) #, % fixed points
    mov_pts = np.array([[225, 299],[143,297],[158,254],[193,255],[179,338],[274,291],[121,286],[107,214],[146,185],[227,185],[284,217],[287,121],[113,125]])# % moving
    
    p = mov_pts
    q = rest_pts
    for ps in p:
        cv2.circle(img, ps, 2, (255,255,0), 2)
    for ps in q:
        cv2.circle(img, ps, 2, (255,255,255), 2)
    
    cv2.imshow("img", img)
    cv2.waitKey(30)
    [H, W] = img.shape[0],img.shape[1]
    [Xd, Yd] = mls_rigid( p, q, H, W)
    img_deform = warp_image_fast(img, Xd, Yd)
    cv2.imwrite("output/img_deform.png", img_deform)
    for ps in p:
        cv2.circle(img_deform, ps, 2, (255,0,0), 2)
    cv2.imshow("img_deform", img_deform)
    
    cv2.waitKey(0)
    if 0:
        np.savez("mls.npz", arr1=Xd, arr2=Yd)
