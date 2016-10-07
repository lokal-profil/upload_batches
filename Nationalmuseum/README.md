This batch is for paintings in the National museum where the corresponding
data had already been used to create Wikidata items.

* `pre_process.py` is used to convert the [~5,000 .xml files](https://github.com/NationalmuseumSWE/WikidataCollection)
  into a single .json file for later re-use. Note that each painting has been
  depicted multiple times (with distinct photographer attribution) but we were
  only supplied by a single image. Hence a later step is needed to determine
  which filename to use.

* `make_Natmus_info.py` is used to create the Wikimedia Commons description
  pages associated with each image along with the filename to use on Commons.

* `local_nsid_mappings.json` is a mapping of non-artist National museum ids (NSID)
  to Wikidata entries. These were isolated and manually confirmed from the log
  file produced by `make_Natmus_info`. After this `make_Natmus_info` was re-run
  to make use of the new info.
