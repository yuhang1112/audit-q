import pymysql
import pandas as pd
from typing import List, Dict
from config import DB_CFG

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

def get_overdue_dataset() -> pd.DataFrame:
    """
    返回 DataFrame：
    loan_id, loan_amount, interest_rate, credit_score, risk_level_num,
    customer_type_num, days_since_approval, max_overdue_days, days_to_next_due, is_overdue_30
    """
    sql = """
    SELECT
        l.loan_id,
        l.loan_amount,
        l.interest_rate,
        c.credit_score,
        CASE c.risk_level
            WHEN 'Low' THEN 0
            WHEN 'Medium' THEN 1
            WHEN 'High' THEN 2
        END AS risk_level_num,
        CASE c.customer_type
            WHEN 'Personal' THEN 0
            ELSE 1
        END AS customer_type_num,
        DATEDIFF(CURDATE(), l.approval_date) AS days_since_approval,
        COALESCE(MAX(o.overdue_days), 0) AS max_overdue_days,
        (SELECT DATEDIFF(MAX(due_date), CURDATE())
         FROM repayment_schedule
         WHERE loan_id = l.loan_id AND status = 'Pending'
         LIMIT 1) AS days_to_next_due,
        CASE WHEN COUNT(o.overdue_id) > 0 THEN 1 ELSE 0 END AS is_overdue_30
    FROM loans l
    JOIN customers c ON l.customer_id = c.customer_id
    LEFT JOIN overdue_loans o ON l.loan_id = o.loan_id
    WHERE l.loan_status <> 'Completed'
    GROUP BY l.loan_id, l.loan_amount, l.interest_rate, c.credit_score, risk_level_num, customer_type_num, days_since_approval
    """
    conn = pymysql.connect(**DB_CFG)
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()