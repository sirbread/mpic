import soundfile as sf
import numpy as np
from PIL import Image
import math

samples, samplerate = sf.read('audio.wav')
print("data:", samples, "\nsamplerate:", samplerate)

#mock_data = [0, 255, 0, 15, 240, 30, 30, 225, 60, 45, 210, 90, 60, 195, 120, 75, 180, 150, 90, 165, 180, 105, 150, 210, 120, 135, 240, 135, 120, 14, 150, 105, 44, 165, 90, 74, 180, 75, 104, 195, 60, 134, 210, 45, 164, 225, 30, 194, 240, 15, 224]

def scale_audio_to_int(samples):
    if samples.ndim > 1:
        samples = samples.mean(axis=1)  # Convert to mono by averaging channels
    max_val = np.max(np.abs(samples))
    if max_val == 0:
        return [0] * len(samples)
    scaled_samples = (samples / max_val * 255).astype(int)
    return scaled_samples.tolist()

def make_rgb(data):
    rgb_data = []
    for i in range(0, len(data), 3):
        r = int(data[i]) if i < len(data) else 0
        g = int(data[i + 1]) if i + 1 < len(data) else 0
        b = int(data[i + 2]) if i + 2 < len(data) else 0
        rgb_data.append((r, g, b))
    return rgb_data

print(scale_audio_to_int(samples))
rgb_data = make_rgb(scale_audio_to_int(samples))

width = 500
height = 500

grid_size = math.ceil(math.sqrt(len(rgb_data)))

block_width = width // grid_size
block_height = height // grid_size

image = Image.new('RGB', (width, height))

for idx, color in enumerate(rgb_data):
    row = idx // grid_size
    col = idx % grid_size
    start_x = col * block_width
    start_y = row * block_height
    for x in range(start_x, start_x + block_width):
        for y in range(start_y, start_y + block_height):
            if x < width and y < height:
                image.putpixel((x, y), color)
    print(f"block ({col}, {row}) color {color}")

image.show()
