# Programs of the conformance cases

* `sNNN/` — the programs a Python test-suite loaded (recorded by wrapping `Program.add_text` while the suites ran; duplicates removed), in the order the suite added them. Each directory is one program in one or more files; the cases run `check`, `translate --to spec`, `translate --to bin` and `run` on all of its files together.
* `lib/` — the library sweep: one-line programs `main in <class> := name(arguments)`, written by `pymo/mkconformance.py`.

| directory | recorded from | files |
|:--|:--|:--|
| `s001` | `tests/test_codec.py` | `p1.hum.imo` |
| `s002` | `tests/test_codec.py` | `p1.hum.imo` |
| `s003` | `tests/test_codec.py` | `p1.hum.imo` |
| `s004` | `tests/test_codec.py` | `p1.hum.imo` |
| `s005` | `tests/test_codec.py` | `p1.hum.imo` |
| `s006` | `tests/test_layers.py` | `p1.imo` |
| `s007` | `tests/test_layers.py` | `p1.hum.imo` |
| `s008` | `tests/test_layers.py` | `p1.hum.imo` |
| `s009` | `tests/test_library.py` | `p1.hum.imo` |
| `s010` | `tests/test_output.py` | `p1.hum.imo` |
| `s011` | `tests/test_output.py` | `p1.imo` |
| `s012` | `tests/test_output.py` | `p1.hum.imo` |
| `s013` | `tests/test_output.py` | `p1.hum.imo` |
| `s014` | `tests/test_output.py` | `p1.imo` |
| `s015` | `tests/test_output.py` | `p1.imo`, `p2.hum.imo` |
| `s016` | `tests/test_output.py` | `p1.hum.imo` |
| `s017` | `tests/test_output.py` | `p1.imo` |
| `s018` | `tests/test_output.py` | `p1.imo`, `p2.hum.imo` |
| `s019` | `tests/test_output.py` | `p1.hum.imo` |
| `s020` | `tests/test_output.py` | `p1.imo` |
| `s021` | `tests/test_output.py` | `p1.hum.imo`, `p2.hum.imo` |
| `s022` | `tests/test_output.py` | `p1.imo`, `p2.imo` |
| `s023` | `tests/test_output.py` | `p1.hum.imo`, `p2.hum.imo`, `p3.imo`, `p4.imo`, `p5.hum.imo`, `p6.hum.imo` |
| `s024` | `tests/test_output.py` | `p1.imo` |
| `s025` | `tests/test_output.py` | `p1.hum.imo`, `p2.hum.imo` |
| `s026` | `tests/test_output.py` | `p1.imo` |
| `s027` | `tests/test_output.py` | `p1.imo` |
| `s028` | `tests/test_output.py` | `p1.hum.imo`, `p2.hum.imo` |
| `s029` | `tests/test_output.py` | `p1.imo`, `p2.imo`, `p3.hum.imo`, `p4.hum.imo` |
| `s030` | `tests/test_output.py` | `p1.imo`, `p2.hum.imo` |
| `s031` | `tests/test_output.py` | `p1.imo`, `p2.hum.imo` |
| `s032` | `tests/test_output.py` | `p1.hum.imo`, `p2.hum.imo` |
| `s033` | `tests/test_output.py` | `p1.imo` |
| `s034` | `tests/test_output.py` | `p1.imo`, `p2.hum.imo`, `p3.hum.imo` |
| `s035` | `tests/test_output.py` | `p1.imo` |
| `s036` | `tests/test_output.py` | `p1.imo` |
| `s037` | `tests/test_output.py` | `p1.hum.imo` |
| `s038` | `tests/test_output.py` | `p1.hum.imo` |
| `s039` | `tests/test_output.py` | `p1.imo`, `p2.imo` |
| `s040` | `tests/test_output.py` | `p1.hum.imo`, `p2.hum.imo` |
| `s041` | `tests/test_output.py` | `p1.imo` |
| `s042` | `tests/test_output.py` | `p1.hum.imo` |
| `s043` | `tests/test_output.py` | `p1.hum.imo` |
| `s044` | `tests/test_output.py` | `p1.imo`, `p2.imo` |
| `s045` | `tests/test_output.py` | `p1.hum.imo`, `p2.hum.imo` |
| `s046` | `tests/test_output.py` | `p1.imo` |
| `s047` | `tests/test_output.py` | `p1.hum.imo` |
| `s048` | `tests/test_output.py` | `p1.hum.imo` |
| `s049` | `tests/test_output.py` | `p1.hum.imo` |
| `s050` | `tests/test_output.py` | `p1.hum.imo` |
| `s051` | `tests/test_output.py` | `p1.hum.imo` |
| `s052` | `tests/test_output.py` | `p1.hum.imo` |
| `s053` | `tests/test_output.py` | `p1.imo` |
| `s054` | `tests/test_output.py` | `p1.hum.imo` |
| `s055` | `tests/test_output.py` | `p1.hum.imo` |
| `s056` | `tests/test_output.py` | `p1.hum.imo` |
| `s057` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s058` | `tests/test_predicates.py` | `p1.imo` |
| `s059` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s060` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s061` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s062` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s063` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s064` | `tests/test_predicates.py` | `p1.imo` |
| `s065` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s066` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s067` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s068` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo`, `p4.imo`, `p5.hum.imo`, `p6.imo` |
| `s069` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s070` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo` |
| `s071` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s072` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo` |
| `s073` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s074` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo` |
| `s075` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s076` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo` |
| `s077` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo`, `p4.hum.imo` |
| `s078` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo` |
| `s079` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s080` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo` |
| `s081` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo`, `p4.hum.imo`, `p5.imo`, `p6.hum.imo`, `p7.imo`, `p8.hum.imo` |
| `s082` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s083` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo` |
| `s084` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s085` | `tests/test_predicates.py` | `p1.imo`, `p2.hum.imo`, `p3.imo` |
| `s086` | `tests/test_predicates.py` | `p1.hum.imo` |
| `s087` | `tests/test_predicates.py` | `p1.hum.imo`, `p2.imo` |
| `s088` | `tests/test_predicates.py` | `p1.hum.imo`, `p2.imo` |
| `s089` | `tests/test_predicates.py` | `p1.hum.imo`, `p2.imo` |
| `s090` | `tests/test_predicates.py` | `p1.hum.imo`, `p2.imo` |
| `s091` | `tests/test_predicates.py` | `p1.hum.imo`, `p2.imo` |
| `s092` | `tests/test_predicates.py` | `p1.hum.imo`, `p2.imo` |
| `s093` | `tests/test_predicates.py` | `p1.hum.imo`, `p2.imo` |
| `s094` | `tests/test_predicates.py` | `p1.hum.imo`, `p2.imo` |
| `s095` | `tests/test_predicates.py` | `p1.imo` |
| `s096` | `tests/test_prove.py` | `p1.hum.imo` |
| `s097` | `tests/test_prove.py` | `p1.hum.imo` |
| `s098` | `tests/test_prove.py` | `p1.hum.imo` |
| `s099` | `tests/test_solve.py` | `p1.hum.imo` |
| `s100` | `tests/test_solve.py` | `p1.hum.imo`, `p2.hum.imo` |
| `s101` | `tests/test_solve.py` | `p1.hum.imo` |
| `s102` | `tests/test_solve.py` | `p1.hum.imo` |
| `s103` | `tests/test_solve.py` | `p1.hum.imo` |
| `s104` | `tests/test_solve.py` | `p1.hum.imo`, `p2.hum.imo` |
| `s105` | `tests/test_solve.py` | `p1.hum.imo` |
| `s106` | `tests/test_solve.py` | `p1.hum.imo` |
| `s107` | `tests/test_solve.py` | `p1.hum.imo`, `p2.hum.imo` |
