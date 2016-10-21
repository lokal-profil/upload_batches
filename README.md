## About this repo
This repo is a collection of various individual batch uploads based on
[lokal-profil/BatchUploadTools](https://github.com/lokal-profil/BatchUploadTools).
It is expected that this repo is cloned into the `Batches` directory of a checked
out verion of that repo.

These projects are mainly here for my own use and to illustrate how BatchUploadTools
can be used. There is no guarantee that any of them will work at any given time
since I'm not keeping them in sync with any later changes to BatchUploadTools.

As such they may also include implicit assumptions about the indata, hard-coded
mappings or insufficient documentation. There may also be nonsensical comments
and todo's left in the code and the commit messages probably won't make much
sense either. And don't expect any tests or similar sensible and useful
precautions.

## Projects
* **`Nationalmuseum`**: A batch upload of paintings from Nationalmuseum
  (Stockholm). Metadata was delivered in xml files and most of the paintings
  already had items on Wikidata thanks to an earlier data import.
