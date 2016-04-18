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

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class API(object):

    @abc.abstractmethod
    def transaction(self, check_error=False, log_errors=True, **kwargs):
        """Create a transaction

        :param check_error: Allow the transaction to raise an exception?
        :type check_error:  bool
        :param log_errors:  Log an error if the transaction fails?
        :type log_errors:   bool
        :returns: A new transaction
        :rtype: :class:`Transaction`
        """

    @abc.abstractmethod
    def create_lswitch(self, name, may_exist=True):
        """Create a command to add an OVN lswitch

        :param name:      The id of the lswitch
        :type name:       string
        :param may_exist: Do not fail if lswitch already exists
        :type may_exist:  bool
        :returns:         :class:`Command` with no result
        """

    @abc.abstractmethod
    def set_lswitch_ext_id(self, name, ext_id):
        """Create a command to set OVN lswitch external id

        :param name:    The name of the lswitch
        :type name:     string
        :param ext_id:  The external id to set for the lswitch
        :type ext_id:   pair of <ext_id_key ,ext_id_value>
        :returns:       :class:`Command` with no result
        """

    @abc.abstractmethod
    def delete_lswitch(self, name=None, ext_id=None, if_exist=True):
        """Create a command to delete an OVN lswitch

        :param name:      The name of the lswitch
        :type name:       string
        :param ext_id:    The external id of the lswitch
        :type ext_id:     pair of <ext_id_key ,ext_id_value>
        :param if_exist:  Do not fail if the lswitch does not exists
        :type if_exist:   bool
        :returns:         :class:`Command` with no result
        """

    @abc.abstractmethod
    def create_lport(self, name, lswitch_name, may_exist=True):
        """Create a command to add an OVN lport

        :param name:         The name of the lport
        :type name:          string
        :param lswitch_name: The name of the lswitch the lport is created on
        :type lswitch_name:  string
        :param may_exist:    Do not fail if lport already exists
        :type may_exist:     bool
        :returns:            :class:`Command` with no result
        """

    @abc.abstractmethod
    def set_lport_ext_id(self, lport_name, ext_id):
        """Create a command to set OVN lport external id

        :param lport_name: The name of the lport
        :type lport_name:  string
        :param ext_id:     The external id to set for the lport
        :type ext_id:      pair of <ext_id_key ,ext_id_value>
        :returns:          :class:`Command` with no result
        """

    @abc.abstractmethod
    def set_lport_mac(self, lport_name, mac):
        """Create a command to set OVN lport MAC

        :param lport_name: The name of the lport
        :type lport_name:  string
        :param mac:        The MAC assigned to the lport
        :type mac:         string
        :returns:          :class:`Command` with no result
        """

    @abc.abstractmethod
    def delete_lport(self, name=None, ext_id=None, if_exist=True):
        """Create a command to delete an OVN lport

        :param name:      The name of the lport
        :type name:       string
        :param ext_id:    The external id of the lport
        :type ext_id:     pair of <ext_id_key ,ext_id_value>
        :param if_exist:  Do not fail if the lport does not exists
        :type if_exist:   bool
        :returns:         :class:`Command` with no result
        """

    @abc.abstractmethod
    def set_lport_up_status(self, lport_name, status):
        """Create a command to set OVN lport "up" status

        :param lport_name: The name of the lport
        :type lport_name:  string
        :param status:     The operational status of the lport
        :type status:      boolean (True or False)
        :returns:          :class:`Command` with no result
        """

    @abc.abstractmethod
    def create_acl_rule(self, lswitch_name, priority, match, action,
                        ext_ids_dict=None):
        """Create a command to add an OVN ACL rule

        :param lswitch_name: The name of the lswitch to create on
        :type lswitch_name:  string
        :param priority:     The priority of the rule
        :type priority:      integer (0..65535)
        :param match:        The ACL match expression
        :type match:         string
        :param action:       The ACL action in case of a match
        :type action:        string ("allow",
                             "allow-related", "drop", "reject")
        :param ext_id:       Dictionary of external id's of this rule
        :type ext_id:        Dictionary of [string]->string
        :returns:            :class:`Command` with no result
        """
