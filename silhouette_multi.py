#!/usr/bin/env python3

import os
import sys
import time
import pickle
import subprocess
from threading import Thread
from tempfile import NamedTemporaryFile
from pathlib import Path
from collections import defaultdict, OrderedDict
import xmltodict
import traceback
from io import StringIO
import wx
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib.agw import ultimatelistctrl as ulc
from wx.lib.agw import genericmessagedialog as gmd
from wx.lib.embeddedimage import PyEmbeddedImage
from inkex.extensions import EffectExtension
from inkex import addNS, Boolean, Style, Color
import simplestyle
from functools import partial
from itertools import groupby


small_up_arrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADxJ"
    "REFUOI1jZGRiZqAEMFGke2gY8P/f3/9kGwDTjM8QnAaga8JlCG3CAJdt2MQxDCAUaOjyjKMp"
    "cRAYAABS2CPsss3BWQAAAABJRU5ErkJggg==")

small_down_arrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEhJ"
    "REFUOI1jZGRiZqAEMFGke9QABgYGBgYWdIH///7+J6SJkYmZEacLkCUJacZqAD5DsInTLhDR"
    "bcPlKrwugGnCFy6Mo3mBAQChDgRlP4RC7wAAAABJRU5ErkJggg==")

multilogfile = None

def emit_to_log(msg, whether=True):
    if whether:
        print(msg, file=multilogfile)
        multilogfile.flush()


def show_log_as_dialog(parent=None):
    logname = multilogfile.name
    multilogfile.close()
    logtext = Path(logname).read_text().strip()
    if logtext:
        info_dialog(parent, logtext, caption='Silhouette Multi Log')


def confirm_dialog(parent, question, caption = 'Silhouette Multiple Actions'):
    dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
    result = dlg.ShowModal() == wx.ID_YES
    dlg.Destroy()
    return result


def info_dialog(parent, message, extended = '',
                caption = 'Silhouette Multiple Actions',):
    dlg = gmd.GenericMessageDialog(
        parent, message, caption, wrap=1000,
        agwStyle=wx.OK | wx.ICON_INFORMATION | gmd.GMD_USE_AQUABUTTONS)
    # You might wonder about the choice of "aquabuttons" above. It's the
    # only option that led to the buttons being visible on the system
    # this was first tested on.
    dlg.SetLayoutAdaptationMode(wx.DIALOG_ADAPTATION_MODE_ENABLED)
    if extended:
        dlg.SetExtendedMessage(extended)
    dlg.ShowModal()
    dlg.Destroy()

