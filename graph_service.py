# graph_service.py
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sklearn.semi_supervised import LabelSpreading
from logger import get_logger
from generate_html import generate_html_2d
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

app = FastAPI()
# 把 /static 路径映射到本地 ./static 目录
app.mount("/static", StaticFiles(directory="static"), name="static")

class Payload(BaseModel):
    edges: list[dict]   # [{"id":..., "from_acct":..., "to_acct":..., "amount":..., "label":...}]

# 半监督图算法接口
@app.post("/semi")
def semi_graph(req: Payload):
    logger = get_logger(__name__)
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
    html_path = generate_html_2d(G, risk_clusters)

    return {
        "risk_clusters": risk_clusters,
        "risk_accounts": sum(risk_clusters.values(), []),
        "graph_url": html_path  # 返回生成的图的链接
    }

@app.get("/graph")
def read_root():
    return FileResponse("static/graph.html")