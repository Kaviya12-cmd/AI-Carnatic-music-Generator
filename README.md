# Carnatic AI Song Generator

A full-stack AI application that generates Carnatic music compositions with Violin-based swara synthesis.

## Features
- **Authentication**: Secure login system.
- **Ragam Engine**: Rule-based generation for 20+ Carnatic Ragams (Arohanam/Avarohanam).
- **Talam Support**: Rhythmic controls for Adi, Rupaka, Chapu talams.
- **violin-Audio**: Custom Python-based audio synthesis engine mimicking violin timbre and gamakas.
- **Responsive UI**: Glassmorphism design with React.

## Prerequisites
- Python 3.9+
- Node.js & npm
- VS Code

## Structure
- `/backend`: FastAPI Python server (Logic & Audio Engine)
- `/frontend`: React Vite application (UI)

## Setup Instructions

### 1. Backend Setup
Open a terminal in `violin_based_generator/backend`:

```powershell
cd backend
# Create virtual environment (optional but recommended)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Server
uvicorn app.main:app --reload
```
Server will start at `http://127.0.0.1:8000`

### 2. Frontend Setup
Open a NEW terminal in `violin_based_generator/frontend`:

```powershell
cd frontend

# Install dependencies
npm install

# Run Development Server
npm run dev
```
Frontend will start at `http://localhost:5173`

## Usage
1. Go to `http://localhost:5173`.
2. Login with generic credentials: 
   - User: `user`
   - Password: `password123`
3. Enter lyrics (e.g., "Sa Ri Ga Ma").
4. Select a Ragam (e.g., "Mayamalavagowla") and Talam.
5. Choose a Gamaka style (e.g., "Kampitam" for vibrato).
6. Click **Generate** and listen to the AI-synthesized violin output!
