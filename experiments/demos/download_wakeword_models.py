import openwakeword
import os

output_dir = "models/wakeword"
os.makedirs(output_dir, exist_ok=True)

print(f"Downloading models to {output_dir}...")
# openwakeword.utils.download_models() does not accept target_dir in some versions
# It downloads to the package directory by default.
# We will manually download the models we need.

import requests

models = [
    "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/alexa_v0.1.onnx",
    "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/hey_mycroft_v0.1.onnx",
    "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx",
    "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx"
]

for url in models:
    filename = url.split("/")[-1]
    filepath = os.path.join(output_dir, filename)
    print(f"Downloading {filename}...")
    response = requests.get(url)
    if response.status_code == 200:
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"Saved to {filepath}")
    else:
        print(f"Failed to download {filename}: {response.status_code}")

print("Download complete.")
