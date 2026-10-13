# LawCodex — Cuba (cu)

Cuban legislation as Markdown, from the **Gaceta Oficial de la República de Cuba**
(Ministerio de Justicia, https://www.gacetaoficial.gob.cu): the **Constitution (2019)**, the **laws**
(leyes of the Asamblea Nacional del Poder Popular) and the **decree-laws** (decretos-leyes of the
Consejo de Estado) catalogued by the Gaceta's norm database, each cut out of the Gaceta issue
(PDF) in which it was published.

Part of [LawCodex](https://github.com/LawCodex): one public repository per jurisdiction.

Retrieved: **2026-10-13**. Language: Spanish (`es`).

Status: **partial (Constitution, and the laws and decree-laws listed by the Gaceta's database)**

## What is covered

| Category | Directory | Files |
|---|---|---|
| Constitución de la República de Cuba (proclaimed 10 April 2019; G.O. No. 5 Extraordinaria) | `constitucion/` | 1 |
| Leyes (Asamblea Nacional del Poder Popular) | `leyes/` | 88 |
| Decretos-leyes (Consejo de Estado) | `decretos-leyes/` | 281 |

The Gaceta's advanced search lists 114 leyes and 395 decretos-leyes (2007 onwards for most; some older norms). For each norm, its record page gives the Gaceta
issue, the norm identifier (GOC-year-number-issue, printed in the Gaceta above each norm since
2017), summary, number and year, and the norms it amends / repeals and is amended / repealed by.
The text is the part of the issue PDF between the norm's identifier and the next norm's
identifier (for older issues without identifiers: from the issuer's "HAGO SABER" before the
"LEY No. N" / "DECRETO-LEY No. N" heading to the next one). `status` is `repealed` when the
record names a repealing norm, otherwise `in_force`; `amended_by` lists amending norms. Texts are
as published (original texts); some recent issues are official *"anotado y concordado"*
editions.

Of the 509 norms listed, 369 were converted; 14 records have no Gaceta issue linked, 21 issues
could not be downloaded or have no text, and for 105 the norm could not be located in the issue
text. The Constitution has no record in the database's search (and the site was intermittently
unreachable from our network at the end of the run): its text was cut from the Gaceta issue PDF
as captured by the Internet Archive (`archived_source`); a font artefact of that PDF (capital U
extracted as "u" inside upper-case words) was corrected.

## What is NOT covered

- Earlier constitutions (1976, 1940).
- Resolutions, decrees, instructions and other norms of the database (about 30,000 records).
- Norms whose record has no Gaceta issue linked, or whose text could not be located in the issue.
- Gacetas 1990–1995 (separate scanned collection).

## Source

Gaceta Oficial de la República de Cuba: advanced search (`POST /es/getdata`, type of norm),
norm record pages `/es/<norm-slug>`, issue pages `/es/gaceta-oficial-no-…` and their PDFs
(`/sites/default/files/goc-….pdf`). robots.txt sets `Crawl-delay: 10`, respected (one request
every 10 s).

## Copyright

Laws and decree-laws are official texts published in the Gaceta Oficial for general knowledge;
official legislative texts are not treated as protected works under Cuban copyright law
(Ley 154 de 2022, De los Derechos del Autor y del Artista Intérprete).

## Regenerate

```
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
RAW=/path/to/scratch .venv/bin/python scripts/cu_fetch.py all
```
