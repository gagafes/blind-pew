# Functional references

Eight Blind Pew profiles implement the input behavior documented on these Translit.ru pages.

| Profile | Reference |
|---|---|
| Belarusian | https://translit.ru/be |
| Ukrainian | https://translit.ru/ua |
| Lithuanian | https://translit.ru/li |
| Georgian | https://translit.ru/ge |
| Armenian | https://translit.ru/am |
| Russian | https://translit.ru/ |
| Russian DE | https://translit.ru/rude |
| Hebrew | https://translit.ru/il |

[The profile data](../data/profiles.json) records the character mappings. For
each imported profile it records the reference URL, reference date and page
SHA-256.
The Arabic phonetic profile is maintained directly in the project. It combines
Latin digraphs with explicit dot-prefixed keys and is outside the Translit.ru
importer.

No website JavaScript, HTML, logos or images are distributed with Blind Pew.
The project is not an official Translit.ru product.

The GNOME integration is independently written against GNOME Shell's
input-source API. GNOME source code is not copied.
Interface catalogs are independently authored. System-language selection
follows the behavior of Malferma Libro; its source and catalogs are not bundled.

From the source checkout, refresh tables from locally saved reference pages:

~~~sh
python3 tools/import_reference.py /path/to/reference-pages
python3 -m unittest discover -s tests -v
~~~

The importer reads the eight known profile filenames as data without
executing JavaScript. Review table changes and rerun desktop input checks
before distributing a package.

The importer extracts functional mapping data. No separate redistribution grant
for those tables is recorded here; references and page hashes are provenance,
not a license. See [licensing notices](../THIRD_PARTY_NOTICES.md) and the
[review scope](LEGAL_REVIEW.md).
