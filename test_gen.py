import requests
import base64

URL = "http://127.0.0.1:8000/generate"

# Get token
token_res = requests.post("http://127.0.0.1:8000/token", data={"username": "user", "password": "password123"})
print("Token Response:", token_res.status_code, token_res.text)
token = token_res.json()["access_token"]

# Payload from frontend
payload = {
    "lyrics": "Sa ri ga ma",
    "ragam": "Mayamalavagowla",
    "talam": "Adi",
    "pitch": 261.63,
    "pitch_name": "C",
    "tempo": 90,
    "scale": "Madhya",
    "instrument": "Violin"
}

headers = {"Authorization": f"Bearer {token}"}
res = requests.post(URL, json=payload, headers=headers)

print("Generate Status:", res.status_code)
if res.status_code != 200:
    print("Error Detail:", res.text)
else:
    print("Success! notation length:", len(res.json()["notation"]))
    print("Audio length (base64 chars):", len(res.json()["audio_base64"]))
