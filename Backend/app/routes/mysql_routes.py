from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import datetime

from urllib.parse import quote_plus

from app.database.connection import SessionLocal
from app.models.connection_model import ConnectionMaster
from app.models.connection_schema import MySQLConnectionCreate

router = APIRouter(
    prefix="/api/v1/connections/mysql",
    tags=["MySQL"]
)

# DATABASE SESSION
def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# GET ALL MYSQL CONNECTIONS
@router.get("/")
def list_mysql_connections(
    db: Session = Depends(get_db)
):

    connections = db.query(ConnectionMaster).filter(
        ConnectionMaster.db_type == "mysql"
    ).all()

    return {
        "status": "success",
        "data": connections
    }


# CREATE MYSQL CONNECTION
@router.post("/")
def create_mysql_connection(
    request: MySQLConnectionCreate,
    db: Session = Depends(get_db)
):

    # ENCODE PASSWORD
    encoded_password = quote_plus(request.password)

    # MYSQL CONNECTION URL
    mysql_url = (
        f"mysql+pymysql://{request.username}:"
        f"{encoded_password}@"
        f"{request.host}:"
        f"{request.port}/"
        f"{request.database_name}"
    )

    try:

        # TEST MYSQL CONNECTION
        engine = create_engine(mysql_url)

        connection = engine.connect()

        connection.close()

    except SQLAlchemyError as e:

        raise HTTPException(
            status_code=400,
            detail=f"MySQL Connection Failed: {str(e)}"
        )

    # SAVE CONNECTION
    new_connection = ConnectionMaster(
        connection_name=request.connection_name,
        db_type="mysql",
        host=request.host,
        port=request.port,
        username=request.username,
        password=request.password,
        database_name=request.database_name
    )
    # (no server/OS configuration persisted in this route)

    db.add(new_connection)

    db.commit()

    db.refresh(new_connection)

    return {
        "status": "success",
        "message": "MySQL Connection Successful",
        "data": {
            "id": new_connection.id,
            "connection_name": new_connection.connection_name,
            "host": new_connection.host
        }
    }


# DELETE MYSQL CONNECTION
@router.delete("/{conn_id}")
def delete_mysql_connection(
    conn_id: int,
    db: Session = Depends(get_db)
):

    connection = db.query(ConnectionMaster).filter(
        ConnectionMaster.id == conn_id
    ).first()

    if not connection:

        raise HTTPException(
            status_code=404,
            detail="Connection Not Found"
        )

    db.delete(connection)

    db.commit()

    return {
        "status": "success",
        "message": "Connection Deleted Successfully"
    }


