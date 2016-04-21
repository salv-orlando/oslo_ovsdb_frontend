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

import six

from oslo_ovsdb_frontend._i18n import _
from oslo_ovsdb_frontend.api import ovn as ovn_api
from oslo_ovsdb_frontend import config as cfg
from oslo_ovsdb_frontend.impl.native import connection
from oslo_ovsdb_frontend.impl.native import idlutils
from oslo_ovsdb_frontend.impl import ovn_commands as cmd
from oslo_ovsdb_frontend.impl import ovs_native
from oslo_ovsdb_frontend.impl import ovsdb_monitor
from oslo_ovsdb_frontend.impl import utils

OVN_NETWORK_NAME_EXT_ID_KEY = 'neutron:network_name'
OVN_PORT_NAME_EXT_ID_KEY = 'neutron:port_name'


class OvsdbOvnIdl(ovn_api.API):

    ovsdb_connection = None

    def __init__(self, event_callbacks=None):
        super(OvsdbOvnIdl, self).__init__()
        if event_callbacks:
            conn_cls = ovsdb_monitor.OvnConnection
        else:
            conn_cls = connection.Connection
        if OvsdbOvnIdl.ovsdb_connection is None:
            OvsdbOvnIdl.ovsdb_connection = conn_cls(
                cfg.get_ovn_ovsdb_connection(),
                cfg.get_ovs_ovsdb_timeout(),
                'OVN_Northbound')
        if isinstance(OvsdbOvnIdl.ovsdb_connection,
                      ovsdb_monitor.OvnConnection):
            OvsdbOvnIdl.ovsdb_connection.start(event_callbacks)
        else:
            OvsdbOvnIdl.ovsdb_connection.start()
        self.idl = OvsdbOvnIdl.ovsdb_connection.idl
        self.ovsdb_timeout = cfg.get_ovn_ovsdb_timeout()

    @property
    def _tables(self):
        return self.idl.tables

    def transaction(self, check_error=False, log_errors=True, **kwargs):
        return ovs_native.Transaction(self,
                                      OvsdbOvnIdl.ovsdb_connection,
                                      self.ovsdb_timeout,
                                      check_error, log_errors)

    def create_lswitch(self, lswitch_name, may_exist=True, **columns):
        return cmd.AddLSwitchCommand(self, lswitch_name,
                                     may_exist, **columns)

    def delete_lswitch(self, lswitch_name=None, ext_id=None, if_exists=True):
        if lswitch_name is not None:
            return cmd.DelLSwitchCommand(self, lswitch_name, if_exists)
        else:
            raise RuntimeError(_("Currently only supports delete "
                                 "by lswitch-name"))

    def set_lswitch_ext_id(self, lswitch_id, ext_id, if_exists=True):
        return cmd.LSwitchSetExternalIdCommand(self, lswitch_id,
                                               ext_id[0], ext_id[1],
                                               if_exists)

    def create_lport(self, lport_name, lswitch_name, may_exist=True,
                     **columns):
        return cmd.AddLogicalPortCommand(self, lport_name, lswitch_name,
                                         may_exist, **columns)

    def set_lport(self, lport_name, if_exists=True, **columns):
        return cmd.SetLogicalPortCommand(self, lport_name,
                                         if_exists, **columns)

    def delete_lport(self, lport_name=None, lswitch=None,
                     ext_id=None, if_exists=True):
        if lport_name is not None:
            return cmd.DelLogicalPortCommand(self, lport_name,
                                             lswitch, if_exists)
        else:
            raise RuntimeError(_("Currently only supports "
                                 "delete by lport-name"))

    def get_all_logical_switches_ids(self):
        result = {}
        for row in self._tables['Logical_Switch'].rows.values():
            result[row.name] = row.external_ids
        return result

    def get_logical_switch_ids(self, lswitch_name):
        for row in self._tables['Logical_Switch'].rows.values():
            if row.name == lswitch_name:
                return row.external_ids
        return {}

    def get_all_logical_ports_ids(self):
        result = {}
        for row in self._tables['Logical_Port'].rows.values():
            result[row.name] = row.external_ids
        return result

    def get_all_logical_switches_with_ports(self, lswitch_key, lport_key):
        """Retrieve logical ports from a given logical switch.

        :param lswitch_key: Tag in external ids for lswitches to look for
        :param lport_key: Tag in external ids for logical ports to look for
        """
        result = []
        for lswitch in self._tables['Logical_Switch'].rows.values():
            if lswitch_key not in lswitch.external_ids:
                continue
            ports = []
            for lport in getattr(lswitch, 'ports', []):
                if lport_key in lport.external_ids:
                    ports.append(lport.name)
            result.append({'name': lswitch.name,
                           'ports': ports})
        return result

    def get_acls_for_lswitches(self, lswitch_names):
        """Get the existing set of acls that belong to the logical switches

        @param lswitch_names: List of logical switch names
        @type lswitch_names: []
        @var acl_values_dict: A dictionary indexed by port_id containing the
                              list of acl values in string format that belong
                              to that port
        @var acl_obj_dict: A dictionary indexed by acl value containing the
                           corresponding acl idl object.
        @var lswitch_ovsdb_dict: A dictionary mapping from logical switch
                                 name to lswitch idl object
        @return: (acl_values_dict, acl_obj_dict, lswitch_ovsdb_dict)
        """
        acl_values_dict = {}
        acl_obj_dict = {}
        lswitch_ovsdb_dict = {}
        for lswitch_name in lswitch_names:
            try:
                lswitch = idlutils.row_by_value(self.idl,
                                                'Logical_Switch',
                                                'name',
                                                utils.ovn_name(lswitch_name))
            except idlutils.RowNotFound:
                # It is possible for the logical switch to be deleted
                # while we are searching for it by name in idl.
                continue
            lswitch_ovsdb_dict[lswitch_name] = lswitch
            acls = getattr(lswitch, 'acls', [])

            # Iterate over each acl in a lswitch and store the acl in
            # a key:value representation for e.g. acl_string. This
            # key:value representation can invoke the code -
            # self._ovn.add_acl(**acl_string)
            for acl in acls:
                ext_ids = getattr(acl, 'external_ids', {})
                port_id = ext_ids.get('neutron:lport')
                acl_list = acl_values_dict.setdefault(port_id, [])
                acl_string = {'lport': port_id,
                              'lswitch': utils.ovn_name(lswitch_name)}
                for acl_key in six.iterkeys(getattr(acl, "_data", {})):
                    try:
                        acl_string[acl_key] = getattr(acl, acl_key)
                    except AttributeError:
                        pass
                acl_obj_dict[str(acl_string)] = acl
                acl_list.append(acl_string)
        return acl_values_dict, acl_obj_dict, lswitch_ovsdb_dict

    def create_lrouter(self, name, may_exist=True, **columns):
        return cmd.AddLRouterCommand(self, name,
                                     may_exist, **columns)

    def update_lrouter(self, name, if_exists=True, **columns):
        return cmd.UpdateLRouterCommand(self, name,
                                        if_exists, **columns)

    def delete_lrouter(self, name, if_exists=True):
        return cmd.DelLRouterCommand(self, name, if_exists)

    def add_lrouter_port(self, name, lrouter, **columns):
        return cmd.AddLRouterPortCommand(self, name, lrouter, **columns)

    def delete_lrouter_port(self, name, lrouter, if_exists=True):
        return cmd.DelLRouterPortCommand(self, name, lrouter,
                                         if_exists)

    def set_lrouter_port_in_lport(self, lport, lrouter_port):
        return cmd.SetLRouterPortInLPortCommand(self, lport, lrouter_port)

    def add_acl(self, lswitch, lport, **columns):
        return cmd.AddACLCommand(self, lswitch, lport, **columns)

    def delete_acl(self, lswitch, lport, if_exists=True):
        return cmd.DelACLCommand(self, lswitch, lport, if_exists)

    def update_acls(self, lswitch_names, port_list, acl_new_values_dict,
                    need_compare=True, is_add_acl=True):
        return cmd.UpdateACLsCommand(self, lswitch_names,
                                     port_list, acl_new_values_dict,
                                     need_compare=need_compare,
                                     is_add_acl=is_add_acl)
