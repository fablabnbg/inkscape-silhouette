#!/usr/bin/env python3

import os
import sys
import time
import subprocess
from threading import Thread
from tempfile import NamedTemporaryFile
from pathlib import Path
from collections import defaultdict
import traceback
from io import StringIO
from inkex.extensions import EffectExtension
from inkex import addNS, Boolean, Style, Color
import simplestyle
from functools import partial
from itertools import groupby

from silhouette.ColorSeparation import ColorSeparation

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
            logger=emit_to_log,
            options=self.options)
        if self.options.gui:
            import wx
            from silhouette.MultiFrame import MultiFrame

            app = wx.App()
            self.frame = MultiFrame(
                color_separation=self.color_separation,
                logger=emit_to_log,
                run_callback=self.run_multi,
                options=self.options)
            self.frame.Show()
            app.MainLoop()
        else:
            self.color_separation.activate_preset('__LAST__', silent=True)
            self.run_multi(self.color_separation.generate_actions({}))

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
        if self.options.gui:
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
