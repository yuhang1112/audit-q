# generate_html.py
import os
import networkx as nx
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from fastapi.responses import FileResponse
from config import STATIC_DIR, REMOTE_ADDR
os.makedirs(STATIC_DIR, exist_ok=True)   # 确保目录存在

def generate_html_2d(G, risk_clusters):
    pos = nx.spring_layout(G)  # 为图计算布局
    colors = ['lightblue' if node not in risk_clusters else 'red' for node in G.nodes()]
    edges_to_highlight = [(i, j) for i, j in G.edges() if i in risk_clusters or j in risk_clusters]
    nx.draw(G, pos, with_labels=True, node_color=colors, edge_color='gray')
    nx.draw_networkx_edges(G, pos, edgelist=edges_to_highlight, edge_color='red')
    plt.savefig('/static/graph.png')
    plt.close()
    # 生成 HTML 文件
    html_content = """
    <html>
    <head><title>Graph Visualization</title>
    </head>
    <body>
    <img src="graph.png" alt="Graph Visualization">
    </body>
    </html>
    """
    local_path = os.path.join(STATIC_DIR, "graph.html")
    web_path = os.path.join(REMOTE_ADDR, "graph.html")
    with open(local_path, 'w') as f:
        f.write(html_content)
    return web_path

def generate_html_3d(G, risk_clusters):
    pos = nx.spring_layout(G, dim=3)

    # 边
    edge_x, edge_y, edge_z = [], [], []
    for u, v in G.edges():
        edge_x += [pos[u][0], pos[v][0], None]
        edge_y += [pos[u][1], pos[v][1], None]
        edge_z += [pos[u][2], pos[v][2], None]

    # 节点颜色
    node_color = ['red' if node in risk_clusters else 'blue' for node in G.nodes()]

    node_trace = go.Scatter3d(
        x=[pos[n][0] for n in G.nodes()],
        y=[pos[n][1] for n in G.nodes()],
        z=[pos[n][2] for n in G.nodes()],
        mode='markers',
        marker=dict(size=6, color=node_color),
        text=list(G.nodes()),
        hoverinfo='text'
    )

    edge_trace = go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode='lines',
        line=dict(color='black', width=2)
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    local_path = os.path.join(STATIC_DIR, "graph_3d.html")
    fig.write_html(local_path, include_plotlyjs='cdn', auto_open=False)
    web_path = os.path.join(REMOTE_ADDR, "graph_3d.html")
    return web_path