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
        layer_num = None
        for layer in data:
            lines = layer.split('\n')
            layer_num = self.find_layer_num(lines)
            if not layer_num:
                continue
            if remove_superfluous:
                self.remove_superfluous(layer_num, lines)
        log('d', '*** MARK 2 TWEAKS END ***')
        return data

    def find_layer_num(self, lines):
        for line in lines:
            if line.startswith(';LAYER:'):
                return self.getValue(line, ";LAYER:")
    
    def remove_superfluous(self, layer_num, lines):
        for line in lines[:]:  # Copy of lines so ines can be modified in loop
            if line in ('T0', 'T1'):
                log('d', 'Tool change in layer {:.0f}'.format(layer_num))

    ## Replacement version of getValue that fixes a couple bugs.
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

