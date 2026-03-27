import requests

# Test the new schema
token_res = requests.post("http://127.0.0.1:8000/token", data={"username": "user", "password": "password123"})
token = token_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Test Sarali Mode
payload_sarali = {
    "ragam": "Mayamalavagowla",
    "pitch_name": "C",
    "tempo": 90,
    "use_sarali": True,
    "sarali_index": 1
}
res1 = requests.post("http://127.0.0.1:8000/generate", json=payload_sarali, headers=headers)
print("Sarali Test:", res1.status_code)
if res1.status_code == 200:
    print("  Notation:", [n['swara'] for n in res1.json()['notation']])

# Test Lyrics Mode
payload_lyrics = {
    "ragam": "Mohanam",
    "pitch_name": "D",
    "tempo": 120,
    "lyrics": "Sa-Ri-Ga-Pa-Da",
    "use_sarali": False
}
res2 = requests.post("http://127.0.0.1:8000/generate", json=payload_lyrics, headers=headers)
print("Lyrics Test:", res2.status_code)
if res2.status_code == 200:
    print("  Notation:", [n['swara'] for n in res2.json()['notation']])
    print("  Lyrics:", [n['lyric'] for n in res2.json()['notation']])
