import cv2
import numpy as np
from PIL import Image
from rembg import remove
import os

def overlay_image_on_video(video_path, image_path, output_path):
    # 1. Remove background from the samurai image
    input_img = Image.open(image_path)
    output_img = remove(input_img)
    samurai_np = np.array(output_img)
    
    # Extract alpha channel
    if samurai_np.shape[2] == 4:
        alpha_s = samurai_np[:, :, 3] / 255.0
        alpha_l = 1.0 - alpha_s
        samurai_rgb = samurai_np[:, :, :3]
    else:
        # Fallback if no alpha channel
        return False

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Resize samurai to fit the scene (adjust scale as needed)
    scale_factor = 0.5 # Example scale
    new_width = int(samurai_rgb.shape[1] * scale_factor)
    new_height = int(samurai_rgb.shape[0] * scale_factor)
    samurai_rgb_resized = cv2.resize(samurai_rgb, (new_width, new_height))
    alpha_s_resized = cv2.resize(alpha_s, (new_width, new_height))
    alpha_l_resized = 1.0 - alpha_s_resized
    
    # Example position (bottom right)
    y1, y2 = height - new_height - 50, height - 50
    x1, x2 = width - new_width - 100, width - 100

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Convert frame to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Overlay
        for c in range(0, 3):
            frame_rgb[y1:y2, x1:x2, c] = (alpha_s_resized * samurai_rgb_resized[:, :, c] +
                                          alpha_l_resized * frame_rgb[y1:y2, x1:x2, c])
                                          
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        out.write(frame_bgr)

    cap.release()
    out.release()
    print("Done")

video = "signin.mp4"
image = r"C:\Users\Rohit\.gemini\antigravity-ide\brain\03fa8999-97dd-4626-8ddb-e0a18265fcfb\.user_uploaded\media_1791305767914.png"
out = "signin_new.mp4"
overlay_image_on_video(video, image, out)
