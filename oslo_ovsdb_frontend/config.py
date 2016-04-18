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

from oslo_config import cfg

from oslo_ovsdb_frontend._i18n import _

# NOTE: These classes are still missing from the source code tree
ovsdb_interface_map = {
    'vsctl': 'ovsdb_frontend.impl.OvsdbVsctl',
    'native': 'ovsdb_frontend.impl.OvsdbIdl',
}
ovndb_interface_map = {
    'native': 'ovsdb_frontend.impl.OvndbIdl'
}


# Default timeout for ovs-vsctl command
DEFAULT_OVS_VSCTL_TIMEOUT = 10
ovs_opts = [
    cfg.StrOpt('ovsdb_interface',
               choices=ovsdb_interface_map.keys(),
               default='vsctl',
               help=_('The interface for interacting with the OVSDB')),
    cfg.StrOpt('ovsdb_connection',
               default='tcp:127.0.0.1:6640',
               help=_('The connection string for the native OVSDB backend. '
                      'Requires the native ovsdb_interface to be enabled.')),
    cfg.IntOpt('ovs_vsctl_timeout',
               default=DEFAULT_OVS_VSCTL_TIMEOUT,
               help=_('Timeout in seconds for ovs-vsctl commands. '
                      'If the timeout expires, ovs commands will fail with '
                      'ALARMCLOCK error.'))
]
cfg.CONF.register_opts(ovs_opts, 'OVS')

ovn_opts = [
    cfg.StrOpt('ovsdb_connection',
               default='tcp:127.0.0.1:6640',
               help=_('The connection string for the native OVSDB backend')),
    cfg.IntOpt('ovsdb_connection_timeout',
               default=60,
               help=_('Timeout in seconds for the OVSDB '
                      'connection transaction')),
    cfg.StrOpt('neutron_sync_mode',
               default='log',
               choices=('off', 'log', 'repair'),
               help=_('The synchronization mode of OVN with Neutron DB. \n'
                      'off - synchronization is off \n'
                      'log - during neutron-server startup, '
                      'check to see if OVN is in sync with '
                      'the Neutron database. '
                      ' Log warnings for any inconsistencies found so'
                      ' that an admin can investigate \n'
                      'repair - during neutron-server startup, automatically'
                      ' create resources found in Neutron but not in OVN.'
                      ' Also remove resources from OVN'
                      ' that are no longer in Neutron.')),
    cfg.StrOpt("vhost_sock_dir",
               default="/var/run/openvswitch",
               help=_("The directory in which vhost virtio socket "
                      "is created by all the vswitch daemons"))
]

cfg.CONF.register_opts(ovn_opts, group='ovn')


def get_ovn_ovsdb_connection():
    return cfg.CONF.ovn.ovsdb_connection


def get_ovn_ovsdb_timeout():
    return cfg.CONF.ovn.ovsdb_connection_timeout
