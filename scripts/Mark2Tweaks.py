##
## Mark2Plugin - Mark2Tweaks: Cura PostProcessingPlugin script for the Mark 2.
## Copyright (C) 2016,2017 Krys Lawrence
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as
## published by the Free Software Foundation, either version 3 of the
## License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##

"""Add-on script for nallath's PostProcessingPlugin to help the Mark 2.

See https://github.com/nallath/PostProcessingPlugin for details about the
plugin.

Put this script in PostProcessingPlugin's scripts folder.
"""


import sys
import re
from UM.Logger import Logger
from ..Script import Script


"""Convenience alias for UM.Logger.Logger.log."""
log = Logger.log


def layer_log(layer_num, message_type, message):
    """Log a message prefixed with the curent layer number."""
    log(message_type, layer_msg(layer_num, message))


def layer_msg(layer_num, message):
    """Return msg prefixed with the current layer number."""
    return 'Layer {:.0f}: {}'.format(layer_num, message)

def layer_assert(layer_num, condition, message):
    assert condition, layer_msg(layer_num, message)


class Mark2Tweaks(Script):
    """Optimize the G-code output for the Mark 2."""

    def getSettingDataString(self):
        """Return script identification and GUI options."""
        # Note: The "version" key is not this script's version, but the API
        # version of the PostProcessingPlugin.
        return '''\
          {
            "name": "Mark 2 Tweaks",
            "key": "Mark2Tweaks",
            "metadata": {},
            "version": 2,
            "settings": {
              "remove_superfluous": {
                "label": "Improve Tool Changes",
                "description":
                  "Remove superfluous movements after each tool change.  This can improve print quality by preventing materials from incorrectly touching immediately after a tool change.",
                "type": "bool",
                "default_value": true
              }
            }
          }'''

    def execute(self, data):
        """Process all G-code and apply selected tweaks."""
        log('d', '*** MARK 2 TWEAKS START ***')
        remove_superfluous = self.getSettingValueByKey('remove_superfluous')
        log('d', 'Remove Superfluous: {}'.format(remove_superfluous))
        for i, layer in enumerate(data):
            lines = layer.split('\n')
            layer_num = self.find_layer_num(lines)
            if layer_num is None:
                continue
            if remove_superfluous:
                self.remove_superfluous(layer_num, lines)
            data[i] = '\n'.join(lines)
        log('d', '*** MARK 2 TWEAKS END ***')
        return data

    def find_layer_num(self, lines):
        """Return the current layer number as a float."""
        result = self.find_line(lines, ';LAYER:', whole=False)
        if result is not None:
            return self.getValue(result, ";LAYER:")

    def remove_superfluous(self, layer_num, lines):
        """Remove superfluous G-code lines that the Mark 2 does not need."""
        # Copy of lines so lines can be deleted or inserted in loop
        for i, line in enumerate(lines[:]):
            if line in ('T0', 'T1'):
                try:
                    self.strip_cura_print_area_hack(layer_num, lines, i)
                except Exception as exception:
                    self.log_exception_as_warning(layer_num, exception)
                try:
                    self.collapse_post_tool_change_movements(
                      layer_num, lines, i)
                except Exception as exception:
                    self.log_exception_as_warning(layer_num, exception)

    def log_exception_as_warning(self, layer_num, exception):
        lineno = sys.exc_info()[-1].tb_lineno
        layer_log(layer_num, 'w', 'Line {}: {}'.format(lineno, exception))

    def strip_cura_print_area_hack(self, layer_num, lines, t_idx):
        """Remove TinkerGnome's Cura print area workaround line.

        If there is a G0 between M109 and G10, remove it.
        There should only be one.
        TinkerGnome says adding it was a hack/workaround so we can kill it.
        """
        m109_idx = self.find_line_index(lines, 'M109', start=t_idx)
        layer_assert(layer_num, m109_idx is not None,
          'Cannot find M109 after tool change.')
        layer_assert(layer_num, t_idx < m109_idx < t_idx + 20,
          'Sanity Check: M109 too far from {}'.format(lines[t_idx]))

        g10_idx = self.find_line_index(lines, 'G10', start=m109_idx)
        layer_assert(layer_num, g10_idx is not None,
          'Cannot find G10 after tool change.')
        layer_assert(layer_num, m109_idx < g10_idx < m109_idx + 5,
          'Sanity Check: G10 too far from M109')

        hack = self.find_line_and_index(lines, 'G0', ('X', 'Y', 'Z'),
          m109_idx+1, g10_idx)
        if hack is None:
            return
        hack_line, hack_idx = hack
        if (self.getValue(hack_line, 'Z') == 14
          and self.getValue(hack_line, 'Y') == 35):
            layer_log(layer_num, 'd', 'Striping Cura print area hack.')
            del lines[hack_idx]

    def collapse_post_tool_change_movements(self, layer_num, lines, t_idx):
        """Collapse any post tool change movents into a single movement.

        Any non-extrusion movements after tool change should be collapsed into
        a single line.  Keep only the last G0/G1 but add the F and Z of the
        first G0/G1.  But only collapse if there is more than one line.
        """
        extrude_idx = self.find_line_index(lines, ('G0', 'G1'), 'E', t_idx)
        layer_assert(layer_num, extrude_idx is not None,
          'Cannot find extruding G0/G1 line after tool change.')

        first_g = self.find_line_and_index(lines, ('G0', 'G1'), None, t_idx,
          extrude_idx)
        layer_assert(layer_num, first_g is not None,
          'Sanity Check: Could not find a G0/G1 line before the extrusion '
          'after tool change.')
        first_g_line, first_g_idx = first_g
        layer_assert(layer_num, first_g_idx < extrude_idx,
          'Sanity Check: First G0/G1 is >= to first extruding G0/G1.')

        f_value = self.getValue(first_g_line, 'F')
        z_value = self.getValue(first_g_line, 'Z')
        layer_assert(layer_num, z_value is not None,
          'Sanity Check: Z value not found in first G0/G1 line.')

        self.delete_all_g0_or_g1_except_last(layer_num, lines, first_g_idx,
          'Collapsing post tool change movements.')
        g_line = lines[first_g_idx]
        layer_assert(layer_num, self.is_g0_or_g1(g_line),
          'Sanity Check: Missing G0/G1 after collapse.')
        layer_assert(layer_num, not self.is_g0_or_g1(lines[first_g_idx+1]),
          'Sanity Check: More than one G0/G1 after collapse.')

        self.add_f_and_z_values(layer_num, lines, first_g_idx, z_value,
          f_value)
        layer_assert(layer_num, self.getValue(g_line, 'F') is not None,
          'Sanity Check: Missing required F value.')
        layer_assert(layer_num, self.getValue(g_line, 'Z') is not None,
          'Sanity Check: Missing required Z value.')

    def delete_all_g0_or_g1_except_last(self, layer_num, lines, first_g_idx,
      log_msg):
        """Delete all G0/G1 lines, except the last one.

        As long as there is more than one G line, delete the first.
        Subsequent G line indices move up by one == first_g_idx.
        This works only if lines are deleted and not just replaced.
        If only one G, never run.  Last G is not deleted.

        Also log only once if one or more deletes occurs.
        """
        has_logged = False
        while self.is_g0_or_g1(lines[first_g_idx+1]):
            if not has_logged:
                # Never log on single line.  Only log once if multiple lines.
                layer_log(layer_num, 'd', log_msg)
                has_logged = True
            del lines[first_g_idx]

    def is_g0_or_g1(self, line):
        return line.startswith('G0 ') or line.startswith('G1 ')

    def add_f_and_z_values(self, layer_num, lines, g_idx, z_value,
      f_value=None):
        """Add Z and F values to the indicated G0/G1 line.

        f_value is optional.
        Existing Z and F values will not be replaced.
        """
        line = lines[g_idx]
        fields = line.split(' ')
        if f_value is not None and self.getValue(line, 'F') is None:
            fields.insert(1, 'F{}'.format(f_value))
        if self.getValue(line, 'Z') is None:
            fields.append('Z{}'.format(z_value))
        lines[g_idx] = ' '.join(fields)

    def find_line(self, *args, **kwargs):
        """Return just the line from self.find_line_and_index()."""
        result = self.find_line_and_index(*args, **kwargs)
        if result is not None:
            return result[0]

    def find_line_index(self, *args, **kwargs):
        """Return just the index from self.find_line_and_index()."""
        result = self.find_line_and_index(*args, **kwargs)
        if result is not None:
            return result[1]

    def find_line_and_index(self, lines, commands, parameters=None, start=0,
      end=None, whole=True):
        """Find the first line in lines that matches the given criteria.

        lines:       The iterable of strings to search
        commands:    The command string (or iterable thereof) with which the
                     line must start.  If given an iterable (e.g. list), the
                     line can match *any* given command.
        parameters:  The parameter string (or iterable thereof) that the line
                     must contain.  Specifically, self.getValue() must return
                     a value.  If gien an iterable, the line must contain
                     *all* of the given parameters.  (Optional)
        start:       The index after which to search lines.  (Optional)
        end:         The index before witch to seach lines.  (Optional)
        whole:       If true, only match on whole commands.  If false, match
                     any command prefix. E.g. with whole=True, G1 will match
                     only G1 commands.  With whole=False, G1 would match G1 and
                     G10 commands, or even G1butterfly commands. :)  E.g. To
                     find all T<x> commands, use commands='T' and whole=False.

        Returns: The matching line string and its index in lines as a tuple, or
                 None if not match was found.
        """
        if isinstance(commands, str):
            commands = (commands,)
        if isinstance(parameters, str):
            parameters = (parameters,)
        if end is None:
            end = len(lines)
        for i, line in enumerate(lines[start:end], start):
            for command in commands:
                # Commands must be standalone, or there must be a space before
                # the first parameter.  This distinguise between G1 and G10,
                # for example.
                if (line == command
                  or line.startswith(command + (' ' if whole else ''))):
                    if parameters is None:
                        return line, i
                    else:
                        values = (self.getValue(line, p) for p in parameters)
                        values = (v for v in values if v is not None)
                        # Consume iterators/generators and force into sequences
                        if len(tuple(values)) == len(tuple(parameters)):
                            return line, i

    def getValue(self, line, key, default = None):
        """Replacement version of getValue that fixes a couple bugs.

        Specifically, it allows variable length keys and should support missing
        leading zeros on values < 1mm (e.g. X.45).  CuraEngine likes to emit
        those sometimes now. :(
        """
        key_pos = line.find(key)
        if key_pos == -1 or (';' in line and key_pos > line.find(';')):
            return default
        sub_part = line[key_pos + len(key):]
        m = re.search('^[0-9]*\.?[0-9]*', sub_part)
        if m is None:
            return default
        try:
            return float(m.group(0))
        except:
            return default
