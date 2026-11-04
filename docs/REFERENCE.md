# Functional references

Blind Pew is an independent implementation of the input behavior documented
by these Translit.ru pages:

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

[data/profiles.json](../data/profiles.json) contains the character
correspondences, reference dates and SHA-256 hashes of the reference pages.
No website JavaScript, HTML, logos or images are distributed with Blind Pew.
The project is not an official Translit.ru product.

The GNOME integration is independently written against GNOME Shell's
input-source API. GNOME source code is not copied.
Interface catalogs are independently authored. System-language selection
follows the behavior of Malferma Libro; its source and catalogs are not bundled.

To refresh tables from locally saved reference pages:

~~~sh
python3 tools/import_reference.py /path/to/reference-pages
python3 -m unittest discover -s tests -v
~~~

The importer reads the eight known profile filenames as data without
executing JavaScript. Review table changes and rerun desktop input checks
before distributing a package.

