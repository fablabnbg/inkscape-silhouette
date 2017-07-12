#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import cPickle
from tempfile import NamedTemporaryFile
from collections import defaultdict, OrderedDict
import xmltodict
import traceback
from cStringIO import StringIO
import wx
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib.agw import ultimatelistctrl as ulc
from wx.lib.embeddedimage import PyEmbeddedImage
from collections import defaultdict
import inkex
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



def presets_path():
    try:
        import appdirs
        config_path = appdirs.user_config_dir('inkscape-silhouette')
    except ImportError:
        config_path = os.path.expanduser('~/.inkscape-silhouette')

    if not os.path.exists(config_path):
        os.makedirs(config_path)
    return os.path.join(config_path, 'presets.cPickle')

def load_presets():
    try:
        with open(presets_path(), 'r') as presets:
            presets = cPickle.load(presets)
            return presets
    except:
        return {}

def save_presets(presets):
    #print "saving presets", presets
    with open(presets_path(), 'w') as presets_file:
        cPickle.dump(presets, presets_file)


def load_preset(name):
    return load_presets().get(name)


def save_preset(name, data):
    presets = load_presets()
    presets[name] = data
    save_presets(presets)


def delete_preset(name):
    presets = load_presets()
    presets.pop(name, None)
    save_presets(presets)


def confirm_dialog(parent, question, caption = 'Silhouette Multiple Actions'):
    dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
    result = dlg.ShowModal() == wx.ID_YES
    dlg.Destroy()
    return result


def info_dialog(parent, message, caption = 'Silhouette Multiple Actions'):
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()


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
        with open('sendto_silhouette.inx') as inx_file:
            self.inx = xmltodict.parse(inx_file, force_list=('param',))

    def create_tabs(self):
        self.notebook = self.inx['inkscape-extension']['param'][0]

        if self.notebook['@type'] != 'notebook':
            print >> sys.stderr, "unexpected INX format"
            return

        self.tabs = []
        for page in self.notebook['page']:
            self.tabs.append(ParamsTab(self, wx.ID_ANY, name=page['@name'], title=page['@_gui-text'], params=page['param']))

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
        self.settings_grid.AddGrowableCol(0, 1)
        self.settings_grid.SetFlexibleDirection(wx.HORIZONTAL)

        self.__set_properties()
        self.__do_layout()

    def get_values(self):
        values = {}

        for name, input in self.param_inputs.iteritems():
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
        for name, value in values.iteritems():
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
            param_name = param['@name']
            if param_type == 'description':
                self.settings_grid.Add(wx.StaticText(self, label=param.get('#text', '')),
                                       pos=(row, 0), span=(1, 2), flag=wx.EXPAND|wx.LEFT|wx.ALIGN_TOP, border=10)
            else:
                self.settings_grid.Add(wx.StaticText(self, label=param.get('@_gui-text', '')),
                                       pos=(row, 0), flag=wx.EXPAND|wx.TOP|wx.ALIGN_TOP, border=5)

                if param_type == 'boolean':
                    input = wx.CheckBox(self)
                elif param_type == 'float':
                    input = wx.SpinCtrlDouble(self, wx.ID_ANY, min=float(param.get('@min', 0.0)), max=float(param.get('@max', 2.0**32)), inc=0.1, value=param.get('#text', ''))
                elif param_type == 'int':
                    input = wx.SpinCtrl(self, wx.ID_ANY, min=int(param.get('@min', 0)), max=int(param.get('@max', 2**32)), value=param.get('#text', ''))
                elif param_type == 'enum':
                    choices = OrderedDict((item['#text'], item['@value']) for item in param['item'])
                    self.choices_by_label[param_name] = choices
                    self.choices_by_value[param_name] = { v: k for k, v in choices.iteritems() }
                    input = wx.Choice(self, wx.ID_ANY, choices=choices.keys(), style=wx.LB_SINGLE)
                    input.SetStringSelection(choices.keys()[0])
                else:
                    # not sure what else to do here...
                    continue

                self.param_inputs[param_name] = input

                self.settings_grid.Add(input, pos=(row, 1), flag=wx.ALIGN_BOTTOM|wx.TOP, border=5)

        self.defaults = self.get_values()

        box.Add(self.settings_grid, proportion=1, flag=wx.ALL, border=10)
        self.SetSizer(box)

        self.Layout()


class SilhouetteMultiFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        # begin wxGlade: MyFrame.__init__
        self.colors = kwargs.pop('colors', [])
        self.run_callback = kwargs.pop('run_callback')
        wx.Frame.__init__(self, None, wx.ID_ANY, 
                          "Silhouette Multi-Action"
                          )

        self.selected = None
        self.color_settings = {}
        self.color_enabled = {}
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

        self._load_preset('__LAST__')

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def close(self, event):
        self.Close()

    def load_preset(self, event):
        preset_name = self.get_preset_name()
        if not preset_name:
            return

        self._load_preset(preset_name)

    def add_preset(self, event, overwrite=False):
        preset_name = self.get_preset_name()
        if not preset_name:
            return

        if not overwrite and load_preset(preset_name):
            info_dialog(self, 'Preset "%s" already exists.  Please use another name or press "Overwrite"' % preset_name, caption='Preset')

        self.save_color_settings()
        save_preset(preset_name, self.get_preset_data())
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

        delete_preset(preset_name)
        self.update_preset_list()
        self.preset_chooser.SetValue("")

        event.Skip()

    def check_and_load_preset(self, preset_name):
        preset = load_preset(preset_name)
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
        preset_names = load_presets().keys()
        preset_names = [preset for preset in preset_names if not preset.startswith("__")]
        self.preset_chooser.SetItems(preset_names)

    def _load_preset(self, preset_name):
        preset = load_preset(preset_name)

        if not preset:
            return

        if self.selected:
            self.actions.Select(self.selected, False)

        old_colors = self.colors
        self.colors = []
        extra_colors = []

        for color in preset['colors']:
            if color in old_colors:
                old_colors.remove(color)
                self.colors.append(color)
                self.color_enabled[color] = preset['color_enabled'].get(color, True)
                self.color_settings[color] = preset['color_settings'].get(color, {})
            else:
                extra_colors.append(color)

        reassigned = 0
        # If there are any leftover colors in this SVG that weren't in the
        # preset, we have to add them back into the list.  Let's try to
        # use the settings from one of the "unclaimed" colors in the preset.

        for color in old_colors:
            if extra_colors:
                reassigned += 1
                assigned_color = extra_colors.pop(0)
                self.colors.append(color)
                self.color_enabled[color] = preset['color_enabled'].get(assigned_color, True)
                self.color_settings[color] = preset['color_settings'].get(assigned_color, {})

        message = []

        if reassigned:
            message.append("%d colors were reassigned." % reassigned)

        if extra_colors:
            message.append("%d colors from the preset were not used." % len(extra_colors))

        if message:
            info_dialog(self, "Colors in the preset and this SVG did not match fully. " + " ".join(message))

        self.refresh_actions()

    def _save_preset(self, preset_name):
        self.save_color_settings()

        preset = self.get_preset_data()
        save_preset(preset_name, preset)

    def get_preset_data(self):
        return { 'colors': self.colors,
                 'color_enabled': self.color_enabled,
                 'color_settings': self.color_settings }

    def run(self, event):
        self.save_color_settings()

        actions = []

        for color in self.colors:
            if self.color_enabled.get(color, True):
                actions.append((color, self.color_settings.get(color) or self.notebook.get_defaults()))

        if actions:
            if not confirm_dialog(self, "About to perform %d actions, continue?" % len(actions)):
                return
        else:
            info_dialog("No colors were enabled, so no actions can be performed.")
            return

        self._save_preset('__LAST__')
        self.run_callback(actions)

    def move_up(self, event):
        if self.selected is None or self.selected == 0:
            return

        this = self.selected
        prev = this - 1

        self.colors[this], self.colors[prev] = self.colors[prev], self.colors[this]
        self.actions.Select(this, False)
        self.actions.Select(prev)

        self.refresh_actions()

    def move_down(self, event):
        if self.selected is None or self.selected == len(self.colors) - 1:
            return

        this = self.selected
        next = this + 1

        self.colors[this], self.colors[next] = self.colors[next], self.colors[this]
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
        color = self.colors[self.selected]
        settings = self.color_settings.get(color)

        if settings:
            self.notebook.set_values(settings)
        else:
            self.notebook.set_defaults()

    def save_color_settings(self):
        #print "save:", self.selected

        if self.selected is None:
            return

        color = self.colors[self.selected]
        settings = self.notebook.get_values()
        self.color_settings[color] = settings

        #print "settings:", settings

    def item_checked(self, event):
        item = event.m_itemIndex
        checked = self.actions.IsItemChecked(item, 2)
        self.color_enabled[self.colors[item]] = checked

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

        for i, color in enumerate(self.colors):
            self.actions.InsertStringItem(i, "%d." % (i + 1))

            item = self.actions.GetItem(i, 2)
            item.SetKind(1) # "a checkbox-like item"
            item.SetMask(ulc.ULC_MASK_KIND)
            self.actions.SetItem(item)

        self.refresh_actions()

    def refresh_actions(self):
        for i, color in enumerate(self.colors):
            item = self.actions.GetItem(i, 1)
            item.SetMask(ulc.ULC_MASK_BACKCOLOUR)
            item.SetBackgroundColour(wx.Colour(*color))
            self.actions.SetItem(item)

            item = self.actions.GetItem(i, 2)
            item.Check(self.color_enabled.get(color, True))
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
        sizer_6.Add(self.cancel_button, 0, flag=wx.ALIGN_RIGHT|wx.EXPAND)
        sizer_2.Add(sizer_6, 0, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=30) 

        sizer_1.Add(sizer_2, 0, flag=wx.EXPAND|wx.ALL, border=10)

        sizer_1.Add(self.notebook, 1, wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, 10)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        # end wxGlade

