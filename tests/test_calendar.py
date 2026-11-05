"""test_calendar.py -- lib/calendar.imo (libsrc/calendar.hum.imo) against Python's datetime: leap years, month lengths, day numbers (date.toordinal), the inverse,
weekdays, differences, the ISO calendar, Easter (an independent Python implementation and known dates), names, ISO date strings.
python3 tests/test_calendar.py [--core pymo|haskimo|rustimo|compimo|ocamimo|schimo|cimo]"""
import calendar as pycal, datetime, random, sys
from langtest import *

R = random.Random(20261105)
S = Suite('the Gregorian calendar')
add = S.add
TRI = ('P', 'Z', ('P', 'Z', 'Z'))
SMALL = CORE == 'pymo'
def n(k): return max(2, k // 6) if SMALL else k

def rdate():
    y = R.choice([R.randint(1, 3000), R.randint(1900, 2100), R.randint(1, 400)])
    m = R.randint(1, 12)
    return datetime.date(y, m, R.randint(1, pycal.monthrange(y, m)[1]))
def tri(d): return (d.year, (d.month, d.day))

for _ in range(n(24)):
    d = rdate(); y = d.year
    add(f'isleap {y}', f'isleap({y})', 'B', pycal.isleap(y))
    add(f'yearlen {y}', f'yearlen({y})', 'Z', 366 if pycal.isleap(y) else 365)
    add(f'monthlen {y} {d.month}', f'monthlen({y}, {d.month})', 'Z', pycal.monthrange(y, d.month)[1])
    add(f'daysbefore {y} {d.month}', f'daysbefore({y}, {d.month})', 'Z', (datetime.date(y, d.month, 1) - datetime.date(y, 1, 1)).days)
    add(f'dayofyear {d}', f'dayofyear({y}, {d.month}, {d.day})', 'Z', d.timetuple().tm_yday)
    add(f'daynumber {d}', f'daynumber({y}, {d.month}, {d.day})', 'Z', d.toordinal())
    add(f'fromdaynumber {d.toordinal()}', f'fromdaynumber({d.toordinal()})', TRI, tri(d))
    add(f'weekday {d}', f'weekdayof({y}, {d.month}, {d.day})', 'Z', d.weekday())
    add(f'weekday of the day number {d.toordinal()}', f'weekday({d.toordinal()})', 'Z', d.weekday())
    iso = d.isocalendar()
    add(f'isoyear {d}', f'isoyear({d.toordinal()})', 'Z', iso[0])
    add(f'isoweek {d}', f'isoweek({d.toordinal()})', 'Z', iso[1])
    e = rdate(); k = R.randint(-4000, 4000)
    add(f'datediff {d} {e}', f'datediff({d.year}, {d.month}, {d.day}, {e.year}, {e.month}, {e.day})', 'Z', (e - d).days)
    try:
        t = d + datetime.timedelta(days=k)
        add(f'adddays {d} {k}', f'adddays({y}, {d.month}, {d.day}, {k})', TRI, tri(t))
    except OverflowError: pass
    add(f'isodate {d}', f'isodate({y}, {d.month}, {d.day})', 'S', d.isoformat())
    add(f'parseisodate {d}', f'parseisodate("{d.isoformat()}")', ('L', TRI), [tri(d)])
    add(f'monthname {d.month}', f'monthname({d.month})', 'S', pycal.month_name[d.month])
    add(f'dayname {d.weekday()}', f'dayname({d.weekday()})', 'S', pycal.day_name[d.weekday()])

# the first and last days of the 400-year cycles and of every century, where the formulas are tight
for y in [1, 4, 100, 399, 400, 401, 1600, 1700, 1800, 1900, 2000, 2100, 2400, 2800, 3200, 9999]:
    for (m, dd) in [(1, 1), (2, 28), (3, 1), (12, 31)]:
        d = datetime.date(y, m, dd)
        add(f'daynumber {d}', f'daynumber({y}, {m}, {dd})', 'Z', d.toordinal())
        add(f'fromdaynumber {d.toordinal()}', f'fromdaynumber({d.toordinal()})', TRI, tri(d))
for y in [4, 100, 400, 1600, 1900, 2000, 2024]:
    d = datetime.date(y, 2, 28) + datetime.timedelta(days=1)
    add(f'adddays Feb 28 {y} + 1', f'adddays({y}, 2, 28, 1)', TRI, tri(d))

# invalid dates and strings
for (y, m, dd) in [(2023, 2, 29), (2024, 2, 30), (2024, 4, 31), (2024, 13, 1), (2024, 0, 5), (0, 1, 1), (2024, 6, 0)]:
    add(f'isvalid {y}-{m}-{dd}', f'isvalid({y}, {m}, {dd})', 'B', y >= 1 and 1 <= m <= 12 and 1 <= dd <= (pycal.monthrange(y, m)[1] if 1 <= m <= 12 and y >= 1 else 0))
for text in ['2023-02-29', '2024-13-01', '2024-1', 'abcd-ef-gh', '', '2024-02-29-01', '2024--01-01']:
    add(f'parseisodate {text!r}', f'parseisodate("{text}")', ('L', TRI), [(2024, (2, 29))] if text == '2024-02-29' else [])

# Easter: known dates, and an independent implementation (the algorithm of Gauss, with its two exceptions) for every year of a range
KNOWN = {1961: (4, 2), 1972: (4, 2), 1985: (4, 7), 2000: (4, 23), 2008: (3, 23), 2016: (3, 27), 2019: (4, 21), 2024: (3, 31), 2025: (4, 20), 2038: (4, 25), 2285: (3, 22)}
for y, md in KNOWN.items(): add(f'easter {y}', f'easter({y})', ('P', 'Z', 'Z'), md)
def easter_gauss(y):
    a, b, c = y % 19, y % 4, y % 7
    k = y // 100; p = (13 + 8 * k) // 25; q = k // 4
    M = (15 - p + k - q) % 30; N = (4 + k - q) % 7
    d = (19 * a + M) % 30; e = (2 * b + 4 * c + 6 * d + N) % 7
    day = 22 + d + e
    if day > 31: month, day = 4, day - 31
    else: month = 3
    if month == 4 and day == 26: day = 19
    elif month == 4 and day == 25 and d == 28 and e == 6 and a > 10: day = 18
    return (month, day)
for _ in range(n(60)):
    y = R.randint(1583, 4099)
    add(f'easter {y}', f'easter({y})', ('P', 'Z', 'Z'), easter_gauss(y))

if __name__ == '__main__': sys.exit(0 if report(S) else 1)
