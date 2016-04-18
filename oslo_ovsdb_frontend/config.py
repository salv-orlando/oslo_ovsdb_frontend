#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_ovsdb_frontend._i18n import _

# NOTE: These classes are still missing from the source code tree
ovsdb_interface_map = {
    'vsctl': 'ovsdb_frontend.impl.OvsdbVsctl',
    'native': 'ovsdb_frontend.impl.OvsdbIdl',
}
ovndb_interface_map = {
    'native': 'ovsdb_frontend.impl.OvndbIdl'
}


OPTS = [
    cfg.StrOpt('ovsdb_interface',
               choices=interface_map.keys(),
               default='vsctl',
               help=_('The interface for interacting with the OVSDB')),
    cfg.StrOpt('ovsdb_connection',
               default='tcp:127.0.0.1:6640',
               help=_('The connection string for the native OVSDB backend. '
                      'Requires the native ovsdb_interface to be enabled.'))
]
cfg.CONF.register_opts(OPTS, 'OVS')
