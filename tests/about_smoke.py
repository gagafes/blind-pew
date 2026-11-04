"""About text follows the actual system locale, including compiled catalogs."""
import os
from unittest.mock import patch
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from blind_pew import __version__, config, i18n
from blind_pew.setup import AboutDialog, Application

config.update(ui_language='system')
before = dict(os.environ)
cases = [(code, code) for code, _ in i18n.LANGUAGES]
cases += [('unknown:uk_UA.UTF-8:de', 'uk'), ('iw_IL', 'he'),
          ('sr_RS@latin', 'sr_Latn'), ('unknown', 'en')]
for locale, expected in cases:
    with patch.dict(os.environ, {'LANGUAGE': locale, 'LC_ALL': 'C', 'LANG': 'C'}):
        app = Application()
        assert i18n.current() == expected
        dialog = AboutDialog(None)
        dialog.show_all()
        assert dialog.get_title() == i18n.tr('About')
        assert dialog.get_widget_for_response(Gtk.ResponseType.CLOSE).get_label() == i18n.tr('Close')
        labels = [widget.get_text() for widget in dialog.get_content_area().get_children()
                  if isinstance(widget, Gtk.Label)]
        assert i18n.tr('Version') + ': ' + __version__ in labels
        assert i18n.tr('License') + ': MIT' in labels
        assert i18n.tr('Transliteration') + ' · ' + i18n.tr('Offline') in labels
        assert any(i18n.tr('Ukrainian') in text and i18n.tr('Hebrew') in text for text in labels)
        assert dialog.get_direction() == (Gtk.TextDirection.RTL if expected in i18n.RTL else Gtk.TextDirection.LTR)
        dialog.destroy()
assert dict(os.environ) == before
print('PASS About: all 49 system languages, locale fallback/aliases, version, license, description, buttons and RTL')
