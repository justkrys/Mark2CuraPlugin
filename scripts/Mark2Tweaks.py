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

import re
from UM.Logger import Logger
from ..Script import Script


"""Convenience alias for UM.Logger.Logger.log."""
log = Logger.log


def layer_log(layer_num, msg_type, msg):
    """Log a message prefixed with the curent layer number."""
    log(msg_type, layer_msg(layer_num, msg))


def layer_msg(layer_num, msg):
    """Return msg prefixed with the current layer number."""
    return 'Layer {:.0f}: {}'.format(layer_num, msg)


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
                self.strip_cura_print_area_hack(layer_num, lines, i)
                self.collapse_post_tool_change_movements(layer_num, lines, i)

    def strip_cura_print_area_hack(self, layer_num, lines, tx_idx):
        """Remove TinkerGnome's Cura print area workaround line.

        If there is a G0 between M109 and G10, remove it.
        There should only be one.
        TinkerGnome says adding it was a hack/workaround so we can kill it.
        """
        m109_idx = self.find_line_index(lines, 'M109', start=tx_idx)
        assert(m109_idx is not None, layer_msg(layer_num,
          'Cannot find M109 after tool change.'))
        assert(tx_idx < m109_idx < tx_idx + 20, layer_msg(layer_num,
          'Sanity Check, M109 too far from {}'.format(lines[tx_idx])))
        g10_idx = self.find_line_index(lines, 'G10', start=m109_idx)
        assert(g10_idx is not None, layer_msg(layer_num,
          'Cannot find G10 after tool change.'))
        assert(m109_idx < g10_idx < m109_idx + 5, layer_msg(layer_num,
          'Sanity Check, G10 too far from M109'))
        hack = self.find_line_and_index(lines, 'G0', ('X', 'Y', 'Z'),
          m109_idx+1, g10_idx)
        if hack is None: return
        hack_line, hack_idx = hack
        if (self.getValue(hack_line, 'Z') == 14
          and self.getValue(hack_line, 'Y') == 35):
            layer_log(layer_num, 'd', 'Striping Cura Print Area Hack.')
            del lines[hack_idx]

    def collapse_post_tool_change_movements(self, layer_num, lines, tx_idx):
        """Collapse any post tool change movents into a single movement.

        Any non-extrusion movements after tool change should be collapsed into
        a single line.  Keep only the last G0/G1 but add the F and Z of the
        first G0/G1.  But only collapse if there is more than one line.
        """
        extrude_idx = self.find_line_index(lines, ('G0', 'G1'), 'E', tx_idx)
        assert(extrude_idx is not None, layer_msg(layer_num,
          'Cannot find extruding movement after tool change.'))
        first_g_line, first_g_idx = self.find_line_and_index(lines, ('G0',
          'G1'), None, tx_idx, extrude_idx)
        f_value = self.getValue(first_g_line, 'F')
        z_value = self.getValue(first_g_line, 'Z')

        layer_log(layer_num, 'w', '{} {}'.format(f_value, z_value))

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