class ColorSeparation:
    """Keep sendto_silhouette settings on a per-color basis"""
    def __init__(self, *args, **kwargs):
        self.colors = kwargs.pop('colors', [])
        self.options = kwargs.pop('options')
        self.color_settings = {}
        self.color_enabled = {}

    def activate_preset(self, preset_name, silent=False):
        preset = self.read_preset(preset_name)
        emit_to_log("Loaded preset " + preset_name + ": "
                    + str(preset), not silent)
        if not preset:
            return preset
        self.extract_settings_from_preset(preset)
        return preset

    def extract_settings_from_preset(self, preset):
        old_colors = self.colors
        self.colors = []
        extra_colors = []

        for color in preset['colors']:
            if color in old_colors:
                old_colors.remove(color)
                self.colors.append(color)
                self.color_enabled[color] = preset['color_enabled'].get(
                    color, True)
                self.color_settings[color] = preset['color_settings'].get(
                    color, {})
            else:
                extra_colors.append(color)

        reassigned = 0
        # If there are any leftover colors in this SVG that weren't in the
        # preset, we have to add them back into the list.  Let's try to
        # use the settings from one of the "unclaimed" colors in the preset.

        for color in old_colors:
            self.colors.append(color)

            if extra_colors:
                reassigned += 1
                assigned_color = extra_colors.pop(0)
                self.color_enabled[color] = preset['color_enabled'].get(
                    assigned_color, True)
                self.color_settings[color] = preset['color_settings'].get(
                    assigned_color, {})
            else:
                self.color_enabled[color] = False

        message = []

        emit_to_log("Reassigned " + str(reassigned) + " colors.",
                    self.options.verbose)
        emit_to_log("Colors remaining: " + str(extra_colors),
                    self.options.verbose)
        emit_to_log("Final colors: " + str(self.colors),
                    self.options.verbose)
        emit_to_log("Color settings: " + str(self.color_settings),
                    self.options.verbose)

        if reassigned:
            message.append("%d colors were reassigned." % reassigned)

        if extra_colors:
            message.append("%d colors from the preset were not used." % len(extra_colors))

        if message and not silent:
            info_dialog(self, "Colors in the preset and this SVG did not match fully. " + " ".join(message))

    def generate_actions(self, default_actions):
        actions = []
        for color in self.colors:
            if self.color_enabled.get(color, True):
                actions.append(
                    (color, self.color_settings.get(color) or default_actions))
        return actions

    def get_preset_data(self):
        return { 'colors': self.colors,
                 'color_enabled': self.color_enabled,
                 'color_settings': self.color_settings }

    def read_preset(self, name):
        return self.read_presets().get(name)

    def read_presets(self):
        try:
            with open(self.presets_path(), 'rb') as presets:
                presets = pickle.load(presets)
                return presets
        except:
            return {}

    def save_presets(self, presets, write_log=False):
        emit_to_log("saving presets: " + str(presets), write_log)
        with open(self.presets_path(), 'wb') as presets_file:
            pickle.dump(presets, presets_file)

    def save_preset(self, name, data, write_log=False):
        presets = self.read_presets()
        presets[name] = data
        self.save_presets(presets, write_log)

    def remove_preset(self, name):
        presets = self.read_presets()
        presets.pop(name, None)
        self.save_presets(presets)

    def presets_path(self):
        if self.options.pickle_path:
            return self.options.pickle_path
        try:
            import appdirs
            config_path = appdirs.user_config_dir('inkscape-silhouette')
        except ImportError:
            config_path = os.path.expanduser('~/.inkscape-silhouette')

        if not os.path.exists(config_path):
            os.makedirs(config_path)
        return os.path.join(config_path, 'presets.cPickle')


class ParamsNotebook(wx.Notebook):
    """Handle a notebook of tabs that contain params.

    Each param has a name, and all names are globally unique across all tabs.
    """

    def __init__(self, *args, **kwargs):
        wx.Notebook.__init__(self, *args, **kwargs)

        self.load_inx()
        self.create_tabs()
        self.add_tabs()

    def load_inx(self):
        notebook = {}

        def addToPage(path, item):
            # This function will process all of the fourth-level tags in
            # sendto_silhouette.inx. We want all of the items on all of the
            # "pages" of the "notebook". First we ignore the only other
            # second-level tag that has fourth-level descendents:
            (booktag, bookattrs) = path[1]
            if booktag == 'effect':
                return True
            # Next we check that we are indeed in the notebook 2nd-level tag:
            if booktag != 'param' or bookattrs['type'] != 'notebook':
                emit_to_log(f"unexpected INX format: '{path[1]}'")
                return False
            # And we make sure we are on a "page" of that notebook:
            (pagetag, pageattrs) = path[2]
            if pagetag != 'page':
                emit_to_log(f"unexpected INX notebook format: '{path[2]}'")
                return False
            pagename = pageattrs['name']
            # If it is a new page we have to initialize it:
            if not pagename in notebook:
                pagetitle = pageattrs['_gui-text']
                notebook[pagename] = dict(title=pagetitle, param=[])
            # Ultimately we want a dict to represent the item on the page,
            # but if there is a text body to the tag, it comes as a string:
            if isinstance(item, str):
                item = {'#text': item.strip()}
            # path[3] is the fourth-level tag itself:
            (tagname, tagattrs) = path[3]
            # rebuild the dict as it would have been without an item handler:
            for attr in tagattrs or []:
                item['@'+attr] = path[3][1][attr]
            if tagname == 'label':
                item['@type'] = 'description'  # re-create the old .inx format
            elif tagname != 'param':
                emit_to_log(f"unexpected INX item format: '{path[3]}'")
                return False
            notebook[pagename]['param'].append(item)
            return True

        with open('sendto_silhouette.inx', 'rb') as inx_file:
            self.inx = xmltodict.parse(
                inx_file, item_depth = 4, item_callback = addToPage)
        self.notebook = notebook

    def create_tabs(self):
        self.tabs = []
        for pagename, attrs in self.notebook.items():
            self.tabs.append(ParamsTab(self, wx.ID_ANY, name=pagename, title=attrs['title'], params=attrs['param']))

    def add_tabs(self):
        for tab in self.tabs:
            self.AddPage(tab, tab.title)

    def get_values(self):
        values = {}

        for tab in self.tabs:
            values.update(tab.get_values())

        return values

    def get_defaults(self):
        values = {}

        for tab in self.tabs:
            values.update(tab.get_defaults())

        return values


    def set_values(self, values):
        for tab in self.tabs:
            tab.set_values(values)


    def set_defaults(self):
        for tab in self.tabs:
            tab.set_defaults()


