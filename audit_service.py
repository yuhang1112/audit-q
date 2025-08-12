# graph_service.py
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sklearn.semi_supervised import LabelSpreading
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from logger import get_logger
from generate_html import generate_html_2d, generate_html_3d
from sql import get_account_by_ids, get_overdue_dataset
from config import CACHE_DIR, STATIC_DIR, REMOTE_ADDR
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import lightgbm as lgb
import joblib
import os
import seaborn as sns

app = FastAPI()
# 把 /static 路径映射到本地 ./static 目录，浏览器可以通过/static访问静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
logger = get_logger(__name__)
class Payload(BaseModel):
    edges: list[dict]   # [{"id":..., "from_acct":..., "to_acct":..., "amount":..., "label":...}]

# 可以用/graph也可以用/static/graph.html访问生成的图
@app.get("/graph")
def read_root():
    return FileResponse("static/graph.html")

# 半监督图算法接口
@app.post("/semi")
def semi_graph(req: Payload):
    logger.info("半监督图算法程序已启动")

    # print("Received edges:", req.edges[0]["records"])
    df = pd.DataFrame(req.edges[0]["records"])
    # 建图
    G = nx.Graph()
    for _, r in df.iterrows():
        G.add_edge(int(r["from_acct"]), int(r["to_acct"]), weight=float(r["amount"]))

    # 已知标签
    known = df.drop_duplicates("id").set_index("id")["label"]
    # logger.info(f"已知标签: {known}")
    y = known.reindex(G.nodes(), fill_value=-1).values

    # 半监督
    adj = nx.adjacency_matrix(G, weight=None).astype(float)
    lp = LabelSpreading()
    lp.fit(adj, y)
    pred = lp.transduction_

    # 团伙
    clusters = {}
    for node, label in zip(G.nodes(), pred):
        clusters.setdefault(int(label), []).append(node)

    # 风险 label=1
    risk_clusters = {k: v for k, v in clusters.items() if k == 1}
    logger.info(f"风险团伙: {risk_clusters}")

    # 可视化
    web_path = generate_html_3d(G, risk_clusters)

    return {
        "risk_accounts": get_account_by_ids(sum(risk_clusters.values(), [])),
        "graph_url": web_path  # 返回生成的图的链接
    }

@app.post("/overdue")
def predict_overdue():
    df = get_overdue_dataset()
    logger.info(df)
    result = train_overdue_model(df, True)

    logger.info(f"模型训练完成，开始生成打分结果\n")
    csv_path = os.path.join(STATIC_DIR, 'overdue_scores.csv')
    result.to_csv(csv_path, index=False, encoding='utf-8-sig')
    logger.info(f"打分结果已保存到: {csv_path}")
    high_risk = result[result['prob'] > 0.7]
    img_url = draw_overdue_chart(result)
    # 构造返回
    return {
        "result": high_risk.to_dict(orient='records'),
        "csv_url": f"{REMOTE_ADDR}overdue_scores.csv",
        "img_url": img_url
    }

def train_overdue_model(df, use_cache=False):
    feature_cols = [
        'loan_amount', 'interest_rate', 'credit_score',
        'risk_level_num', 'customer_type_num',
        'days_since_approval', 'max_overdue_days', 'days_to_next_due'
    ]
    X = df[feature_cols].fillna(0)
    y = df['is_overdue_30']
    MODEL_PATH = os.path.join(CACHE_DIR, "overdue_model.pkl")
    # 1. 如果允许缓存且模型文件存在，直接加载
    if use_cache and os.path.exists(MODEL_PATH):
        logger.info("发现缓存模型，直接加载")
        model = joblib.load(MODEL_PATH)
    else:
        logger.info("缓存不存在或强制重新训练")
        # 1. 分层采样 + 训练/验证集
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y)

        # 2. 处理不平衡
        pos_rate = y.mean()          # ≈ 0.02
        logger.info(f"正样本比例: {pos_rate:.2%}")
        scale_pos_weight = (1 - pos_rate) / pos_rate

        # 3. 用原生接口，方便传 scale_pos_weight
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data   = lgb.Dataset(X_val,   label=y_val, reference=train_data)

        params = {
            'objective': 'binary',
            'metric': 'auc',
            'learning_rate': 0.05,
            'num_leaves': 32,
            'max_depth': 4,
            'min_data_in_leaf': 1,
            'scale_pos_weight': scale_pos_weight,
            'verbose': -1,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 1,
            'lambda_l2': 0.1
        }

        model = lgb.train(
            params,
            train_data,
            num_boost_round=1000,
            valid_sets=[train_data, val_data]
        )

        # 4. 保存
        joblib.dump(model, MODEL_PATH)

    # 5. 给整表打分
    df['prob'] = model.predict(X)
    return df[['loan_id', 'prob']]

# 绘图并返回 URL
def draw_overdue_chart(high_df: pd.DataFrame):
    """
    high_df 必须包含 loan_id, prob
    """
    if high_df.empty:
        return None

    save_dir = os.path.join(STATIC_DIR, "images")
    os.makedirs(save_dir, exist_ok=True)
    file_name = "overdue_high_risk.png"
    full_path = os.path.join(save_dir, file_name)

    plt.figure(figsize=(6, max(3, len(high_df) * 0.4)))   # 自适应高度
    sns.set_style("whitegrid")
    sns.barplot(
        x='prob',
        y='loan_id',
        data=high_df.sort_values('prob', ascending=False),
        palette='Reds_r'
    )
    plt.xlim(0, 1)
    plt.xlabel('30 天逾期概率')
    plt.title('高风险贷款 TOP')
    plt.tight_layout()
    plt.savefig(full_path, dpi=150, bbox_inches='tight')
    plt.close()

    return f"{REMOTE_ADDR}images/{file_name}"