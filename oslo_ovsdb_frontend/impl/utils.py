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

import collections
import uuid

import six


def ovn_name(id):
    # The name of the OVN entry will be neutron-<UUID>
    # This is due to the fact that the OVN application checks if the name
    # is a UUID. If so then there will be no matches.
    # We prefix the UUID to enable us to use the Neutron UUID when
    # updating, deleting etc.
    return 'neutron-%s' % id


def ovn_lrouter_port_name(id):
    # The name of the OVN lrouter port entry will be lrp-<UUID>
    # This is to distinguish with the name of the connected lswitch patch port,
    # which is named with neutron port uuid, so that OVS patch ports are
    # generated properly. The pairing patch port names will be:
    #   - patch-lrp-<UUID>-to-<UUID>
    #   - patch-<UUID>-to-lrp-<UUID>
    # lrp stands for Logical Router Port
    return 'lrp-%s' % id


def val_to_py(val):
    """Convert a json ovsdb return value to native python object"""
    if isinstance(val, collections.Sequence) and len(val) == 2:
        if val[0] == "uuid":
            return uuid.UUID(val[1])
        elif val[0] == "set":
            return [val_to_py(x) for x in val[1]]
        elif val[0] == "map":
            return {val_to_py(x): val_to_py(y) for x, y in val[1]}
    return val


def py_to_val(pyval):
    """Convert python value to ovs-vsctl value argument"""
    if isinstance(pyval, bool):
        return 'true' if pyval is True else 'false'
    elif pyval == '':
        return '""'
    else:
        return pyval


def set_colval_args(*col_values):
    args = []
    # TODO(twilson) This is ugly, but set/find args are very similar except for
    # op. Will try to find a better way to default this op to '='
    for entry in col_values:
        if len(entry) == 2:
            col, op, val = entry[0], '=', entry[1]
        else:
            col, op, val = entry
        if isinstance(val, collections.Mapping):
            args += ["%s:%s%s%s" % (
                col, k, op, py_to_val(v)) for k, v in val.items()]
        elif (isinstance(val, collections.Sequence)
                and not isinstance(val, six.string_types)):
            if len(val) == 0:
                args.append("%s%s%s" % (col, op, "[]"))
            else:
                args.append(
                    "%s%s%s" % (col, op, ",".join(map(py_to_val, val))))
        else:
            args.append("%s%s%s" % (col, op, py_to_val(val)))
    return args