# MYSQL TELEMETRY DASHBOARD
@router.get("/{conn_id}/dashboard")
def get_mysql_dashboard(
    conn_id: int,
    db: Session = Depends(get_db)
):
    connection = db.query(ConnectionMaster).filter(
        ConnectionMaster.id == conn_id,
        ConnectionMaster.db_type == "mysql"
    ).first()

    if not connection:
        raise HTTPException(
            status_code=404,
            detail="Connection Profile Not Found"
        )

    conn_meta = {
        "id": connection.id,
        "name": connection.connection_name,
        "host": connection.host,
        "port": connection.port,
        "database": connection.database_name
    }

    # Build connection URL safely
    encoded_password = quote_plus(connection.password) if connection.password else ""
    user_part = f"{connection.username}" if connection.username else ""
    pass_part = f":{encoded_password}" if connection.password else ""
    auth_part = f"{user_part}{pass_part}@" if (user_part or pass_part) else ""
    db_name = connection.database_name or ""
    mysql_url = f"mysql+pymysql://{auth_part}{connection.host}:{connection.port}/{db_name}"

    try:
        # Connect to MySQL and gather status and telemetry variables
        engine = create_engine(
            mysql_url,
            connect_args={
                "connect_timeout": 3,
                "read_timeout": 3,
                "write_timeout": 3
            }
        )
        with engine.connect() as conn:
            status_dict = {}
            try:
                res_status = conn.execute(text("SHOW GLOBAL STATUS;"))
                status_dict = {row[0]: row[1] for row in res_status.fetchall()}
            except Exception:
                try:
                    res_status = conn.execute(text("SHOW STATUS;"))
                    status_dict = {row[0]: row[1] for row in res_status.fetchall()}
                except Exception:
                    pass

            vars_dict = {}
            try:
                res_vars = conn.execute(text("SHOW GLOBAL VARIABLES;"))
                vars_dict = {row[0]: row[1] for row in res_vars.fetchall()}
            except Exception:
                try:
                    res_vars = conn.execute(text("SHOW VARIABLES;"))
                    vars_dict = {row[0]: row[1] for row in res_vars.fetchall()}
                except Exception:
                    pass

            # Helpers for parsing types
            def to_int(val, default=0):
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return default

            def to_float(val, default=0.0):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            # Calculation for Uptime & Restart Time
            uptime_sec = to_int(status_dict.get("Uptime", 0))
            uptime_str = "0s"
            last_restart_str = "NA"
            if uptime_sec > 0:
                days = uptime_sec // 86400
                hours = (uptime_sec % 86400) // 3600
                minutes = (uptime_sec % 3600) // 60
                if days > 0:
                    uptime_str = f"{days}d {hours}h {minutes}m"
                else:
                    uptime_str = f"{hours}h {minutes}m"
                
                # Approximate calculation
                last_restart = datetime.datetime.now() - datetime.timedelta(seconds=uptime_sec)
                last_restart_str = last_restart.strftime("%Y-%m-%d %H:%M:%S")

            version = vars_dict.get("version", "NA")
            hostname = vars_dict.get("hostname", "NA")
            storage_engine = vars_dict.get("default_storage_engine", "InnoDB")

            max_conns = to_int(vars_dict.get("max_connections", 151))
            current_conns = to_int(status_dict.get("Threads_connected", 1))
            conn_usage_pct = round((current_conns / max_conns) * 100, 2) if max_conns > 0 else 0.0

            # Buffer Cache Usage %
            read_req = to_int(status_dict.get("Innodb_buffer_pool_read_requests", 0))
            reads = to_int(status_dict.get("Innodb_buffer_pool_reads", 0))
            cache_usage_pct = 100.0
            if read_req > 0:
                cache_usage_pct = round((1 - (reads / read_req)) * 100, 2)

            # Query Databases and compute details
            databases_list = []
            total_dbs = 0
            total_tbls = 0
            total_sz_bytes = 0

            try:
                db_query = text("""
                    SELECT 
                        table_schema AS db_name,
                        COUNT(*) AS tables_count,
                        SUM(data_length + index_length) AS size_bytes
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                    GROUP BY table_schema;
                """)
                res_dbs = conn.execute(db_query)
                for r in res_dbs.fetchall():
                    d_name = r[0]
                    d_tables = to_int(r[1])
                    d_bytes = to_int(r[2])
                    d_mb = round(d_bytes / (1024 * 1024), 2)
                    databases_list.append({
                        "name": d_name,
                        "tables_count": d_tables,
                        "size_mb": d_mb
                    })
                    if d_name not in ["information_schema", "performance_schema", "mysql", "sys"]:
                        total_dbs += 1
                        total_tbls += d_tables
                        total_sz_bytes += d_bytes
            except Exception:
                try:
                    res_show = conn.execute(text("SHOW DATABASES;"))
                    for r in res_show.fetchall():
                        databases_list.append({
                            "name": r[0],
                            "tables_count": 0,
                            "size_mb": 0.0
                        })
                    total_dbs = len(databases_list)
                except Exception:
                    pass

            total_sz_mb = round(total_sz_bytes / (1024 * 1024), 2)
            total_sz_gb = round(total_sz_mb / 1024, 2)

            # Process List
            process_list = []
            try:
                res_proc = conn.execute(text("SHOW FULL PROCESSLIST;"))
                for r in res_proc.fetchall():
                    process_list.append({
                        "Id": r[0],
                        "User": r[1],
                        "Host": r[2],
                        "db": r[3],
                        "Command": r[4],
                        "Time": r[5],
                        "State": r[6],
                        "Info": r[7]
                    })
            except Exception:
                pass

            long_running_queries = [
                proc for proc in process_list
                if to_int(proc.get("Time", 0)) >= 1 and proc.get("Command") != "Sleep"
            ]

            # Replication status
            replication_dict = {}
            replication_state = "STANDALONE"
            try:
                res_repl = conn.execute(text("SHOW SLAVE STATUS;"))
                row_repl = res_repl.fetchone()
                if not row_repl:
                    try:
                        res_repl = conn.execute(text("SHOW REPLICA STATUS;"))
                        row_repl = res_repl.fetchone()
                    except Exception:
                        pass
                
                if row_repl:
                    replication_state = "REPLICA"
                    try:
                        keys = res_repl.keys()
                        for k, v in zip(keys, row_repl):
                            if isinstance(v, (int, float)):
                                replication_dict[k] = v
                            elif v is None:
                                replication_dict[k] = ""
                            else:
                                replication_dict[k] = str(v)
                    except Exception:
                        for idx, v in enumerate(row_repl):
                            replication_dict[f"field_{idx}"] = str(v) if v is not None else ""
            except Exception:
                pass

            slow_log = vars_dict.get("slow_query_log", "OFF")
            long_query = to_float(vars_dict.get("long_query_time", 10.0))
            slow_log_file = vars_dict.get("slow_query_log_file", "")

            # Memory buffer pool
            buf_pool_size = to_int(vars_dict.get("innodb_buffer_pool_size", 0))
            buf_pool_size_mb = round(buf_pool_size / (1024 * 1024), 2)
            pages_data = to_int(status_dict.get("Innodb_buffer_pool_pages_data", 0))
            pages_total = to_int(status_dict.get("Innodb_buffer_pool_pages_total", 0))

            payload = {
                "status": "success",
                "connection": conn_meta,
                "health_summary": {
                    "uptime": uptime_str,
                    "last_restart": last_restart_str,
                    "host_name": hostname,
                    "version": version,
                    "replication_state": replication_state,
                    "connection_usage_pct": conn_usage_pct,
                    "cache_usage_pct": cache_usage_pct,
                    "total_databases": total_dbs,
                    "total_tables": total_tbls,
                    "total_size_mb": total_sz_mb,
                    "total_size_gb": total_sz_gb,
                    "current_connections": current_conns,
                    "max_connections": max_conns,
                    "storage_engine": storage_engine
                },
                "databases": databases_list,
                "chart_data": {
                    "connection_pct": conn_usage_pct,
                    "cache_pct": cache_usage_pct,
                    "query_stats": {
                        "labels": ["Com_select", "Com_insert", "Com_update", "Com_delete"],
                        "values": [
                            to_int(status_dict.get("Com_select", 0)),
                            to_int(status_dict.get("Com_insert", 0)),
                            to_int(status_dict.get("Com_update", 0)),
                            to_int(status_dict.get("Com_delete", 0))
                        ]
                    },
                    "db_sizes": [
                        {"name": db["name"], "size_mb": db["size_mb"]}
                        for db in databases_list if db["name"] not in ["information_schema", "performance_schema", "mysql", "sys"]
                    ][:10]
                },
                "connections_detail": {
                    "current": current_conns,
                    "max": max_conns,
                    "connection_usage_pct": conn_usage_pct
                },
                "memory": {
                    "buffer_pool_size_mb": buf_pool_size_mb,
                    "pages_data": pages_data,
                    "pages_total": pages_total,
                    "read_requests": read_req,
                    "reads": reads,
                    "cache_usage_pct": cache_usage_pct
                },
                "query_stats": {
                    "Com_select": to_int(status_dict.get("Com_select", 0)),
                    "Com_insert": to_int(status_dict.get("Com_insert", 0)),
                    "Com_update": to_int(status_dict.get("Com_update", 0)),
                    "Com_delete": to_int(status_dict.get("Com_delete", 0)),
                    "Questions": to_int(status_dict.get("Questions", 0)),
                    "Slow_queries": to_int(status_dict.get("Slow_queries", 0))
                },
                "network": {
                    "bytes_received": to_int(status_dict.get("Bytes_received", 0)),
                    "bytes_sent": to_int(status_dict.get("Bytes_sent", 0))
                },
                "slow_query_config": {
                    "slow_query_log": slow_log,
                    "long_query_time": long_query,
                    "slow_query_log_file": slow_log_file
                },
                "error_log_path": vars_dict.get("log_error", "NA"),
                "error_log_count": 0,
                "process_list": process_list,
                "long_running_queries": long_running_queries,
                "replication": replication_dict
            }
            return payload

    except Exception as e:
        return {
            "status": "error",
            "error": f"MySQL Connection Failed: {str(e)}",
            "connection": conn_meta
        }