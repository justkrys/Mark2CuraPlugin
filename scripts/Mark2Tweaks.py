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

from UM.Logger import Logger
from ..Script import Script


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
              "airspeed": {
                "label": "Airspeed",
                "description":
                  "What is the air speed velocity of an unladden swallow?",
                "unit": "m/s",
                "type": "float",
                "default_value": 11.0
              }
            }
          }'''

    def execute(self, data):
        airspeed = self.getSettingValueByKey('airspeed')
        data = [';AIRSPEED: {}\n'.format(airspeed)] + data
        for i, layer in enumerate(data):
            lines = layer.split('\n')
            for line in lines:
                Logger.log('d', 'MARK2: {}'.format(line))
        return data