class SilhouetteMulti(inkex.Effect):
    def get_style(self, element):
        if element.get('style') is not None:
            return simplestyle.parseStyle(element.get('style'))
        else:
            return {}

        return style

    def get_stroke_color(self, element):
        stroke = self.get_style(element).get('stroke')

        if stroke is not None and stroke != 'none':
            return simplestyle.parseColor(stroke)
        else:
            return None

    def load_selected_objects(self):
        self.selected_objects = set()

        def traverse_element(element, selected=False, parent_visibility="visible"):
            if self.get_style(element).get('display') == 'none':
                return

            visibility = element.get('visibility', parent_visibility)

            if visibility == 'inherit':
                visibility = parent_visibility

            if element.get('id') in self.selected:
                selected = True

            if selected and visibility not in ('hidden', 'collapse'):
                self.selected_objects.add(element)

            for child in element:
                traverse_element(child, visibility)

        traverse_element(self.document.getroot())

    def split_objects_by_color(self):
        self.objects_by_color = defaultdict(list)
        self.load_selected_objects()

        for obj in self.selected_objects:
            color = self.get_stroke_color(obj)
            if color:
                self.objects_by_color[color].append(obj)

    def effect(self):
        app = wx.App()
        self.split_objects_by_color()
        self.frame = SilhouetteMultiFrame(colors=self.objects_by_color.keys(), run_callback=self.run)
        self.frame.Show()
        app.MainLoop()

    def save_copy(self):
        f = NamedTemporaryFile(suffix='.svg', prefix='silhouette-multiple-actions')
        self.document.write(f)
        f.flush()
        return f

    def format_args(self, args):
        if isinstance(args, dict):
            args = args.iteritems()

        return " ".join(("--%s=%s" % (k, v) for k, v in args))

    def id_args(self, nodes):
        return self.format_args(("id", node.get("id")) for node in nodes)

    def run(self, actions):
        svg_file = self.save_copy()

        for color, settings in actions:
            command = "python sendto_silhouette.py "
            command += self.format_args(settings)
            command += self.id_args(self.objects_by_color[color])
            command += " " + svg_file.name

            #print >> sys.stderr, command

            status = os.system(command)

            if status != 0:
                print >> sys.stderr, "command returned exit status %s: %s" % (status, command)
                break



        self.frame.Close()


def save_stderr():
    # GTK likes to spam stderr, which inkscape will show in a dialog.
    null = open('/dev/null', 'w')
    sys.stderr_dup = os.dup(sys.stderr.fileno())
    os.dup2(null.fileno(), 2)
    sys.stderr_backup = sys.stderr
    sys.stderr = StringIO()


def restore_stderr():
    os.dup2(sys.stderr_dup, 2)
    sys.stderr_backup.write(sys.stderr.getvalue())
    sys.sys.stderr = stderr_backup


# end of class MyFrame
if __name__ == "__main__":
    save_stderr()

    try:
        e = SilhouetteMulti()
        e.affect()
    except:
        traceback.print_exc()

    restore_stderr()
