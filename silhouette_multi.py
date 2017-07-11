#!/usr/bin/env python

import sys, os
from collections import defaultdict
import math
import struct
import time
import inkex
import simplestyle

class SilhouetteMulti(inkex.Effect):
    def parse_args(self, argv):
        args = {}
        ignored = []

        for arg in argv:
            if arg.startswith('--'):
                arg = arg[2:]
            else:
                ignored.append(arg)
                continue

            k, v = arg.split('=', 1)


            if k == "id":
                # ignore selected items, because we're going to create selections
                # based on colors
                continue

            args[k] = v

        return args, ignored

    def mock_options(self):
        class FakeOptions:
            ids = []

        self.options = FakeOptions()

    def getoptions(self, args=sys.argv[1:]):
        # getoptions() is called automatically by affect() and uses optparse.
        # We just want to store the args to pass through, so we override it.

        self.mock_options()

        self.globals = {}
        self.extra_args = []
        self.actions = defaultdict(dict)

        args, self.extra_args = self.parse_args(args)

        for k, v in args.iteritems():
            if k.startswith('action'):
                # example: action1_color
                action_name, k = k.split('_', 1)
                action_num = int(action_name[6:])

                self.actions[action_num][k] = v
            else:
                self.globals[k] = v

        self.tolerance = float(self.globals.pop('tolerance', 0))
        self.pause = float(self.globals.pop('pause', 0))
        self.debug = self.globals.pop('debug') == "true"


    def integer_to_rgb(self, color):
        # takes a packed 4-byte signed integer color like -16711681 and unpacks
        # it into a tuple of (red, green, blue) as unsigned integers
        # in the range 0-255.  Alpha is discarded.
        return struct.unpack("BBBB", struct.pack(">i", color))[0:3]

    def colors_match(self, color1, color2):
        # Do these colors match?
        #
        # Compare using self.tolerance, which specifies the maximum allowed
        # "distance".
        #
        # Colors are (r, g, b) tuples

        distance = math.sqrt((color1[0] - color2[0])**2 + \
                             (color1[1] - color2[1])**2 + \
                             (color1[2] - color2[2])**2)

        return distance <= self.tolerance

    def get_node_stroke_color(self, node):
        if node.get('style') is None:
            return None

        style = simplestyle.parseStyle(node.get('style'))

        if not style.get('stroke'):
            return None

        return simplestyle.parseColor(style.get('stroke'))

    def get_nodes_by_color(self, color, element=None, parent_visibility="visible"):
        if element is None:
            element = self.document.getroot()

        nodes_by_color = []

        for node in element:
            visibility = node.get('visibility', parent_visibility)

            if visibility == 'inherit':
                visibility = parent_visibility

            if visibility in ('hidden', 'collapse'):
                return []

            node_color = self.get_node_stroke_color(node)

            if node_color and self.colors_match(color, node_color):
                nodes_by_color.append(node)

            nodes_by_color.extend(self.get_nodes_by_color(color, node, visibility))

        return nodes_by_color

    def format_args(self, args):
        if isinstance(args, dict):
            args = args.iteritems()

        return " ".join(("--%s=%s" % (k, v) for k, v in args))

    def global_args(self):
        return self.format_args(self.globals)

    def id_args(self, nodes):
        return self.format_args(("id", node.get("id")) for node in nodes)

    def effect(self):
        # any output on stdout crashes inkscape, so let's avoid that
        old_stdout = sys.stdout
        sys.stdout = sys.stderr

        commands = []

        for action_num in sorted(self.actions.keys()):
            action = self.actions[action_num]

            if action['tool'] == 'none':
                continue

            color = self.integer_to_rgb(int(action.pop('color')))
            nodes = self.get_nodes_by_color(color)

            if not nodes:
                continue

            command = ("python sendto_silhouette.py" + " " +
                       self.global_args() + " " +
                       self.format_args(action) + " " +
                       self.id_args(nodes) + " " +
                       " ".join(self.extra_args))

            commands.append(command)

        if self.debug:
            print >> sys.stderr, "\n".join(commands)
        else:
            for command in commands:
                status = os.system(command)

                if status != 0:
                    print >> sys.stderr, "command returned exit status %s: %s" % (status, command)
                    break

                time.sleep(self.pause)

        sys.stdout = old_stdout


if __name__ == "__main__":
    #print >> sys.stderr, " ".join(sys.argv)
    #sys.exit(0)

    s = SilhouetteMulti()
    s.affect()

