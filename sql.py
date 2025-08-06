import pymysql
from typing import List, Dict

DB_CFG = {
    "host":     "8.138.3.143",
    "port":     3306,
    "user":     "root",
    "password": "123456",
    "database": "hxbank",
    "charset":  "utf8mb4",
}

def get_account_by_ids(ids: List[int]) -> List[Dict]:
    """
    根据节点 id 列表查询 name、acct_no
    :param ids: 风险团伙节点 id 列表
    :return:  [{"id": 1, "name": "xxx", "acct_no": "A00001"}, ...]
    """
    if not ids:
        return []

    placeholders = ",".join(["%s"] * len(ids))
    sql = f"""
        SELECT id, name, acct_no
        FROM bill_account
        WHERE id IN ({placeholders})
    """

    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, ids)
            return cur.fetchall()
    finally:
        conn.close()