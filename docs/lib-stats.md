# Statistics (`lib/stats.imo`)

Sixteen functions of descriptive statistics on lists of rational numbers, every result an exact rational.  Written in the human notation (`libsrc/stats.hum.imo`) and translated
into spec notation by `libsrc/build.sh`.  There is no square root in them: the variance is given, not the standard deviation, and the correlation as its square.

| group | functions |
|:--|:--|
| centre | `total average median modes` (`modes` returns every value of the greatest multiplicity, in increasing order) |
| spread | `spread` (maximum − minimum) `variance` (population) `svariance` (sample, n − 1) `quantile(p, xs)` (linear interpolation between order statistics, p between 0 and 1) `iqr` |
| two samples | `covariance` (population; the shorter list decides) `correlation2` (Pearson's r², 0 when a variance is 0) `linreg(xs, ys)` = `pair(slope, intercept)` of the least-squares line |
| running | `cumsum movingavg(k, xs)` (the averages of k consecutive values) `weightedmean(ws, xs)` |
| ranks | `ranks` (ties get the mean of their positions, as in the Spearman and Wilcoxon statistics) |

The empty list gives 0 wherever a number is expected.  `tally` of `lib/lists.imo` gives the frequencies, and `mean`, `sumsq`, `dotl` of that module are there as well.

## Tests

`tests/test_stats.py` (640 checks): every function against Python's `fractions` and `statistics` on random lists of rationals with small denominators (negative values, ties,
repeated values, empty and one-element lists included).
