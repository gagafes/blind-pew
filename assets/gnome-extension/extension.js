// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Andrey Popovich
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Keyboard from 'resource:///org/gnome/shell/ui/status/keyboard.js';

const IFACE = 'org.blindpew.Desktop';
const XML = `<node><interface name="${IFACE}">
<method name="GetState"><arg type="s" direction="out"/><arg type="s" direction="out"/></method>
<method name="Activate"><arg type="s" direction="in"/><arg type="s" direction="in"/><arg type="b" direction="out"/></method>
<signal name="StateChanged"><arg type="s"/><arg type="s"/></signal>
</interface></node>`;

export default class BlindPewExtension extends Extension {
    enable() {
        this._manager = Keyboard.getInputSourceManager();
        this._export = Gio.DBusExportedObject.wrapJSObject(XML, this);
        this._export.export(Gio.DBus.session, '/org/blindpew/Desktop');
        this._sourceSignal = this._manager.connect('current-source-changed', () => this._emit());
        this._emit();
    }

    GetState() {
        const source = this._manager.currentSource;
        return [source?.type || '', source?.id || ''];
    }

    Activate(type, id) {
        const source = Object.values(this._manager.inputSources).find(s => s.type === type && s.id === id);
        if (!source)
            return false;
        source.activate(true);
        return true;
    }

    _emit() {
        this._export?.emit_signal('StateChanged', new GLib.Variant('(ss)', this.GetState()));
    }

    disable() {
        if (this._sourceSignal)
            this._manager.disconnect(this._sourceSignal);
        this._export?.emit_signal('StateChanged', new GLib.Variant('(ss)', ['', '']));
        this._export?.unexport();
        this._export = null;
        this._manager = null;
        this._sourceSignal = 0;
    }
}
