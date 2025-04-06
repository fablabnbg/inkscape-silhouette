import wx
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib.agw import ultimatelistctrl as ulc
from wx.lib.agw import genericmessagedialog as gmd
from wx.lib.embeddedimage import PyEmbeddedImage

import xmltodict
from collections import OrderedDict

from silhouette.ColorSeparation import ColorSeparation

from silhouette.Dialog import Dialog

small_up_arrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYA"
    "AAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADxJ"
    "REFUOI1jZGRiZqAEMFGke2gY8P/f3/9kGwDT"
    "jM8QnAaga8JlCG3CAJdt2MQxDCAUaOjyjKMp"
    "cRAYAABS2CPsss3BWQAAAABJRU5ErkJggg==")

small_down_arrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYA"
    "AAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEhJ"
    "REFUOI1jZGRiZqAEMFGke9QABgYGBgYWdIH/"
    "//7+J6SJkYmZEacLkCUJacZqAD5DsInTLhDR"
    "bcPlKrwugGnCFy6Mo3mBAQChDgRlP4RC7wAAAABJRU5ErkJggg==")

class ParamsNotebook(wx.Notebook):
    """Handle a notebook of tabs that contain params.

    Each param has a name, and all names are globally unique across all tabs.
    """

    def __init__(self, *args, **kwargs):
        self.logger = kwargs.pop('logger')
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
                self.logger(f"unexpected INX format: '{path[1]}'")
                return False
            # And we make sure we are on a "page" of that notebook:
            (pagetag, pageattrs) = path[2]
            if pagetag != 'page':
                self.logger(f"unexpected INX notebook format: '{path[2]}'")
                return False
            pagename = pageattrs['name']
            # If it is a new page we have to initialize it:
            if not pagename in notebook:
                pagetitle = pageattrs['gui-text']
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
                self.logger(f"unexpected INX item format: '{path[3]}'")
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
            elif isinstance(input, wx.FilePickerCtrl):
                values[name] = input.GetPath()
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
            elif isinstance(input, wx.FilePickerCtrl):
                input.SetPath(value)
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
            display_text = param.get('@gui-text', '')
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
            elif param_type == 'optiongroup':
                choices = OrderedDict((option['#text'], option['@value']) for option in param['option'])
                self.choices_by_label[param_name] = choices
                self.choices_by_value[param_name] = { v: k for k, v in choices.items() }
                choice_list = list(choices.keys())
                input = wx.Choice(self, wx.ID_ANY, choices=choice_list, style=0)
                input.SetStringSelection(choice_list[0])
            elif param_type == 'string':
                input = wx.TextCtrl(self)
                iflag |= wx.EXPAND
            elif param_type == 'path':
                input = wx.FilePickerCtrl(self, wx.ID_ANY,
                                          path=param.get('#text', ''),
                                          wildcard = param.get('@filetypes') + " files (*." + param.get('@filetypes') + ")",
                                          name=param_name,
                                          style = wx.FLP_SAVE|wx.FLP_OVERWRITE_PROMPT|wx.FLP_USE_TEXTCTRL,
                                          message=display_text)
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


class MultiFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        # begin wxGlade: MyFrame.__init__
        self.colsep = kwargs.pop('color_separation')
        self.logger = kwargs.pop('logger')
        self.options = kwargs.pop('options')
        self.run_callback = kwargs.pop('run_callback')
        wx.Frame.__init__(self, None, wx.ID_ANY, "Silhouette Multi-Action")

        self.selected = None
        self.notebook = ParamsNotebook(self, wx.ID_ANY, logger=self.logger)
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
        self.Close()

    def close(self, event):
        self.wrapup()

    def load_preset(self, event):
        preset_name = self.get_preset_name()
        if not preset_name:
            return

        return self._load_preset(preset_name)

    def add_preset(self, event, overwrite=False):
        preset_name = self.get_preset_name()
        if not preset_name:
            return

        if not overwrite and self.load_preset(preset_name):
            Dialog.info(None, 'Preset "%s" already exists.  Please use another name or press "Overwrite"' % preset_name, caption='Preset')

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
            Dialog.info(None, 'Preset "%s" not found.' % preset_name, caption='Preset')

        return preset

    def get_preset_name(self):
        preset_name = self.preset_chooser.GetValue().strip()
        if preset_name:
            return preset_name
        else:
            Dialog.info(None, "Please enter or select a preset name first.", caption='Preset')
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

        return preset

    def _save_preset(self, preset_name):
        self.save_color_settings()

        preset = self.colsep.get_preset_data()
        self.colsep.save_preset(preset_name, preset)

    def run(self, event):
        self.save_color_settings()
        actions = self.colsep.generate_actions(self.notebook.get_defaults())
        if actions:
            if not self.options.dry_run:
                if not Dialog.confirm(None, "About to perform %d actions, continue?" % len(actions)):
                    return
        else:
            Dialog.info(None, "No colors were enabled, so no actions can be performed.")
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
        self.logger("save: " + str(self.selected), self.options.verbose)

        if self.selected is None:
            return

        color = self.colsep.colors[self.selected]
        settings = self.notebook.get_values()
        self.colsep.color_settings[color] = settings

        self.logger("settings: " + str(settings), self.options.verbose)

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