class ParamsTab(ScrolledPanel):
    def __init__(self, *args, **kwargs):
        self.params = kwargs.pop('params', [])
        self.name = kwargs.pop('name', None)
        self.title = kwargs.pop('title', None)
        kwargs["style"] = wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwargs)
        self.SetupScrolling()

        self.param_inputs = {}
        self.choices_by_label = {}
        self.choices_by_value = {}
        self.defaults = {}

        self.settings_grid = wx.GridBagSizer(hgap=0, vgap=0)

        self.__set_properties()
        self.__do_layout()

    def get_values(self):
        values = {}

        for name, input in self.param_inputs.items():
            if isinstance(input, wx.Choice):
                choice = input.GetSelection()

                if choice == wx.NOT_FOUND:
                    values[name] = None
                else:
                    values[name] = self.choices_by_label[name][input.GetString(choice)]
            else:
                values[name] = input.GetValue()
        return values

    def get_defaults(self):
        return self.defaults

    def set_values(self, values):
        for name, value in values.items():
            if name not in self.param_inputs:
                # ignore params not contained in this tab
                continue

            input = self.param_inputs[name]

            if isinstance(input, wx.Choice):
                if value is None:
                    input.SetSelection(wx.NOT_FOUND)
                else:
                    label = self.choices_by_value[name][value]
                    input.SetStringSelection(label)
            else:
                input.SetValue(value)

    def set_defaults(self):
        self.set_values(self.defaults)

    def __set_properties(self):
        # begin wxGlade: SatinPane.__set_properties
        # end wxGlade
        pass

    def __do_layout(self):
        # just to add space around the settings
        box = wx.BoxSizer(wx.VERTICAL)

        for row, param in enumerate(self.params):
            param_type = param['@type']
            param_name = param.get('@name','**unnamed**')
            display_text = param.get('@_gui-text', '')
            text_span = (1, 2)
            text_pos = (row, 0)
            text_flag = wx.EXPAND|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL
            input = None
            ipos = (row, 2)
            iflag = wx.ALIGN_CENTER_VERTICAL
            if param_type == 'description':
                display_text = param.get('#text', '')
                text_span = (1,3)
                text_flag |= wx.BOTTOM
            elif param_type == 'bool':
                input = wx.CheckBox(self)
                text_pos = (row, 1)
                ipos = (row,0)
            elif param_type == 'float':
                input = wx.SpinCtrlDouble(
                    self, wx.ID_ANY, min=float(param.get('@min', 0.0)),
                    max=float(param.get('@max', 2.0**32)), inc=0.1,
                    value=param.get('#text', ''))
            elif param_type == 'int':
                input = wx.SpinCtrl(
                    self, wx.ID_ANY, min=int(param.get('@min', 0)),
                    max=int(param.get('@max', 2**32)),
                    value=param.get('#text', ''))
            elif param_type == 'enum':
                choices = OrderedDict((item['#text'], item['@value']) for item in param['item'])
                self.choices_by_label[param_name] = choices
                self.choices_by_value[param_name] = { v: k for k, v in choices.items() }
                choice_list = list(choices.keys())
                input = wx.Choice(self, wx.ID_ANY, choices=choice_list,
                                  style=wx.LB_SINGLE)
                input.SetStringSelection(choice_list[0])
            elif param_type == 'string':
                input = wx.TextCtrl(self)
                iflag |= wx.EXPAND

            textbox = wx.StaticText(self, label=display_text)
            textbox.Wrap(800)
            self.settings_grid.Add(textbox, pos=text_pos, span=text_span,
                                   border=10, flag=text_flag)
            if input:
                self.param_inputs[param_name] = input
                self.settings_grid.Add(input, pos=ipos, border=5, flag=iflag)

        self.defaults = self.get_values()

        box.Add(self.settings_grid, proportion=1, flag=wx.ALL, border=10)
        self.SetSizer(box)

        self.Layout()


class SilhouetteMultiFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        # begin wxGlade: MyFrame.__init__
        self.colsep = kwargs.pop('color_separation')
        self.options = kwargs.pop('options')
        self.run_callback = kwargs.pop('run_callback')
        wx.Frame.__init__(self, None, wx.ID_ANY, "Silhouette Multi-Action")

        self.selected = None
        self.notebook = ParamsNotebook(self, wx.ID_ANY)
        self.up_button = wx.Button(self, wx.ID_UP)
        self.down_button = wx.Button(self, wx.ID_DOWN)
        self.run_button = wx.Button(self, wx.ID_EXECUTE)
        self.cancel_button = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.presets_box = wx.StaticBox(self, wx.ID_ANY, label="Presets")
        self.preset_chooser = wx.ComboBox(self, wx.ID_ANY, style=wx.CB_SORT)
        self.load_preset_button = wx.Button(self, wx.ID_REVERT_TO_SAVED, "Load")
        self.add_preset_button = wx.Button(self, wx.ID_SAVE, "Add")
        self.overwrite_preset_button = wx.Button(self, wx.ID_SAVEAS, "Overwrite")
        self.delete_preset_button = wx.Button(self, wx.ID_DELETE, "Delete")

        self.update_preset_list()
        self.init_actions()

        self.Bind(wx.EVT_BUTTON, self.move_up, self.up_button)
        self.Bind(wx.EVT_BUTTON, self.move_down, self.down_button)
        self.Bind(wx.EVT_BUTTON, self.run, self.run_button)
        self.Bind(wx.EVT_BUTTON, self.load_preset, self.load_preset_button)
        self.Bind(wx.EVT_BUTTON, self.add_preset, self.add_preset_button)
        self.Bind(wx.EVT_BUTTON, self.overwrite_preset, self.overwrite_preset_button)
        self.Bind(wx.EVT_BUTTON, self.delete_preset, self.delete_preset_button)
        self.Bind(wx.EVT_BUTTON, self.close, self.cancel_button)

        self._load_preset('__LAST__', silent=True)
        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def wrapup(self):
        if self.options.unblock_inkscape:
            show_log_as_dialog(self)
        self.Close()

    def close(self, event):
        self.wrapup()

    def load_preset(self, event):
        preset_name = self.get_preset_name()
        if not preset_name:
            return

        self._load_preset(preset_name)

    def add_preset(self, event, overwrite=False):
        preset_name = self.get_preset_name()
        if not preset_name:
            return

        if not overwrite and self.load_preset(preset_name):
            info_dialog(self, 'Preset "%s" already exists.  Please use another name or press "Overwrite"' % preset_name, caption='Preset')

        self.save_color_settings()
        self.colsep.save_preset(
            preset_name, self.colsep.get_preset_data(), self.options.verbose)
        self.update_preset_list()

        event.Skip()

    def overwrite_preset(self, event):
        self.add_preset(event, overwrite=True)

    def delete_preset(self, event):
        preset_name = self.get_preset_name()
        if not preset_name:
            return

        preset = self.check_and_load_preset(preset_name)
        if not preset:
            return

        self.colsep.remove_preset(preset_name)
        self.update_preset_list()
        self.preset_chooser.SetValue("")

        event.Skip()

    def check_and_load_preset(self, preset_name):
        preset = self.load_preset(preset_name)
        if not preset:
            info_dialog(self, 'Preset "%s" not found.' % preset_name, caption='Preset')

        return preset

    def get_preset_name(self):
        preset_name = self.preset_chooser.GetValue().strip()
        if preset_name:
            return preset_name
        else:
            info_dialog(self, "Please enter or select a preset name first.", caption='Preset')
            return

    def update_preset_list(self):
        preset_names = self.colsep.read_presets().keys()
        preset_names = [preset for preset in preset_names if not preset.startswith("__")]
        self.preset_chooser.SetItems(preset_names)

    def _load_preset(self, preset_name, silent=False):
        preset = self.colsep.activate_preset(preset_name, silent)
        if not preset:
            return
        if self.selected:
            self.actions.Select(self.selected, False)
        self.refresh_actions()

    def _save_preset(self, preset_name):
        self.save_color_settings()

        preset = self.colsep.get_preset_data()
        self.colsep.save_preset(preset_name, preset)

    def run(self, event):
        self.save_color_settings()
        actions = self.colsep.generate_actions(self.notebook.get_defaults)
        if actions:
            if not self.options.dry_run:
                if not confirm_dialog(self, "About to perform %d actions, continue?" % len(actions)):
                    return
        else:
            info_dialog(self, "No colors were enabled, so no actions can be performed.")
            return

        self._save_preset('__LAST__')
        self.run_callback(actions)

    def move_up(self, event):
        if self.selected is None or self.selected == 0:
            return

        this = self.selected
        prev = this - 1

        self.colsep.colors[this], self.colsep.colors[prev] = (
            self.colsep.colors[prev], self.colsep.colors[this])
        self.actions.Select(this, False)
        self.actions.Select(prev)

        self.refresh_actions()

    def move_down(self, event):
        if self.selected is None or self.selected == len(self.colors) - 1:
            return

        this = self.selected
        next = this + 1

        self.colsep.colors[this], self.colsep.colors[next] = (
            self.colsep.colors[next], self.colsep.colors[this])
        self.actions.Select(this, False)
        self.actions.Select(next)

        self.refresh_actions()

    def action_selected(self, event=None):
        # first, save the settings for the color they were previously working on
        self.save_color_settings()

        # then load the settings for the newly-selected color
        self.selected = event.m_itemIndex
        self.load_color_settings()

        self.up_button.Enable()
        self.down_button.Enable()
        self.notebook.Enable()

    def action_deselected(self, event=None):
        self.save_color_settings()

        self.selected = None

        self.up_button.Disable()
        self.down_button.Disable()
        self.notebook.Disable()

    def load_color_settings(self):
        color = self.colsep.colors[self.selected]
        settings = self.colsep.color_settings.get(color)

        if settings:
            self.notebook.set_values(settings)
        else:
            self.notebook.set_defaults()

    def save_color_settings(self):
        emit_to_log("save: " + str(self.selected), self.options.verbose)

        if self.selected is None:
            return

        color = self.colsep.colors[self.selected]
        settings = self.notebook.get_values()
        self.colsep.color_settings[color] = settings

        emit_to_log("settings: " + str(settings), self.options.verbose)

    def item_checked(self, event):
        item = event.m_itemIndex
        checked = self.actions.IsItemChecked(item, 2)
        self.colsep.color_enabled[self.colsep.colors[item]] = checked

    def init_actions(self):
        self.actions = ulc.UltimateListCtrl(self, size=(300, 150), agwStyle=wx.LC_REPORT|ulc.ULC_HRULES|ulc.ULC_SINGLE_SEL)

        self.Bind(ulc.EVT_LIST_ITEM_SELECTED, self.action_selected, self.actions)
        self.Bind(ulc.EVT_LIST_ITEM_DESELECTED, self.action_deselected, self.actions)
        self.Bind(ulc.EVT_LIST_ITEM_CHECKED, self.item_checked, self.actions)
        self.action_deselected()

        self.actions.InsertColumn(0, "Step")
        self.actions.InsertColumn(1, "Color")
        self.actions.InsertColumn(2, "Perform Action?")
        self.actions.SetColumnWidth(2, ulc.ULC_AUTOSIZE_FILL)

        self.action_checkboxes = []

        for i, color in enumerate(self.colsep.colors):
            self.actions.InsertStringItem(i, "%d." % (i + 1))

            item = self.actions.GetItem(i, 2)
            item.SetKind(1) # "a checkbox-like item"
            item.SetMask(ulc.ULC_MASK_KIND)
            self.actions.SetItem(item)

        self.refresh_actions()

    def refresh_actions(self):
        for i, color in enumerate(self.colsep.colors):
            item = self.actions.GetItem(i, 1)
            item.SetMask(ulc.ULC_MASK_BACKCOLOUR|ulc.ULC_MASK_TEXT)
            wxcol = wx.Colour(255,255,255)
            if color != 'colorless':
                item.SetText(' ')
                wxcol = wx.Colour(*color)
            else:
                item.SetText('<no color>')
            item.SetBackgroundColour(wxcol)
            self.actions.SetItem(item)

            item = self.actions.GetItem(i, 2)
            item.Check(self.colsep.color_enabled.get(color, True))
            item.SetMask(ulc.ULC_MASK_CHECK)
            self.actions.SetItem(item)


    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle("Silhouette Multi-Action")
        self.notebook.SetMinSize((800, 800))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.actions, 0, flag=wx.ALL|wx.EXPAND, border=10)

        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_3.Add(self.up_button, 0, border=10)
        sizer_3.Add(self.down_button, 0, border=10)

        sizer_2.Add(sizer_3, 0, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)

        sizer_4 = wx.StaticBoxSizer(self.presets_box, wx.VERTICAL)
        sizer_4.Add(self.preset_chooser, 0, flag=wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, border=10)

        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5.Add(self.load_preset_button, 0, flag=wx.RIGHT|wx.LEFT|wx.BOTTOM, border=10)
        sizer_5.Add(self.add_preset_button, 0, flag=wx.RIGHT, border=10)
        sizer_5.Add(self.overwrite_preset_button, 0, flag=wx.RIGHT, border=10)
        sizer_5.Add(self.delete_preset_button, 0, flag=wx.RIGHT, border=10)

        sizer_4.Add(sizer_5, 0)
        sizer_2.Add(sizer_4, 0, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=30)

        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        sizer_6.Add(self.run_button, 0, flag=wx.ALIGN_RIGHT|wx.BOTTOM, border=10)
        sizer_6.Add(self.cancel_button, 0, flag=wx.ALIGN_RIGHT)
        sizer_2.Add(sizer_6, 0, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=30)

        sizer_1.Add(sizer_2, 0, flag=wx.EXPAND|wx.ALL, border=10)

        sizer_1.Add(self.notebook, 1, wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, 10)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        # end wxGlade


