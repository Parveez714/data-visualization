# 📊 AI Data Visualization & Analytics Portal

A high-performance full-stack web application featuring an **AI Data Visualization Agent** and **Dataset Explorer**, built with **React** and a **Python FastAPI backend**.

The interface features a crisp, high-contrast **Black & White monochrome design system**:
* **Layer 0 & Layer 1 Backgrounds**: Clean ambient background with deterministic SVG constellation network.
* **Pure Black Framing (`#000000`)**: High-contrast header bar and typography (`Manrope` + `Inter`).
* **High-Contrast Surfaces**: Clean card surfaces and dividers.
* **Instant Client-Side Filtering**: One-time initial fetch with real-time React `useMemo` in-memory filtering (0ms latency).

---

## 🚀 Key Features

### 1. 🤖 AI Visualization Studio
- **Natural Language Data Analysis**: Query your datasets in plain English (e.g. *"Show overview of sales distribution across categories"*).
- **Google Gemini & Cloud LLM Integration**: Direct execution engine powered by Gemini 2.5 Flash / 3.6 / Pro or Together AI.
- **Smart Local Sandbox**: Built-in heuristic engine with `matplotlib` & `seaborn` rendering.
- **Dynamic Visuals & Export**: High-resolution chart previews, instant PNG downloads, and executive summary insights.

### 2. 🔍 Dataset Explorer & Schema Inspector
- Instant 0ms search across hundreds of rows and columns.
- Statistical summary inspection (`mean`, `std`, `min`, `25%`, `50%`, `75%`, `max`).
- One-click CSV upload and export.

---

## 🛠️ Project Structure

```
data visualization/
├── backend/
│   ├── main.py                  # FastAPI server with endpoints for datasets & analytics
│   ├── agent.py                 # AI agent logic (Gemini + Together AI + Local Matplotlib/Seaborn engine)
│   ├── requirements.txt         # Backend Python requirements
│   └── start_server.py          # Server launcher script
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ConstellationBackground.jsx  # Deterministic SVG constellation network
│   │   │   ├── Header.jsx                   # Black header with status & model switcher
│   │   │   ├── VisualizationStudio.jsx      # AI query box, chart renderer, and insights
│   │   │   ├── DataExplorer.jsx             # 0ms search table & statistical summary
│   │   │   └── ApiSettingsModal.jsx         # Gemini, Together AI & E2B API keys configuration
│   │   ├── App.jsx                          # Main application layout
│   │   ├── index.css                        # B&W design system styles and typography
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── requirements.txt             # Production Python requirements
```

---

## ⚡ Quickstart Guide

### 1. Start the Python Backend

```bash
cd backend
pip install -r requirements.txt
python start_server.py
```

*The backend API runs on [http://localhost:8000](http://localhost:8000).*

### 2. Start the React Frontend

```bash
cd frontend
npm install
npm run dev
```

*Open your browser at [http://localhost:5173](http://localhost:5173).*