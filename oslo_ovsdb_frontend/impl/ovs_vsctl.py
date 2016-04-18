# Copyright (c) 2014 OpenStack Foundation
#
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

import itertools

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import excutils

from oslo_ovsdb_frontend._i18n import _LE
from oslo_ovsdb_frontend import api
from oslo_ovsdb_frontend.api import ovs
from oslo_ovsdb_frontend.impl import utils

LOG = logging.getLogger(__name__)


class Transaction(api.Transaction):
    def __init__(self, context, execute_func,
                 check_error=False, log_errors=True, opts=None):
        self.context = context
        self.check_error = check_error
        self.log_errors = log_errors
        self.opts = ["--timeout=%d" % self.context.vsctl_timeout,
                     '--oneline', '--format=json']
        if opts:
            self.opts += opts
        self.commands = []

    def add(self, command):
        self.commands.append(command)
        return command

    def commit(self):
        args = []
        for cmd in self.commands:
            cmd.result = None
            args += cmd.vsctl_args()
        res = self.run_vsctl(args)
        if res is None:
            return
        res = res.replace(r'\\', '\\').splitlines()
        for i, record in enumerate(res):
            self.commands[i].result = record
        return [cmd.result for cmd in self.commands]

    def run_vsctl(self, args):
        full_args = ["ovs-vsctl"] + self.opts + args
        try:
            # We log our own errors, so never have execute do it
            return self.execute_func(full_args, run_as_root=True,
                                     log_fail_as_error=False).rstrip()
        except Exception as e:
            with excutils.save_and_reraise_exception() as ctxt:
                if self.log_errors:
                    LOG.error(_LE("Unable to execute %(cmd)s. "
                                  "Exception: %(exception)s"),
                              {'cmd': full_args, 'exception': e})
                if not self.check_error:
                    ctxt.reraise = False


class BaseCommand(api.Command):
    def __init__(self, context, cmd, execute_func, opts=None, args=None):
        self.context = context
        self.cmd = cmd
        self.execute_func = execute_func
        self.opts = [] if opts is None else opts
        self.args = [] if args is None else args

    def execute(self, check_error=False, log_errors=True):
        with Transaction(self.context, self.execute_func,
                         check_error=check_error,
                         log_errors=log_errors) as txn:
            txn.add(self)
        return self.result

    def vsctl_args(self):
        return itertools.chain(('--',), self.opts, (self.cmd,), self.args)


class MultiLineCommand(BaseCommand):
    """Command for ovs-vsctl commands that return multiple lines"""
    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, raw_result):
        self._result = raw_result.split(r'\n') if raw_result else []


class DbCommand(BaseCommand):
    def __init__(self, context, cmd, execute_func,
                 opts=None, args=None, columns=None):
        if opts is None:
            opts = []
        if columns:
            opts += ['--columns=%s' % ",".join(columns)]
        super(DbCommand, self).__init__(context, cmd, execute_func,
                                        opts, args)

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, raw_result):
        # If check_error=False, run_vsctl can return None
        if not raw_result:
            self._result = None
            return

        try:
            json = jsonutils.loads(raw_result)
        except (ValueError, TypeError) as e:
            # This shouldn't happen, but if it does and we check_errors
            # log and raise.
            with excutils.save_and_reraise_exception():
                LOG.error(_LE("Could not parse: %(raw_result)s. "
                              "Exception: %(exception)s"),
                          {'raw_result': raw_result, 'exception': e})

        headings = json['headings']
        data = json['data']
        results = []
        for record in data:
            obj = {}
            for pos, heading in enumerate(headings):
                obj[heading] = utils.val_to_py(record[pos])
            results.append(obj)
        self._result = results


class DbGetCommand(DbCommand):
    @DbCommand.result.setter
    def result(self, val):
        # super()'s never worked for setters http://bugs.python.org/issue14965
        DbCommand.result.fset(self, val)
        # DbCommand will return [{'column': value}] and we just want value.
        if self._result:
            self._result = list(self._result[0].values())[0]


class BrExistsCommand(DbCommand):
    @DbCommand.result.setter
    def result(self, val):
        self._result = val is not None

    def execute(self):
        return super(BrExistsCommand, self).execute(check_error=False,
                                                    log_errors=False)


