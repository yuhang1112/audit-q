# generate_html.py
import networkx as nx
import matplotlib.pyplot as plt

def generate_html_2d(G, risk_clusters):
    pos = nx.spring_layout(G)  # 为图计算布局
    colors = ['lightblue' if node not in risk_clusters else 'red' for node in G.nodes()]
    edges_to_highlight = [(i, j) for i, j in G.edges() if i in risk_clusters or j in risk_clusters]
    nx.draw(G, pos, with_labels=True, node_color=colors, edge_color='gray')
    nx.draw_networkx_edges(G, pos, edgelist=edges_to_highlight, edge_color='red')
    plt.savefig('graph.png')
    
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
    with open('/static/graph.html', 'w') as f:
        f.write(html_content)
    return 'graph.html'