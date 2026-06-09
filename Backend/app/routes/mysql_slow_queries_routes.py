from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

from urllib.parse import quote_plus

from app.database.connection import SessionLocal
from app.models.connection_model import ConnectionMaster

import os
import re

router = APIRouter(
    prefix="/api/v1/mysql",
    tags=["MySQL Slow Queries"]
)

# =========================================================
# DATABASE SESSION
# =========================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =========================================================
# GET MYSQL SLOW QUERIES
# =========================================================

@router.get("/{conn_id}/slow-queries")
def get_slow_queries(

    conn_id: int,
    db: Session = Depends(get_db)

):

    # =====================================================
    # FETCH CONNECTION
    # =====================================================

    connection = db.query(ConnectionMaster).filter(
        ConnectionMaster.id == conn_id
    ).first()

    if not connection:

        raise HTTPException(
            status_code=404,
            detail="Connection not found"
        )

    # =====================================================
    # ENCODE PASSWORD
    # =====================================================

    encoded_password = quote_plus(
        connection.password
    )

    # =====================================================
    # MYSQL URL
    # =====================================================

    mysql_url = (

        f"mysql+pymysql://"

        f"{connection.username}:"

        f"{encoded_password}@"

        f"{connection.host}:"

        f"{connection.port}/"

        f"{connection.database_name}"
    )

    try:

        # =================================================
        # CREATE ENGINE
        # =================================================

        engine = create_engine(mysql_url)

        with engine.connect() as conn:

            # =============================================
            # CHECK SLOW QUERY STATUS
            # =============================================

            slow_status = conn.execute(text("""

                SHOW VARIABLES LIKE 'slow_query_log'

            """)).fetchone()

            slow_file = conn.execute(text("""

                SHOW VARIABLES LIKE 'slow_query_log_file'

            """)).fetchone()

            long_query = conn.execute(text("""

                SHOW VARIABLES LIKE 'long_query_time'

            """)).fetchone()

            slow_query_log = slow_status[1]

            slow_query_log_file = slow_file[1]

            long_query_time = long_query[1]

        # =================================================
        # IF SLOW QUERY DISABLED
        # =================================================

        if slow_query_log != "ON":

            return {

                "status": "success",

                "slow_query_log": "OFF",

                "slow_query_log_file": slow_query_log_file,

                "long_query_time": long_query_time,

                "slow_queries": []
            }

        # =================================================
        # WINDOWS PATH FIX
        # =================================================

        if not os.path.isabs(
            slow_query_log_file
        ):

            slow_query_log_file = (

                "C:/ProgramData/MySQL/MySQL Server 8.0/Data/"

                + slow_query_log_file
            )

        # =================================================
        # CHECK FILE EXISTS
        # =================================================

        if not os.path.exists(
            slow_query_log_file
        ):

            return {

                "status": "error",

                "message": "Slow query log file not found",

                "path": slow_query_log_file,

                "slow_queries": []
            }

        # =================================================
        # READ LOG FILE
        # =================================================

        with open(

            slow_query_log_file,

            "r",

            encoding="utf-8",

            errors="ignore"

        ) as f:

            content = f.read()

        # =================================================
        # PARSE SLOW LOG FILE
        # =================================================

        queries = []

        blocks = content.split("# Time:")

        for block in blocks:

            try:

                if "Query_time:" not in block:
                    continue

                # =========================================
                # TIME
                # =========================================

                time_match = re.search(

                    r"^(.*?)\n",

                    block,

                    re.MULTILINE
                )

                start_time = (

                    time_match.group(1).strip()

                    if time_match else "NA"
                )

                # =========================================
                # QUERY TIME
                # =========================================

                qt_match = re.search(

                    r"Query_time:\s*([\d\.]+)",

                    block
                )

                query_time = (

                    qt_match.group(1)

                    if qt_match else "0"
                )

                # =========================================
                # ROWS EXAMINED
                # =========================================

                rows_match = re.search(

                    r"Rows_examined:\s*(\d+)",

                    block
                )

                rows_examined = (

                    rows_match.group(1)

                    if rows_match else "0"
                )

                # =========================================
                # SQL QUERY
                # =========================================

                sql_match = re.search(

                    r"SET timestamp=.*?;\n(.*?;)",

                    block,

                    re.DOTALL
                )

                sql_text = (

                    sql_match.group(1).strip()

                    if sql_match else "NA"
                )

                queries.append({

                    "start_time": start_time,

                    "db": connection.database_name,

                    "query_time": query_time,

                    "rows_examined": rows_examined,

                    "sql_text": sql_text

                })

            except Exception:

                pass

        # =================================================
        # REVERSE LATEST FIRST
        # =================================================

        queries = queries[::-1]

        # =================================================
        # RETURN RESPONSE
        # =================================================

        return {

            "status": "success",

            "slow_query_log": slow_query_log,

            "slow_query_log_file": slow_query_log_file,

            "long_query_time": long_query_time,

            "total_queries": len(queries),

            "slow_queries": queries
        }

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )