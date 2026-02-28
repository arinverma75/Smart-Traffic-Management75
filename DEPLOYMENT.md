# How to Deploy This Project Online

## Why Vercel Does Not Work for This Project

**Vercel** is built for:
- **Static sites** (HTML/JS/CSS)
- **Serverless functions** (short, small Node.js or Python functions)
- **Short timeouts** (e.g. 10–60 seconds)
- **Size limits** (e.g. 50 MB compressed for serverless)

**This project** needs:
- A **long-running server** (FastAPI + Uvicorn) that stays on
- **Heavy Python packages**: PyTorch (~2 GB), Ultralytics, OpenCV (large binaries)
- **Video/camera streaming** and file uploads (not typical serverless)
- **No strict 50 MB limit** – the app is too big for Vercel serverless

So **Vercel is not a good fit**. Use a platform that runs **containers** or **long-running web services** instead.

---

## Options That Work

### Option 1: Railway (recommended – simple)

1. Push your code to **GitHub**.
2. Go to [railway.app](https://railway.app) → Sign in with GitHub.
3. **New Project** → **Deploy from GitHub repo** → select your repo.
4. Railway will detect the app. Set:
   - **Root Directory:** (leave blank if app is at repo root)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add a **Variable:** `PORT` is usually set by Railway; if not, set `PORT=8000`.
6. Click **Deploy**. Railway will build and give you a URL like `https://your-app.up.railway.app`.

**Note:** First deploy may take 10–15 minutes (PyTorch/Ultralytics are large). Free tier has limits; paid tier is better for heavy ML.

---

### Option 2: Render (free tier available)

1. Push code to **GitHub**.
2. Go to [render.com](https://render.com) → Sign in with GitHub.
3. **New** → **Web Service** → connect your repo.
4. Settings:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Environment Variables:** Add `PORT` (Render usually sets this automatically).
6. **Create Web Service**. You get a URL like `https://your-app.onrender.com`.

**Note:** Free tier spins down after ~15 min idle; first request can be slow (cold start). Build can take 15+ minutes due to PyTorch.

---

### Option 3: Docker (works on any host)

Use the **Dockerfile** in this repo. Then you can run the same image on:
- Your own VPS (DigitalOcean, Linode, AWS EC2)
- Google Cloud Run
- AWS ECS / Fargate
- Fly.io

**Build and run locally:**
```bash
docker build -t traffic-app .
docker run -p 8000:8000 traffic-app
```

**On a server:** push the image to Docker Hub or GitHub Container Registry, then pull and run on the server.

---

### Option 4: Run on a VPS (full control)

> **Tip:** copy `.env.example` from the repository root and edit it with your own values. Rename to `.env` before starting the server, or set environment variables directly in your shell.


1. Rent a **Linux VPS** (e.g. DigitalOcean, Linode, AWS EC2 – at least 2 GB RAM, 4 GB for smoother ML).
2. SSH into the server, install Python 3.10+, clone your repo.
3. Create venv, install dependencies: `pip install -r requirements.txt`
4. Run with a process manager so it stays up:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
5. Use **Nginx** (or Caddy) as reverse proxy and add **HTTPS** (e.g. Let’s Encrypt).
6. Use **systemd** or **supervisor** to keep the app running and restart on crash.

---

## Summary

| Platform   | Best for              | Difficulty |
|-----------|------------------------|------------|
| Railway   | Quick deploy, GitHub   | Easy       |
| Render    | Free tier, GitHub      | Easy       |
| Docker    | Any cloud / VPS        | Medium     |
| VPS       | Full control, 24/7    | Medium     |

**Do not use:** Vercel, Netlify (serverless), or similar – they are not meant for long-running Python apps with large ML dependencies.

Use **Railway** or **Render** for the easiest online deploy; use **Docker** or a **VPS** if you need more control or a custom server.
