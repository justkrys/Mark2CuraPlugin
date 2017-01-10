##
## Mark2Plugin - Mark2Tweaks: Cura Post Processing script for the Mark 2 mod.
## Copyright (C) 2016 Krys Lawrence
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

import re
from UM.Logger import Logger
from ..Script import Script


log = Logger.log  # Alias for convenience


def layer_log(layer_num, msg_type, msg):
    log(msg_type, layer_msg(layer_num, msg))


def layer_msg(layer_num, msg):
    return 'Layer {:.0f}: {}'.format(layer_num, msg)


class Mark2Tweaks(Script):

    # Note: "version" key is not script version, but API version of
    # PostProcessingPlugin.
    def getSettingDataString(self):
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
        result = self.find_next_line_starting_with(lines, 0, ';LAYER:')
        return self.getValue(result[1], ";LAYER:") if result else result

    def remove_superfluous(self, layer_num, lines):
        # Copy of lines so lines can be deleted or inserted in loop
        for i, line in enumerate(lines[:]):
            if line in ('T0', 'T1'):
                self.strip_cura_print_area_hack(layer_num, lines, i)

    def strip_cura_print_area_hack(self, layer_num, lines, tx_idx):
        # If there are any G0 between M109 and G10, remove them.
        # There should only be one.
        # TinkerGnome says adding it was a hack/workaround so we can kill it.
        # Also trying to be somewhat flexible.
        m109_idx = self.find_next_line_starting_with(lines, tx_idx, 'M109')[0]
        assert(
          m109_idx < tx_idx + 20,
          layer_msg(
            layer_num,
            'Sanity Check, M109 far from {}'.format(lines[tx_idx])
          )
        )
        g10_idx = self.find_next_line_starting_with(lines, m109_idx, 'G10')[0]
        assert(
          g10_idx < m109_idx + 20,
          layer_msg(layer_num, 'Sanity Check, G10 far from M109')
        )
        # Subset copy. So we can modify original lines list.
        for i, line in enumerate(lines[m109_idx + 1:g10_idx]):
            if (
              line.startswith('G0')
              and self.getValue(line, 'Z') == 14
              and self.getValue(line, 'Y') == 35
            ):
                layer_log(layer_num, 'd', 'Striping Cura Print Area Hack.')
                del lines[m109_idx + 1 + i]

    def find_next_line_starting_with(self, lines, start, key):
        for i, line in enumerate(lines[start:]):
            if line.startswith(key):
                return start + i, line

    ## Replacement version of getValue that fixes a couple bugs.
    ## Specifically, it allows variable length keys and should support missing
    ## leading zeros on values < 1mm (e.g. X.45).  CuraEngine likes to emit
    ## those now. :(
    def getValue(self, line, key, default = None):
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
