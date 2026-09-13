import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from agent.app.core.config import settings
from agent.app.api.routes import router as api_router
from agent.app.api.websocket import ws_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("kubeops.main")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Autonomous Self-Healing Kubernetes & GitOps AI-Ops Agent"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api")

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keepalive listener
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# Web Dashboard Static Hosting
web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web"))
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

@app.get("/")
async def serve_index():
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "KubeOps-Aegis API is running. Web UI directory not found."}

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