class OvsdbVsctl(ovs.API):

    def __init__(self, context, execute_func):
        super(OvsdbVsctl, self).__init__(context)
        self.execute_func = execute_func

    def transaction(self, check_error=False, log_errors=True, **kwargs):
        return Transaction(self.context, self.execute_func,
                           check_error, log_errors, **kwargs)

    def add_br(self, name, may_exist=True, datapath_type=None):
        opts = ['--may-exist'] if may_exist else None
        params = [name]
        if datapath_type:
            params += ['--', 'set', 'Bridge', name,
                       'datapath_type=%s' % datapath_type]
        return BaseCommand(self.context, 'add-br', self.execute_func,
                           opts, params)

    def del_br(self, name, if_exists=True):
        opts = ['--if-exists'] if if_exists else None
        return BaseCommand(self.context, 'del-br', self.execute_func,
                           opts, [name])

    def br_exists(self, name):
        return BrExistsCommand(self.context, 'list', self.execute_func,
                               args=['Bridge', name])

    def port_to_br(self, name):
        return BaseCommand(self.context, 'port-to-br', self.execute_func,
                           args=[name])

    def iface_to_br(self, name):
        return BaseCommand(self.context, 'iface-to-br', self.execute_func,
                           args=[name])

    def list_br(self):
        return MultiLineCommand(self.context, 'list-br', self.execute_func)

    def br_get_external_id(self, name, field):
        return BaseCommand(self.context, 'br-get-external-id',
                           self.execute_func, args=[name, field])

    def db_create(self, table, **col_values):
        args = [table]
        args += utils.set_colval_args(*col_values.items())
        return BaseCommand(self.context, 'create', self.execute_func,
                           args=args)

    def db_destroy(self, table, record):
        args = [table, record]
        return BaseCommand(self.context, 'destroy', self.execute_func,
                           args=args)

    def db_set(self, table, record, *col_values):
        args = [table, record]
        args += utils.set_colval_args(*col_values)
        return BaseCommand(self.context, 'set', self.execute_func,
                           args=args)

    def db_clear(self, table, record, column):
        return BaseCommand(self.context, 'clear', self.execute_func,
                           args=[table, record, column])

    def db_get(self, table, record, column):
        # Use the 'list' command as it can return json and 'get' cannot so that
        # we can get real return types instead of treating everything as string
        # NOTE: openvswitch can return a single atomic value for fields that
        # are sets, but only have one value. This makes directly iterating over
        # the result of a db_get() call unsafe.
        return DbGetCommand(self.context, 'list', self.execute_func,
                            args=[table, record], columns=[column])

    def db_list(self, table, records=None, columns=None, if_exists=False):
        opts = ['--if-exists'] if if_exists else None
        args = [table]
        if records:
            args += records
        return DbCommand(self.context, 'list', self.execute_func,
                         opts=opts, args=args, columns=columns)

    def db_find(self, table, *conditions, **kwargs):
        columns = kwargs.pop('columns', None)
        args = itertools.chain([table],
                               *[utils.set_colval_args(c)
                                 for c in conditions])
        return DbCommand(self.context, 'find', self.execute_func,
                         args=args, columns=columns)

    def set_controller(self, bridge, controllers):
        return BaseCommand(self.context, 'set-controller', self.execute_func,
                           args=[bridge] + list(controllers))

    def del_controller(self, bridge):
        return BaseCommand(self.context, 'del-controller', self.execute_func,
                           args=[bridge])

    def get_controller(self, bridge):
        return MultiLineCommand(self.context, 'get-controller',
                                self.execute_func, args=[bridge])

    def set_fail_mode(self, bridge, mode):
        return BaseCommand(self.context, 'set-fail-mode',
                           self.execute_func,
                           args=[bridge, mode])

    def add_port(self, bridge, port, may_exist=True):
        opts = ['--may-exist'] if may_exist else None
        return BaseCommand(self.context, 'add-port',
                           self.execute_func,
                           opts, [bridge, port])

    def del_port(self, port, bridge=None, if_exists=True):
        opts = ['--if-exists'] if if_exists else None
        args = filter(None, [bridge, port])
        return BaseCommand(self.context, 'del-port',
                           self.execute_func, opts, args)

    def list_ports(self, bridge):
        return MultiLineCommand(self.context, 'list-ports',
                                self.execute_func, args=[bridge])

    def list_ifaces(self, bridge):
        return MultiLineCommand(self.context, 'list-ifaces',
                                self.execute_func, args=[bridge])
