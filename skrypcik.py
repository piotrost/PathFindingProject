import pickle as pkl

g = pkl.load(open('graph.pkl', 'rb'))

print(len(g.nodes.keys()))