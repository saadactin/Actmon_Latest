from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.mysql_routes import router as mysql_router
from app.routes.oracle_routes import router as oracle_router
from app.routes.postgres_routes import router as postgres_router
from app.routes.mongo_routes import router as mongo_router
from app.routes.clickhouse_routes import router as clickhouse_router
from app.routes.mssql_routes import router as mssql_router

from app.routes.postgres_error_analysis_routes import router as postgres_error_router
from app.routes.mongo_error_analysis_routes import router as mongo_error_router
from app.routes.clickhouse_error_analysis_routes import router as clickhouse_error_router
from app.routes.mssql_error_analysis_routes import router as mssql_error_router

from app.database.connection import engine
from app.models.connection_model import Base
from app.routes.mysql_slow_queries_routes import router as mysql_slow_queries_router
from app.routes.mysql_explain_routes import router as mysql_explain_router
from app.routes.mysql_error_logs_routes import router as mysql_error_logs_router
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ACTMON API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection CRUD routes
app.include_router(mysql_router)
app.include_router(oracle_router)
app.include_router(postgres_router)
app.include_router(mongo_router)
app.include_router(clickhouse_router)
app.include_router(mssql_router)

# Error analysis routes
app.include_router(postgres_error_router)
app.include_router(mongo_error_router)
app.include_router(clickhouse_error_router)
app.include_router(mssql_error_router)

# MySQL specific routes
app.include_router(mysql_slow_queries_router)
app.include_router(mysql_explain_router)
app.include_router(mysql_error_logs_router)


@app.get("/")
def home():
    return {
        "status": "success",
        "message": "ACTMON Backend Running Successfully"
    }