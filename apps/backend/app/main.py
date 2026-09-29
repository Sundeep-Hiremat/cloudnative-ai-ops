import os
import time
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from apps.backend.app.database import engine, Base, get_db
from apps.backend.app import models, schemas

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Order Management API",
    version="1.0.0",
    description="Production-ready REST API for Order Management (Phase 1)"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency in seconds", ["endpoint"])


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time
    
    endpoint = request.url.path
    method = request.method
    status_code = str(response.status_code)
    
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)
    return response


# ------------------------------------------------------------------------------
# Liveness & Readiness Endpoints
# ------------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health_check():
    """Liveness probe: verifies process is alive."""
    return {"status": "ok", "service": "order-management-backend"}


@app.get("/ready", tags=["Health"])
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe: verifies database connection is active."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )


@app.get("/metrics", tags=["Observability"])
def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ------------------------------------------------------------------------------
# Order REST API CRUD Endpoints
# ------------------------------------------------------------------------------
@app.get("/api/orders", response_model=List[schemas.OrderResponse], tags=["Orders"])
def list_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all orders."""
    return db.query(models.Order).offset(skip).limit(limit).all()


@app.post("/api/orders", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Orders"])
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    """Create a new order."""
    db_order = models.Order(
        customer_name=order.customer_name,
        item_name=order.item_name,
        quantity=order.quantity,
        total_price=order.total_price,
        status="PENDING"
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


@app.get("/api/orders/{order_id}", response_model=schemas.OrderResponse, tags=["Orders"])
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get an order by ID."""
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    return db_order


@app.put("/api/orders/{order_id}", response_model=schemas.OrderResponse, tags=["Orders"])
def update_order_status(order_id: int, order_update: schemas.OrderUpdate, db: Session = Depends(get_db)):
    """Update order status."""
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    
    db_order.status = order_update.status
    db.commit()
    db.refresh(db_order)
    return db_order


@app.delete("/api/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Orders"])
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """Delete / cancel an order."""
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    
    db.delete(db_order)
    db.commit()
    return None


# Static Frontend Mounting for local Phase 1 development
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend_static")

@app.get("/", tags=["Frontend"])
def serve_frontend():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Order Management API is running. Access /docs for API documentation."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
