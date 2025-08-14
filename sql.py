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

AS_OF_DATE = '2025-06-08' # 特征日
VAL_END = '2025-07-09' # 验证日
def get_overdue_dataset() -> pd.DataFrame:
    """
    返回 DataFrame：
    loan_id, loan_amount, interest_rate, credit_score, risk_level_num,
    customer_type_num, days_since_approval, max_overdue_days, days_to_next_due, is_overdue_30
    """
    sql = f"""
    -- 生成特征 + 标签
    SELECT
        l.loan_id,
        l.loan_amount,
        l.interest_rate,
        l.approval_date,
        c.credit_score,

        -- 枚举转数值
        CASE c.risk_level
            WHEN 'Low' THEN 0 WHEN 'Medium' THEN 1 WHEN 'High' THEN 2
        END AS risk_level_num,
        CASE c.customer_type WHEN 'Personal' THEN 0 ELSE 1 END AS customer_type_num,

        -- 特征：审批日已过去多少天
        DATEDIFF('{AS_OF_DATE}', l.approval_date) AS days_since_approval,

        -- 特征：截至特征日 的最大历史逾期天数
        COALESCE(MAX(CASE WHEN o.last_repayment_date <= '{AS_OF_DATE}' THEN o.overdue_days END), 0) AS max_overdue_days,

        -- 特征：截至特征日 下一笔待还多少天
        COALESCE(
            DATEDIFF(
                (SELECT MIN(due_date)
                FROM repayment_schedule
                WHERE loan_id = l.loan_id
                AND due_date > '{AS_OF_DATE}'
                AND status = 'Pending'),
                '{AS_OF_DATE}'
            ),
            9999
        ) AS days_to_next_due,

        -- 标签：特征日 起 30 天内是否出现逾期
        CASE WHEN SUM(o.overdue_days) > 0 THEN 1 ELSE 0 END AS is_overdue_30
    FROM loans l
    LEFT JOIN customers         c ON c.customer_id = l.customer_id
    LEFT JOIN overdue_loans     o ON o.loan_id = l.loan_id
    WHERE l.approval_date < '{AS_OF_DATE}'   -- 贷款必须在特征截止日前已发生
    GROUP BY l.loan_id;
    """
    conn = pymysql.connect(**DB_CFG)
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()

def get_overdue_valset() -> pd.DataFrame:
    """
    返回 DataFrame：
    loan_id, loan_amount, interest_rate, credit_score, risk_level_num,
    customer_type_num, days_since_approval, max_overdue_days, days_to_next_due
    """
    sql = f"""
    -- 验证集（特征、标签均按 2025-06-08 计算）
    SELECT
        l.loan_id,
        l.loan_amount,
        l.interest_rate,
        c.credit_score,
        CASE c.risk_level WHEN 'Low' THEN 0 WHEN 'Medium' THEN 1 WHEN 'High' THEN 2 END AS risk_level_num,
        CASE c.customer_type WHEN 'Personal' THEN 0 ELSE 1 END AS customer_type_num,
        DATEDIFF('{VAL_END}', l.approval_date) AS days_since_approval,
        -- 历史已逾期 与 未来 30 天是否逾期 是 两个不同标签。前者是“截至 '{AS_OF_DATE}' 的历史逾期”，后者是“'{AS_OF_DATE}' 起 30 天内是否逾期”
        COALESCE(MAX(CASE WHEN o.last_repayment_date <= '{AS_OF_DATE}' THEN o.overdue_days END), 0) AS max_overdue_days,
        COALESCE(
            DATEDIFF(
                (SELECT MIN(due_date)
                FROM repayment_schedule
                WHERE loan_id = l.loan_id
                AND due_date > '{AS_OF_DATE}'
                AND status = 'Pending'),
                '{AS_OF_DATE}'
            ),
            9999
        ) AS days_to_next_due
    FROM loans l
    LEFT JOIN customers c ON c.customer_id = l.customer_id
    LEFT JOIN overdue_loans o ON o.loan_id = l.loan_id
    WHERE l.approval_date >= '{AS_OF_DATE}'
    AND l.approval_date <  '{VAL_END}'
    GROUP BY l.loan_id;
    """
    conn = pymysql.connect(**DB_CFG)
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()