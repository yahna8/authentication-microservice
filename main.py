from fastapi import FastAPI
from routers import users
from database import Base, engine
import uvicorn

app = FastAPI()

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Include the router
app.include_router(users.router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
