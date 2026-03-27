import requests
import base64

def test_sahana():
    # Get token
    token_res = requests.post("http://127.0.0.1:8000/token", data={"username": "user", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generation Request for Sahana
    payload = {
        "ragam": "Sahana",
        "pitch_name": "C",
        "tempo": 90,
        "lyrics": "",
        "use_sarali": False,
        "sarali_index": 1
    }

    res = requests.post("http://127.0.0.1:8000/generate", json=payload, headers=headers)
    print("Status:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        print("Sahana notation:", [n['swara'] for n in data['notation']])
        # Check for M1 P M1 or similar Sahana characteristic
        # Arohanam: S R2 G3 M1 P M1 D2 N2 S'
        # Avarohanam: S' N2 D2 P M1 G3 M1 R2 S
    else:
        print("Error:", res.text)

if __name__ == "__main__":
    test_sahana()
