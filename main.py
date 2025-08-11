import soundfile as sf
import numpy as np
from PIL import Image
import math

input_image_path = 'tom.png'
encoded_audio_path = 'encoded_audio.wav'
decoded_image_path = 'decoded_image.png'

def image_to_audio(image):
    image = image.convert('RGB')
    pixels = list(image.getdata())
    flat_pixels = []
    for r, g, b in pixels:
        flat_pixels.extend([r, g, b])
    samples = np.array(flat_pixels, dtype=np.uint8)
    float_samples = (samples.astype(np.float32) / 255.0) * 2 - 1
    return float_samples

def audio_to_image(samples, width, height):
    int_samples = ((samples + 1) / 2 * 255).astype(np.uint8)
    rgb_tuples = []
    for i in range(0, len(int_samples), 3):
        r = int_samples[i]
        g = int_samples[i + 1] if i + 1 < len(int_samples) else 0
        b = int_samples[i + 2] if i + 2 < len(int_samples) else 0
        rgb_tuples.append((r, g, b))
    image = Image.new('RGB', (width, height))
    image.putdata(rgb_tuples)
    return image

path = input("image->audio->image / audio->image->audio? ")
if path == "1":
    image_path=input("image path:")
    encoded_audio_path=image_path.replace('.png', '_encoded.wav')
    decoded_image_path=image_path.replace('.png', '_decoded.png')
    image = Image.open(image_path)
    width, height = image.size

    audio_samples = image_to_audio(image)

    sf.write(encoded_audio_path, audio_samples, 44100)

    print(f"Saved encoded audio to {encoded_audio_path}")

    loaded_samples, _ = sf.read(encoded_audio_path)

    decoded_image = audio_to_image(loaded_samples, width, height)
    decoded_image.show()
    decoded_image.save(decoded_image_path)

    print(f"Saved decoded image to {decoded_image_path}")
else:
    audio_path=input("audio path:")
    decoded_image_path=audio_path.replace('.wav', '_decoded.png')
    loaded_samples, samplerate = sf.read(audio_path, always_2d=False)

    if len(loaded_samples.shape) > 1:
        loaded_samples = loaded_samples.mean(axis=1)

    width = 500
    height = width
    print(f"Assumed image dimensions: {width}x{height}")

    decoded_image = audio_to_image(loaded_samples, width, height)
    decoded_image.show()
    decoded_image.save(decoded_image_path)

    print(f"Saved decoded image to {decoded_image_path}")

    image = Image.open(decoded_image_path)
    audio_samples = image_to_audio(image)
    re_encoded_audio_path = audio_path.replace('.wav', '_re_encoded.wav')
    sf.write(re_encoded_audio_path, audio_samples, 44100)
    print(f"Saved re-encoded audio to {re_encoded_audio_path}")