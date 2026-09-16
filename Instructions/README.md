# Instruction PDFs

Drop official LEGO instruction booklets here, one folder per set:

```
Instructions/
  UCS Venator/
    6482339.pdf
    6482341.pdf
    ...
  Another Set/
    booklet.pdf
```

Ingest walks this tree for `*.pdf` files. The parent folder name becomes the set display name.

PDFs are gitignored. Derived rasters and the search index live in `/data` (the Compose `data` volume), so you can delete these PDFs later without losing the index.
