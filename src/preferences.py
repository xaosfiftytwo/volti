# -*- coding: utf-8 -*-

# Author: Milan Nikolic <gen2brain@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import gtk
import gobject
import pango
from ConfigParser import ConfigParser

from alsactrl import AlsaControl

prefs = {
    "card_index": 0,
    "control": "Master",
    "mixer": "",
    "run_in_terminal": 0,
    "scale_increment": 1.0,
    "scale_show_value": 0,
    "show_tooltip": 1,
    "toggle": "mute",
    "keys": 0,
    "keys_backend": "hal",
    "show_notify": 0,
    "notify_timeout": 2.0
    }

_preferences = None

class Preferences:

    def __init__(self, MainInstance):
        self.main = MainInstance

        self.cp = ConfigParser()
        self.set_section()

        if not os.path.isfile(self.main.config.CONFIG_FILE):
            self.write_file()

        self.read_file()

        self.glade = os.path.join(self.main.config.RES_DIR, "preferences.glade")
        self.tree = gtk.Builder()
        self.tree.set_translation_domain(self.main.config.APP_NAME)
        self.tree.add_from_file(self.glade)

        self.window = self.tree.get_object("window")
        self.window.set_icon_name("multimedia-volume-control")
        self.window.connect("destroy", self.close)

        self.button_close = self.tree.get_object("button_close")
        self.button_close.connect("clicked", self.close)

        self.button_browse = self.tree.get_object("button_browse")
        self.button_browse.connect("clicked", self.on_browse_button_clicked)

        self.mixer_entry = self.tree.get_object("mixer_entry")
        self.mixer_entry.set_text(prefs["mixer"])
        self.mixer_entry.connect_after("changed", self.on_entry_changed)

        self.scale_spinbutton = self.tree.get_object("scale_spinbutton")
        self.scale_spinbutton.set_value(float(prefs["scale_increment"]))
        self.scale_spinbutton.connect("value_changed", self.on_scale_spinbutton_changed)

        self.tooltip_checkbutton = self.tree.get_object("tooltip_checkbutton")
        self.tooltip_checkbutton.set_active(bool(int(prefs["show_tooltip"])))
        self.tooltip_checkbutton.connect("toggled", self.on_tooltip_toggled)

        self.terminal_checkbutton = self.tree.get_object("terminal_checkbutton")
        self.terminal_checkbutton.set_active(bool(int(prefs["run_in_terminal"])))
        self.terminal_checkbutton.connect("toggled", self.on_terminal_toggled)

        self.draw_value_checkbutton = self.tree.get_object("draw_value_checkbutton")
        self.draw_value_checkbutton.set_active(bool(int(prefs["scale_show_value"])))
        self.draw_value_checkbutton.connect("toggled", self.on_draw_value_toggled)

        self.mute_radiobutton = self.tree.get_object("radiobutton_mute")
        self.mute_radiobutton.connect("toggled", self.on_radio_mute_toggled)
        self.mixer_radiobutton = self.tree.get_object("radiobutton_mixer")
        self.mixer_radiobutton.connect("toggled", self.on_radio_mixer_toggled)

        self.keys_checkbutton = self.tree.get_object("keys_checkbutton")
        self.keys_checkbutton.set_active(bool(int(prefs["keys"])))
        self.keys_checkbutton.connect("toggled", self.on_keys_toggled)

        self.hal_radiobutton = self.tree.get_object("radiobutton_hal")
        hal_handler_id = self.hal_radiobutton.connect("toggled", self.on_radio_hal_toggled)
        self.xlib_radiobutton = self.tree.get_object("radiobutton_xlib")
        xlib_handler_id = self.xlib_radiobutton.connect("toggled", self.on_radio_xlib_toggled)

        self.notify_checkbutton = self.tree.get_object("notify_checkbutton")
        notify_handler_id = self.notify_checkbutton.connect("toggled", self.on_notify_toggled)

        self.timeout_spinbutton = self.tree.get_object("timeout_spinbutton")
        self.timeout_spinbutton.set_value(float(prefs["notify_timeout"]))
        self.timeout_spinbutton.connect("value_changed", self.on_timeout_spinbutton_changed)

        if prefs["toggle"] == "mute":
            self.mute_radiobutton.set_active(True)
        elif prefs["toggle"] == "mixer":
            self.mixer_radiobutton.set_active(True)

        if prefs["keys_backend"] == "hal":
            self.hal_radiobutton.handler_block(hal_handler_id)
            self.hal_radiobutton.set_active(True)
            self.hal_radiobutton.handler_unblock(hal_handler_id)
        elif prefs["keys_backend"] == "xlib":
            self.xlib_radiobutton.handler_block(xlib_handler_id)
            self.xlib_radiobutton.set_active(True)
            self.xlib_radiobutton.handler_unblock(xlib_handler_id)

        self.notify_checkbutton.handler_block(notify_handler_id)
        self.notify_checkbutton.set_active(bool(int(prefs["show_notify"])))
        self.notify_checkbutton.handler_unblock(notify_handler_id)

        self.set_sensitive(bool(int(prefs["keys"])))

    def open(self, widget=None, data=None):
        global _preferences
        if _preferences is None:
            _preferences = Preferences(self.main)
            _preferences.init_combobox()
            _preferences.init_treeview()
            _preferences.window.show_all()
        else:
            _preferences.window.present()

    def close(self, widget=None):
        global _preferences
        self.write_file()
        if _preferences is not None:
            _preferences.window.destroy()
            _preferences = None

    def set_section(self):
        self.section = "card-%s" % prefs["card_index"]

    def init_combobox(self):
        icon_theme = gtk.icon_theme_get_default()
        icon = icon_theme.load_icon("audio-card", 18, flags=gtk.ICON_LOOKUP_FORCE_SVG)

        self.combo_model = gtk.ListStore(int, gtk.gdk.Pixbuf, str)
        cards = self.main.alsactrl.get_cards()
        for index in range(0, len(cards)):
            if cards[index] is not None:
                self.combo_model.append([index, icon, cards[index]])

        self.combobox = self.tree.get_object("combobox")
        self.combobox.set_model(self.combo_model)
        self.combobox.set_active(int(prefs["card_index"]))

        cell1 = gtk.CellRendererPixbuf()
        cell1.set_property("xalign", 0)
        cell1.set_property("xpad", 3)
        self.combobox.pack_start(cell1, False)
        self.combobox.add_attribute(cell1, "pixbuf", 1)

        cell2 = gtk.CellRendererText()
        cell2.set_property("xpad", 10)
        self.combobox.pack_start(cell2, True)
        self.combobox.set_attributes(cell2, text=2)

        self.combobox.connect("changed", self.on_combobox_changed)

    def init_treeview(self):
        self.liststore = gtk.ListStore(bool, str, int)
        for mixer in self.main.alsactrl.get_mixers():
            active = (mixer == prefs["control"])
            if active:
                self.liststore.append([active, mixer, pango.WEIGHT_BOLD])
            else:
                self.liststore.append([active, mixer, pango.WEIGHT_NORMAL])

        self.treeview = gtk.TreeView(self.liststore)
        self.treeview.set_headers_visible(False)

        cell1 = gtk.CellRendererToggle()
        cell1.set_radio(True)
        cell1.set_property("activatable", True)
        cell1.connect('toggled', self.on_treeview_toggled, self.liststore)
        column1 = gtk.TreeViewColumn()
        column1.pack_start(cell1, True)
        column1.add_attribute(cell1, 'active', 0)
        self.treeview.append_column(column1)

        cell2 = gtk.CellRendererText()
        column2 = gtk.TreeViewColumn()
        column2.pack_start(cell2, True)
        column2.add_attribute(cell2, 'text', 1)
        column2.add_attribute(cell2, 'weight', 2)
        self.treeview.append_column(column2)

        scrolledwindow = self.tree.get_object("scrolledwindow")
        scrolledwindow.add(self.treeview)

    def on_browse_button_clicked(self, widget=None):
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        dialog = gtk.FileChooserDialog(title=_("Choose external mixer"), action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=buttons)
        dialog.set_current_folder("/usr/bin")
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_show_hidden(False)

        file_filter_mixers=gtk.FileFilter()
        file_filter_mixers.set_name(_("Audio Mixers"))
        file_filter_mixers.add_custom(gtk.FILE_FILTER_FILENAME, self.custom_mixer_filter)
        file_filter_all=gtk.FileFilter()
        file_filter_all.set_name(_("All files"))
        file_filter_all.add_pattern("*")
        dialog.add_filter(file_filter_mixers)
        dialog.add_filter(file_filter_all)

        response = dialog.run()
        filename = dialog.get_filename()
        dialog.destroy()

        while gtk.events_pending():
            gtk.main_iteration(False)

        if response == gtk.RESPONSE_OK:
            self.mixer_entry.set_text(filename)
            prefs["mixer"] = filename
            return filename
        elif response == gtk.RESPONSE_CANCEL:
            return None

    def custom_mixer_filter(self, filter_info=None, data=None):
        mixers = ["aumix", "alsamixer", "alsamixergui", "gamix", "gmixer", "gnome-alsamixer", "gnome-volume-control"]
        if filter_info[2] in mixers:
            if filter_info[3] == "application/x-executable":
                return True
        return False

    def on_combobox_changed(self, widget=None):
        model = widget.get_model()
        iter = widget.get_active_iter()
        card_index = model.get_value(iter, 0)
        prefs["card_index"] = card_index
        self.set_section()
        if self.cp.has_section(self.section):
            prefs["control"] = self.cp.get(self.section, "control").strip()
        else:
            prefs["control"] = self.main.alsactrl.get_mixers()[0]

        self.main.update()
        self.liststore.clear()

        for mixer in self.main.alsactrl.get_mixers():
            active = (mixer == prefs["control"])
            if active:
                self.liststore.append([active, mixer, pango.WEIGHT_BOLD])
            else:
                self.liststore.append([active, mixer, pango.WEIGHT_NORMAL])

    def on_treeview_toggled(self, cell, path, model):
        iter = model.get_iter_from_string(path)
        active = model.get_value(iter, 0)
        if not active:
            model.foreach(self.radio_toggle)
            model.set(iter, 0, not active)
            model.set(iter, 2, pango.WEIGHT_BOLD)

            prefs["control"] = model.get_value(iter, 1)
            self.main.update()
            self.write_file()

    def radio_toggle(self, model, path, iter):
        active = model.get(iter, 0)
        if active:
            model.set(iter, 0, not active)
            model.set(iter, 2, pango.WEIGHT_NORMAL)

    def on_scale_spinbutton_changed(self, widget):
        scale_increment = widget.get_value()
        prefs["scale_increment"] = scale_increment
        self.main.scale_increment = scale_increment

    def on_tooltip_toggled(self, widget):
        active = widget.get_active()
        prefs["show_tooltip"] = int(active)
        self.main.show_tooltip = active
        if active:
            volume = _("Muted") if self.main.alsactrl.is_muted() else self.main.alsactrl.get_volume()
            self.main.update_tooltip(volume)
        else:
            self.main.set_tooltip(None)

    def on_terminal_toggled(self, widget):
        active = widget.get_active()
        prefs["run_in_terminal"] = int(active)
        self.main.run_in_terminal = active

    def on_draw_value_toggled(self, widget):
        active = widget.get_active()
        prefs["scale_show_value"] = int(active)
        self.main.scale.set_draw_value(active)

    def on_entry_changed(self, widget):
        mixer = widget.get_text()
        prefs["mixer"] = mixer
        self.main.mixer = mixer

    def on_radio_mute_toggled(self, widget):
        if widget.get_active():
            prefs["toggle"] = "mute"
            self.main.toggle = "mute"

    def on_radio_mixer_toggled(self, widget):
        if widget.get_active():
            prefs["toggle"] = "mixer"
            self.main.toggle = "mixer"

    def on_keys_toggled(self, widget):
        active = widget.get_active()
        prefs["keys"] = int(active)
        self.main.keys = active
        self.main.init_keys_events()
        self.main.init_notify()
        self.set_sensitive(active)

    def set_sensitive(self, active):
        if not active:
            self.hal_radiobutton.set_sensitive(False)
            self.xlib_radiobutton.set_sensitive(False)
            self.notify_checkbutton.set_sensitive(False)
            self.timeout_spinbutton.set_sensitive(False)
        else:
            self.hal_radiobutton.set_sensitive(True)
            self.xlib_radiobutton.set_sensitive(True)
            self.notify_checkbutton.set_sensitive(True)
            if prefs["show_notify"] and self.main.notify:
                self.timeout_spinbutton.set_sensitive(True)
            else:
                self.timeout_spinbutton.set_sensitive(False)

    def on_notify_toggled(self, widget):
        active = widget.get_active()
        prefs["show_notify"] = int(active)
        self.main.show_notify = bool(int(active))
        self.main.init_notify()
        if active and self.main.notify:
            self.timeout_spinbutton.set_sensitive(True)
        else:
            self.timeout_spinbutton.set_sensitive(False)

    def on_timeout_spinbutton_changed(self, widget):
        scale_increment = widget.get_value()
        prefs["notify_timeout"] = scale_increment
        self.main.notify_timeout = scale_increment

    def on_radio_hal_toggled(self, widget):
        if widget.get_active():
            prefs["keys_backend"] = "hal"
            self.main.keys_backend = "hal"
            self.main.init_keys_events()

    def on_radio_xlib_toggled(self, widget):
        if widget.get_active():
            prefs["keys_backend"] = "xlib"
            self.main.keys_backend = "xlib"
            self.main.init_keys_events()

    def read_file(self):
        self.cp.read(self.main.config.CONFIG_FILE)
        for option in self.cp.options("global"):
            prefs[option.lower()] = self.cp.get("global", option).strip()
        self.set_section()
        prefs["control"] = self.cp.get(self.section, "control").strip()

    def write_file(self):
        if not os.path.isdir(self.main.config.CONFIG_DIR):
            try:
                os.makedirs(self.main.config.CONFIG_DIR)
            except OSError:
                pass
        for section in self.section, "global":
            if not self.cp.has_section(section):
                self.cp.add_section(section)
        for k,v in prefs.items():
            if k in ["control"]:
                self.cp.set(self.section, k, v)
            else:
                self.cp.set("global", k, v)
        self.cp.write(open(self.main.config.CONFIG_FILE, "w"))