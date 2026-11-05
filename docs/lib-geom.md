# Plane geometry (`lib/geom.imo`)

Twenty-seven functions of the Euclidean plane with exact rational coordinates.  Written in the human notation (`libsrc/geom.hum.imo`) and translated into spec notation by
`libsrc/build.sh`.  No square root is needed anywhere: lengths are squared (`dist2`), and a circle is its centre.

A **point** (or vector) is a pair `pair(x, y)` of rationals; a **polygon** is a list of points in order around it (the first is not repeated at the end).

| group | functions |
|:--|:--|
| vectors | `ptx pty vsub2 vadd2 vscale2 dotp crossp dist2 midpoint centroid bbox` |
| orientation | `cross3(o, a, b)` (twice the signed area of the triangle) `orient` (1, 0 or −1) `triarea2 iscollinear` |
| segments and lines | `onsegment segmentsintersect` (closed segments, touching included) `lineintersection` (a list of at most one point) `circumcenter` (a list of at most one point) |
| polygons | `polyarea2 polyarea signedarea2` (shoelace) `polyperimeter2` (squared side lengths) `inpolygon(p, poly)` = 1 inside, 0 on the boundary, −1 outside (even-odd rule) `isconvex` |
| point sets | `convexhull` (Andrew's monotone chain: counter-clockwise from the lowest-leftmost point, collinear points dropped, duplicates ignored) `closestpair2` |

## Tests

`tests/test_geom.py` (977 checks): every function against Python implementations written with `fractions` on random points with integer and half-integer coordinates, including
degenerate cases (equal points, collinear points, parallel lines, polygons that are not simple), the circumcentre by its defining property (equidistance), points on the boundary of a
square and of random convex hulls.
