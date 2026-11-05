"""test_graph.py -- lib/graph.imo (libsrc/graph.hum.imo) against Python implementations of the same algorithms on random graphs: construction, breadth- and depth-first search,
reachability, components, distances, shortest paths, topological order, bipartiteness, Dijkstra, Kruskal.
python3 tests/test_graph.py [--core pymo|haskimo|rustimo|compimo|ocamimo|schimo|cimo]"""
import heapq, random, sys
from collections import deque
from fractions import Fraction as F
from langtest import *

R = random.Random(20261106)
SMALL = CORE == 'pymo'
def n(k): return max(2, k // 6) if SMALL else k
S = Suite('graphs')
add = S.add
LZ = ('L', 'Z'); EZ = ('P', 'Z', 'Z'); LE = ('L', EZ); WE = ('P', 'Z', ('P', 'Z', 'Q')); LW = ('L', WE)

def rgraph(directed, nmax=7):
    nv = R.randint(1, nmax)
    vs = R.sample(range(0, 12), nv)
    es = [(R.choice(vs), R.choice(vs)) for _ in range(R.randint(0, 2 * nv))]
    return vs, es
def adjacency(vs, es, directed):
    adj = {v: [] for v in vs}
    for (u, v) in es:
        adj[u].append(v)
        if not directed and u != v: adj[v].append(u)
    return adj
def gexpr(vs, es, directed): return f'{"digraph" if directed else "ugraph"}({lit(vs, LZ)}, {lit(es, LE)})'
def py_bfs(adj, s):
    seen, order, q = {s}, [], deque([s])
    while q:
        v = q.popleft(); order.append(v)
        for w in adj[v]:
            if w not in seen: seen.add(w); q.append(w)
    return order
def py_dfs(adj, s):
    seen, order, stack = set(), [], [s]
    while stack:
        v = stack.pop(0)
        if v in seen: continue
        seen.add(v); order.append(v); stack = adj[v] + stack
    return order
def py_dist(adj, s):
    d, q = {s: 0}, deque([s])
    while q:
        v = q.popleft()
        for w in adj[v]:
            if w not in d: d[w] = d[v] + 1; q.append(w)
    return d
def py_path(adj, s, t):
    par, q = {s: s}, deque([s])
    while q:
        v = q.popleft()
        for w in adj[v]:
            if w not in par: par[w] = v; q.append(w)
    if t not in par: return []
    path = [t]
    while path[-1] != s: path.append(par[path[-1]])
    return [path[::-1]]
def py_components(adj):
    seen, comps = set(), []
    for v in adj:
        if v not in seen:
            c = py_bfs(adj, v); seen.update(c); comps.append(c)
    return comps
def py_kahn_count(adj):
    indeg = {v: 0 for v in adj}
    for v in adj:
        for w in adj[v]: indeg[w] += 1
    q = deque(v for v in adj if indeg[v] == 0); k = 0
    while q:
        v = q.popleft(); k += 1
        for w in adj[v]:
            indeg[w] -= 1
            if indeg[w] == 0: q.append(w)
    return k
def py_bipartite(adj):
    color = {}
    for r in adj:
        if r in color: continue
        color[r] = 0; q = deque([r])
        while q:
            v = q.popleft()
            for w in adj[v]:
                if w not in color: color[w] = 1 - color[v]; q.append(w)
                elif color[w] == color[v]: return False
    return True

for t in range(n(14)):
    for directed in (True, False):
        vs, es = rgraph(directed)
        adj = adjacency(vs, es, directed); g = gexpr(vs, es, directed); tag = f'{"di" if directed else "u"}graph {vs} {es}'
        s = R.choice(vs); u = R.choice(vs)
        add(f'bfs {s} {tag}', f'bfs({g}, {s})', LZ, py_bfs(adj, s))
        add(f'dfs {s} {tag}', f'dfs({g}, {s})', LZ, py_dfs(adj, s))
        add(f'reachable {s} {u} {tag}', f'reachable({g}, {s}, {u})', 'B', u in py_bfs(adj, s))
        d = py_dist(adj, s)
        add(f'distances {s} {tag}', f'map((v in \\Z |-> dgetd(v, -1, distances({g}, {s}))), {lit(vs, LZ)})', LZ, [d.get(v, -1) for v in vs])
        add(f'shortestpath {s} {u} {tag}', f'shortestpath({g}, {s}, {u})', ('L', LZ), py_path(adj, s, u))
        add(f'degree {s} {tag}', f'degree({g}, {s})', 'N', len(adj[s]))
        add(f'number of vertices {tag}', f'length(vertices({g}))', 'N', len(vs))
        add(f'number of edges {tag}', f'length(edges({g}))', 'N', sum(len(a) for a in adj.values()))
        add(f'reversed {tag}', f'length(edges(reversed({g})))', 'N', sum(len(a) for a in adj.values()))
        add(f'reachable in the reversed graph {s} {u} {tag}', f'reachable(reversed({g}), {s}, {u})', 'B', u in py_bfs(adjacency(vs, [(b, a) for (a, b) in es], directed), s) if directed else u in py_bfs(adj, s))
        if not directed:
            comps = py_components(adj)
            add(f'components {tag}', f'sort(map(length, components({g})))', ('L', 'N'), sorted(len(c) for c in comps))
            add(f'number of components {tag}', f'length(components({g}))', 'N', len(comps))
            add(f'isconnected {tag}', f'isconnected({g})', 'B', len(comps) <= 1)
            add(f'isbipartite {tag}', f'isbipartite({g})', 'B', py_bipartite(adj))
        else:
            add(f'isacyclic {tag}', f'isacyclic({g})', 'B', py_kahn_count(adj) == len(vs))
            add(f'toposort length {tag}', f'length(toposort({g}))', 'N', py_kahn_count(adj))

# topological orders of random DAGs: the order is a permutation and every edge goes forward
for t in range(n(8)):
    nv = R.randint(1, 7); vs = list(range(nv)); perm = vs[:]; R.shuffle(perm)
    es = [(perm[a], perm[b]) for a in range(nv) for b in range(a + 1, nv) if R.random() < 0.35]
    R.shuffle(es)
    g = gexpr(vs, es, True)
    pos = lambda x: f'head(findindex((x in \\Z |-> x == {x}), toposort({g})))'
    add(f'toposort of a DAG {vs} {es}: length', f'length(toposort({g}))', 'N', nv)
    add(f'toposort of a DAG {vs} {es}: edges go forward', f'forall((e in Pair(\\Z, \\Z) |-> head(findindex((x in \\Z |-> x == fst(e)), toposort({g}))) lt head(findindex((x in \\Z |-> x == snd(e)), toposort({g})))), {lit(es, LE)})', 'B', True)
    add(f'isacyclic of a DAG {es}', f'isacyclic({g})', 'B', True)

# weighted graphs: Dijkstra and Kruskal
def rweighted(nmax=7):
    nv = R.randint(2, nmax); vs = R.sample(range(0, 12), nv)
    es = [(R.choice(vs), R.choice(vs), F(R.randint(0, 9)) if R.random() < 0.7 else F(R.randint(1, 9), 2)) for _ in range(R.randint(1, 2 * nv))]
    return vs, es
def py_dijkstra(vs, es, s, directed):
    adj = {v: [] for v in vs}
    for (a, b, w) in es:
        adj[a].append((b, w))
        if not directed and a != b: adj[b].append((a, w))
    dist, h = {}, [(F(0), 0, s)]; cnt = 1
    while h:
        d, _, v = heapq.heappop(h)
        if v in dist: continue
        dist[v] = d
        for (w, c) in adj[v]:
            if w not in dist: heapq.heappush(h, (d + c, cnt, w)); cnt += 1
    return dist
def py_kruskal(es):
    par = {}
    def find(x):
        while par.get(x, x) != x: x = par[x]
        return x
    out = []
    for e in sorted(es, key=lambda e: e[2]):
        a, b = find(e[0]), find(e[1])
        if a != b: par[a] = b; out.append(e)
    return out
for t in range(n(14)):
    vs, es = rweighted(); s = R.choice(vs)
    wes = [(a, (b, w)) for (a, b, w) in es]
    for directed in (True, False):
        g = f'{"wdigraph" if directed else "wugraph"}({lit(vs, LZ)}, {lit(wes, LW)})'
        d = py_dijkstra(vs, es, s, directed)
        add(f'dijkstra {s} {"di" if directed else "u"}graph {vs} {es}', f'map((v in \\Z |-> dgetd(v, -1, dijkstra({g}, {s}))), {lit(vs, LZ)})', ('L', 'Q'), [d.get(v, F(-1)) for v in vs])
    k = py_kruskal(es)
    add(f'kruskal {es}', f'kruskal({lit(wes, LW)})', LW, [(a, (b, w)) for (a, b, w) in k])
    add(f'mstweight {es}', f'mstweight({lit(wes, LW)})', 'Q', sum((e[2] for e in k), F(0)))

if __name__ == '__main__': sys.exit(0 if report(S) else 1)
