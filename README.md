## About this repo
This repo is a collection of various individual batch uploads based on
[lokal-profil/BatchUploadTools](https://github.com/lokal-profil/BatchUploadTools).

To run it you will have to install `BatchUploadTools` using:
`pip install git+https://github.com/lokal-profil/BatchUploadTools.git`

*Note*: You might have to add the `--process-dependency-links` flag to the above
command if you are running a different version of pywikibot from the required one.

These projects are mainly here for my own use and to illustrate how
BatchUploadTools can be used. There is no guarantee that any of them will work
with versions of BatchUploadTools later than that given in the
`requirements.txt` in each directory.

As such they may also include implicit assumptions about the indata, hard-coded
mappings or insufficient documentation. There may also be nonsensical comments
and todo's left in the code and the commit messages probably won't make much
sense either. And don't expect any tests or similar sensible and useful
precautions.

## Projects
* **`Nationalmuseum`**: A batch upload of paintings from Nationalmuseum
  (Stockholm). Metadata was delivered in .xml files and most of the paintings
  already had items on Wikidata thanks to an earlier data import.
* **`SMM-images`**: A batch upload of images from the National Maritime Museums 
  of Sweden. Metadata was delivered as a .csv file and connected to objects in
  KulturNav.
* **`KMB`**: A batch upload of images from the National Heritage Board's
  *Kulturmiljöbild*. A list of image ids to upload was provided by the
  organisation and the metadata for these was pre-fetched using `kmb_massload.py`.
  The code is based heavily on pre-existing code in
  [lokal-profil/RAA-tools](https://github.com/lokal-profil/RAA-tools).