class SilhouetteMulti(EffectExtension):
    def __init__(self, *args, **kwargs):
        EffectExtension.__init__(self, *args, **kwargs)

        self.saved_argv = list(sys.argv)

        self.arg_parser.add_argument(
            "-b", "--block", dest="block_inkscape", type=Boolean,
            default=False,
            help="Make inkscape wait until silhouette_multi is done")
        self.arg_parser.add_argument(
            "-d", "--dry_run", dest="dry_run", type=Boolean,
            default=False,
            help="Display generated commands but do not run them")
        self.arg_parser.add_argument(
            "-g", "--gui", dest="gui", type=Boolean,
            default=True,
            help="Should silhouette_multi use a gui to select its actions?")
        self.arg_parser.add_argument(
            "-p", "--pickle", dest="pickle_path", type=str,
            default='',
            help="Path of the pickle file with initial option settings")
        self.arg_parser.add_argument(
            "-v", "--verbose", dest="verbose", type=Boolean,
            default=False,
            help="Enable verbose logging")

    def get_style(self, element):
        element_style = element.get('style')
        if element_style is not None:
            return dict(Style.parse_str(element_style))
        return {}

    def get_color(self, element):
        if (element.tag == addNS('g', 'svg')
            or element.tag == addNS('svg', 'svg')):
            # Make sure we don't report a color on a group or on the svg as a whole
            # (to avoid duplicate cutting)
            return None

        color = self.get_style(element).get('stroke', 'colorless')

        if color == 'colorless':
            color = self.get_style(element).get('fill', 'colorless')

        if color != 'colorless':
            color = Color(color).to_rgb()
        return color

    def load_selected_objects(self):
        self.selected_objects = []

        def traverse_element(element, selected=False, parent_visibility="visible"):
            if self.get_style(element).get('display') == 'none':
                return

            visibility = element.get('visibility', parent_visibility)

            if visibility == 'inherit':
                visibility = parent_visibility

            if element.get('id') in self.svg.selected:
                selected = True

            if selected and visibility not in ('hidden', 'collapse'):
                self.selected_objects.append(element)

            for child in element:
                traverse_element(child, selected, visibility)

        # if they haven't selected specific objects, then process all objects
        if self.svg.selected:
            select_all = False
        else:
            select_all = True

        traverse_element(self.document.getroot(), selected=select_all)

    def split_objects_by_color(self):
        self.objects_by_color = defaultdict(list)
        self.load_selected_objects()

        for obj in self.selected_objects:
            color = self.get_color(obj)
            if color:
                self.objects_by_color[color].append(obj)

    def effect(self):
        emit_to_log("silhouette_multi.py was called via: "
                    + str(self.saved_argv), self.options.verbose)
        setattr(self.options, 'unblock_inkscape',
                not self.options.block_inkscape)
        self.split_objects_by_color()
        emit_to_log("Color keys are " + str(self.objects_by_color.keys()),
                    self.options.verbose)
        self.color_separation = ColorSeparation(
            colors=list(self.objects_by_color.keys()),
            options=self.options)
        app = wx.App()
        self.frame = SilhouetteMultiFrame(
            color_separation=self.color_separation,
            run_callback=self.run_multi, options=self.options)
        self.frame.Show()
        app.MainLoop()

    def save_copy(self):
        self.svg_copy_file = NamedTemporaryFile(
            suffix='.svg', prefix='silhouette-multiple-actions',
            delete=False) # this way the temp file will remain if error
        self.svg_copy_file_name = self.svg_copy_file.name
        self.document.write(self.svg_copy_file)
        self.svg_copy_file.flush()
        self.svg_copy_file.close()

    def format_args(self, args):
        if isinstance(args, dict):
            args = args.items()

        return " ".join(("--%s=%s" % (k, v) for k, v in args))

    def id_args(self, nodes):
        return self.format_args(("id", node.get("id")) for node in nodes)

    def format_commands(self, actions):
        commands = []

        for color, settings in actions:
            command = sys.executable
            command += " sendto_silhouette.py"
            command += " " + self.format_args(settings)
            command += " " + self.id_args(self.objects_by_color[color])
            command += " " + self.svg_copy_file_name

            commands.append(command)

        return commands

    def run_multi(self, actions):
        if self.options.dry_run:
            self.svg_copy_file_name = '<DUMMY_FILE>'
        else:
            self.save_copy()
        commands = self.format_commands(actions)
        self.frame.wrapup()
        if self.options.dry_run:
            emit_to_log("\n\n".join(commands))
        else:
            self.run_commands_with_dialog(commands)
            os.remove(self.svg_copy_file_name)

    def run_commands_with_dialog(self, commands):
        for i, command in enumerate(commands):
            returncode = self.run_command_with_dialog(command, step=i + 1, total=len(commands))
            if returncode != 0:
                # At this point, we have already displayed the log if we are
                # going to. So if we want the user to see the failed command
                # we just have to go ahead and display it.
                # But we will use the dialog's extended message to reduce
                # visual clutter
                info_dialog(None, "Action failed.",
                            extended = f"Return code: {returncode}\nCommand: '{command}'")

                sys.exit(1)

    def run_command_with_dialog(self, command, step, total):
        # exec ensures that the shell gets replaced so that we can terminate the
        # actual python script if the user cancels
        process = subprocess.Popen("exec " + command, shell=True)

        dialog = wx.ProgressDialog(style=wx.PD_APP_MODAL|wx.PD_CAN_ABORT|wx.PD_ELAPSED_TIME,
                                   message="Performing action %d of %d..." % (step, total),
                                   title="Silhouette Multiple Actions")

        last_tick = time.time()

        while process.returncode is None:
            if time.time() - last_tick > 0.5:
                dialog.Pulse()
                last_tick = time.time()

            process.poll()
            wx.Yield()
            time.sleep(0.1)

            if dialog.WasCancelled():
                def cancel():
                    process.terminate()
                    process.wait()

                Thread(target=cancel).start()

                dialog.Destroy()
                wx.Yield()
                info_dialog(None, "Action aborted.  It may take awhile for the machine to cancel its operation.")
                sys.exit(1)

        dialog.Destroy()
        wx.Yield()
        return process.returncode

    # end of class MyFrame


if __name__ == "__main__":

    unblock_inkscape = True
    if '--block=true' in sys.argv:
        unblock_inkscape = False

    pid = 0

    if unblock_inkscape: pid = os.fork()

    if pid != 0:
        # We forked and this is the "parent", so just return
        sys.exit(0)

    # Here we are in the process that will do the actual work:

    if unblock_inkscape:
        # Closing stdout and stderr allows inkscape to continue on
        # while the silhouette machine is cutting.  This is useful if you're
        # cutting something really big and want to work on another document.
        os.close(1)
        os.close(2)

        multilogfile = NamedTemporaryFile(
            suffix='.log', prefix='silhouette-multiple-actions',
            mode='w', delete=False)
    else:
        multilogfile = sys.stderr

    try:
        e = SilhouetteMulti()
        e.run()
    except:
        traceback.print_exc(file=multilogfile)
        # SilhouetteMultiFrame.wrapup likely never called if there was
        # an exception, so:
        if unblock_inkscape:
            show_log_as_dialog()

    sys.exit(0)
