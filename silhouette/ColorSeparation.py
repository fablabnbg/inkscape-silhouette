import os
import pickle

class ColorSeparation:
    """Keep sendto_silhouette settings on a per-color basis"""
    def __init__(self, *args, **kwargs):
        self.colors = kwargs.pop('colors', [])
        self.options = kwargs.pop('options')
        self.logger = kwargs.pop('logger')
        self.color_settings = {}
        self.color_enabled = {}

    def activate_preset(self, preset_name, silent=False):
        preset = self.read_preset(preset_name)
        self.logger("Loaded preset " + preset_name + ": "
                    + str(preset), not silent)
        if not preset:
            return preset
        self.extract_settings_from_preset(preset, silent)
        return preset

    def extract_settings_from_preset(self, preset, silent=False):
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

        self.logger("Reassigned " + str(reassigned) + " colors.",
                    self.options.verbose)
        self.logger("Colors remaining: " + str(extra_colors),
                    self.options.verbose)
        self.logger("Final colors: " + str(self.colors),
                    self.options.verbose)
        self.logger("Color settings: " + str(self.color_settings),
                    self.options.verbose)

        if reassigned:
            message.append("%d colors were reassigned." % reassigned)

        if extra_colors:
            message.append("%d colors from the preset were not used." % len(extra_colors))

        if message and not silent:
            Dialog.info(self, "Colors in the preset and this SVG did not match fully. " + " ".join(message))

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
        self.logger("saving presets: " + str(presets), write_log)
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
