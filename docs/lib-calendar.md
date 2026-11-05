# The calendar (`lib/calendar.imo`)

The proleptic Gregorian calendar, in 19 functions.  Written in the human notation (`libsrc/calendar.hum.imo`, class-checked like any program) and translated into spec
notation by `libsrc/build.sh`, which is how `lib/calendar.imo` is made.  Everything is integer arithmetic (`div`, `mod`, `+ - *`), so a date is a few base-(i − 1) digit strings.

## Conventions

* A **date** is a triple *(year, month, day)*, written as nested pairs `pair(y, pair(m, d))`.  Years count from 1 (0001-01-01 is the first day).
* A **day number** is the ordinal of Python's `date.toordinal()`: day 1 is 0001-01-01, day 738 000 is in 2021.
* A **weekday** is 0 for Monday … 6 for Sunday, as Python's `date.weekday()`.

## What is there

| group | functions |
|:--|:--|
| years and months | `isleap yearlen monthlen daysbefore isvalid dayofyear` |
| day numbers | `daynumber fromdaynumber weekday weekdayof datediff adddays` |
| the ISO calendar | `isoyear isoweek` (of a day number: the year and week of the Thursday of its week) |
| Easter | `easter(y)` = `pair(month, day)` of Easter Sunday (the anonymous Gregorian algorithm of Meeus, Jones and Butcher) |
| text | `monthname dayname isodate parseisodate` (`isodate(2024, 2, 9)` = `"2024-02-09"`; `parseisodate` returns a list of at most one date, empty for a malformed or impossible one) |

`fromdaynumber` uses the cycles of the calendar (146 097 days in 400 years, 36 524 in a century, 1 461 in four years), so it does not search.

## Tests

`tests/test_calendar.py` (900 checks): every function against Python's `datetime` and `calendar` on random dates (years 1 to 3 000, the boundaries of the 400-year cycles,
century years), the ISO year and week against `isocalendar()`, differences and sums of dates, invalid dates and strings, and Easter against known dates and against an independent
implementation (the algorithm of Gauss with its two exceptions) for 60 random years between 1583 and 4099.
