# Graphs (`lib/graph.imo`)

Twenty-two functions on graphs: construction, searching, paths, components, ordering, bipartiteness, Dijkstra and Kruskal.  Written in the human notation
(`libsrc/graph.hum.imo`, class-checked like any program) and translated into spec notation by `libsrc/build.sh`.

## Conventions

* A **graph** is a dictionary (`lib/dict.imo`) from vertices to the lists of their neighbours, `Dict(List(\Z))`: the neighbours are in the order in which the edges were given.
  A vertex is any Gaussian integer (an integer in practice).  `digraph(vs, es)` builds a directed graph from a vertex list and an edge list of pairs, `ugraph(vs, es)` an undirected
  one (each edge both ways; a loop once).  Vertices in `vs` without edges are kept; the endpoints of an edge need not be in `vs`.
* A **weighted graph** is `Dict(List(Pair(\Z, \QQ)))`: a vertex maps to its (neighbour, weight) pairs; `wdigraph(vs, es)` and `wugraph(vs, es)` take weighted edges `pair(u, pair(v, w))`.
* The order of `vertices(g)`, `edges(g)` and of `components(g)` is the trie order of the keys of the dictionary (its least significant base-(i − 1) digit first), not numeric order:
  a program that needs a numeric order sorts the result.  The order of `bfs`, `dfs` and of paths depends only on the order of the neighbour lists.

## What is there

| group | functions |
|:--|:--|
| building and looking | `digraph ugraph neighbors vertices degree edges reversed wdigraph wugraph` |
| searching | `bfs dfs reachable` (the vertices reachable from s, in the order of first reaching / of the depth-first preorder) |
| distances and paths | `distances` (numbers of edges, a dictionary) `shortestpath` (a list of at most one path, fewest edges) `dijkstra` (non-negative weights; a dictionary of distances) |
| structure | `components isconnected isbipartite` (undirected) `toposort isacyclic` (directed: Kahn's algorithm; a cycle leaves its vertices out of the order) |
| spanning forests | `kruskal` (edges in the order of their weights, a stable sort) `mstweight` |

## Tests

`tests/test_graph.py` (444 checks): the same algorithms written in Python, on random directed and undirected graphs (loops and repeated edges included): the orders of `bfs` and
`dfs`, distances, shortest paths, sizes of components, bipartiteness, acyclicity and the number of vertices a topological sort reaches, topological orders of random DAGs
(every edge goes forward), Dijkstra with integer and half-integer weights against `heapq`, Kruskal against a sorted union-find.
