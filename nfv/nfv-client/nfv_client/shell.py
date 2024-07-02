#
# Copyright (c) 2016-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import argparse
import os
from six.moves import urllib
import sys

from nfv_client import sw_update


REGISTERED_STRATEGIES = {}


def _process_exit(error):
    print(error)
    sys.exit(1)


def register_strategy(cmd_area, strategy_name):
    """
    Registers a parser command with an update strategy name

    :param cmd_area: the parser command to register
    :param strategy_name: the strategy to associate with this parser
    """
    REGISTERED_STRATEGIES[cmd_area] = strategy_name


def get_strategy_name(cmd_area):
    """
    Determines the strategy name for a parser command

    :param cmd_area: the parser command to lookup
    :returns: the strategy name associated with the parser
    :raises: ValueError if the parser was never registered
    """
    strategy_name = REGISTERED_STRATEGIES.get(cmd_area, None)
    if strategy_name is None:
        raise ValueError("Unknown command area, %s, given" % cmd_area)
    return strategy_name


def get_extra_create_args(cmd_area, args):
    """
    Return the extra create arguments supported by a strategy type

    :param cmd_area: the strategy that supports additional create arguments
    :param args: the parsed arguments to extract the additional fields from
    :returns: a dictionary of additional kwargs for the create_strategy command
    :raises: ValueError if a strategy has been registered but not update here
    """
    if sw_update.CMD_NAME_SW_PATCH == cmd_area:
        # no additional kwargs for patch
        return {}
    elif sw_update.CMD_NAME_SW_DEPLOY == cmd_area:
        # We can't use mutual exclusion for release and rollback because
        # release is a positional arg.
        if args.release is None and not args.rollback:
            raise ValueError("Must set release or rollback")
        elif args.release is not None and args.rollback:
            raise ValueError("Cannot set both release and rollback")
        return {
            'release': args.release,
            'rollback': args.rollback
        }
    elif sw_update.CMD_NAME_FW_UPDATE == cmd_area:
        # no additional kwargs for firmware update
        return {}
    elif sw_update.CMD_NAME_SYSTEM_CONFIG_UPDATE == cmd_area:
        # no additional kwargs for system config update
        return {}
    elif sw_update.CMD_NAME_KUBE_ROOTCA_UPDATE == cmd_area:
        # kube rootca update supports expiry_date, subject and cert_file
        return {
            'expiry_date': args.expiry_date,
            'subject': args.subject,
            'cert_file': args.cert_file
        }
    elif sw_update.CMD_NAME_KUBE_UPGRADE == cmd_area:
        # kube upgrade supports: to_version
        return {'to_version': args.to_version}
    else:
        raise ValueError("Unknown command area, %s, given" % cmd_area)


def add_list_arg(some_cmd, some_arg, some_list):
    """
    Adds an argument to a command accepting a list of valid values.

    :param some_cmd: a command parser object that is adding a new argument
    :param some_arg: a string indicating the new argument. ex: --foo
    :param some_list: a list of valid values for the argument.

    The list cannot be empty.  The first item in the list is the default
    """
    default = some_list[0]
    some_cmd.add_argument(some_arg,
                          default=default,
                          choices=some_list,
                          help='defaults to ' + default)


def setup_abort_cmd(parser):
    """
    Sets up an 'abort' command for a strategy command parser.

    ex: sw-manager patch-strategy abort <some args>

    :param parser: the strategy parser to add the create command to.
    """
    abort_cmd = parser.add_parser('abort',
                                  help='Abort a strategy')
    abort_cmd.set_defaults(cmd='abort')
    abort_cmd.add_argument('--stage-id',
                           help='stage identifier to abort')
    return abort_cmd


def setup_apply_cmd(parser):
    """
    Sets up an 'apply' command for a strategy command parser.

    ex: sw-manager patch-strategy apply <some args>

    :param parser: the strategy parser to register the command under
    """
    apply_cmd = parser.add_parser('apply',
                                  help='Apply a strategy')
    apply_cmd.set_defaults(cmd='apply')
    apply_cmd.add_argument('--stage-id',
                           default=None,
                           help='stage identifier to apply')
    return apply_cmd


def setup_create_cmd(parser,
                     controller_types,
                     storage_types,
                     worker_types,
                     instance_actions,
                     alarm_restrictions,
                     min_parallel=1,
                     max_parallel=5):
    """
    Sets up a 'create' command for a strategy command parser.

    ex: sw-manager patch-strategy create <some args>

    :param parser: the strategy parser to register the command under
    :param controller_types: list of the valid apply types for controller
    :param storage_types: list of the valid apply types for storage
    :param worker_types: list of the valid apply types for worker
    :param instance_actions: list of valid VM actions during worker apply
    :param alarm_restrictions: list of valid alarm restrictions
    :param min_parallel: minimum value (inclusive) for updating parallel hosts
    :param max_parallel: maximum value (inclusive) for updating parallel hosts

    The lists cannot be empty.  The first item in the lists is the default
    """
    create_cmd = parser.add_parser('create', help='Create a strategy')
    create_cmd.set_defaults(cmd='create')

    add_list_arg(create_cmd, '--controller-apply-type', controller_types)
    add_list_arg(create_cmd, '--storage-apply-type', storage_types)
    add_list_arg(create_cmd, '--worker-apply-type', worker_types)
    add_list_arg(create_cmd, '--instance-action', instance_actions)
    add_list_arg(create_cmd, '--alarm-restrictions', alarm_restrictions)
    create_cmd.add_argument('--max-parallel-worker-hosts',
                            type=int,
                            choices=list(range(min_parallel, max_parallel + 1)),
                            help='maximum worker hosts to update in parallel')

    return create_cmd


def setup_delete_cmd(parser):
    """
    Sets up a 'delete' command for a strategy command parser.

    ex: sw-manager patch-strategy delete <some args>

    :param parser: the strategy parser to register the command under
    """
    delete_cmd = parser.add_parser('delete', help='Delete a strategy')
    delete_cmd.set_defaults(cmd='delete')
    delete_cmd.add_argument('--force',
                            action='store_true',
                            help=argparse.SUPPRESS)
    return delete_cmd


def setup_show_cmd(parser):
    """
    Sets up a 'show' command for a strategy command parser.

    ex: sw-manager patch-strategy show <some args>

    :param parser: the strategy parser to register the command under
    """
    show_cmd = parser.add_parser('show', help='Show a strategy')
    show_cmd.set_defaults(cmd='show')
    show_cmd.add_argument('--details',
                          action='store_true',
                          help='show strategy details')
    show_cmd.add_argument('--active',
                          action='store_true',
                          help='show currently active strategy step')
    show_cmd.add_argument('--error-details',
                          action='store_true',
                          help='show error details of failed strategy step')
    return show_cmd


def setup_fw_update_parser(commands):
    """Firmware Update Strategy Commands"""

    cmd_area = sw_update.CMD_NAME_FW_UPDATE
    register_strategy(cmd_area, sw_update.STRATEGY_NAME_FW_UPDATE)
    cmd_parser = commands.add_parser(cmd_area,
                                     help='Firmware Update Strategy')
    cmd_parser.set_defaults(cmd_area=cmd_area)

    sub_cmds = cmd_parser.add_subparsers(title='Firmware Update Commands',
                                         metavar='')
    sub_cmds.required = True

    # define the create command
    # alarm restrictions, defaults to strict
    _ = setup_create_cmd(
        sub_cmds,
        [sw_update.APPLY_TYPE_IGNORE],  # controller supports ignore
        [sw_update.APPLY_TYPE_IGNORE],  # storage supports ignore
        [sw_update.APPLY_TYPE_SERIAL,  # worker supports serial and parallel
         sw_update.APPLY_TYPE_PARALLEL,
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.INSTANCE_ACTION_STOP_START,  # instance actions
         sw_update.INSTANCE_ACTION_MIGRATE],
        [sw_update.ALARM_RESTRICTIONS_STRICT,  # alarm restrictions
         sw_update.ALARM_RESTRICTIONS_RELAXED],
        min_parallel=2,
        max_parallel=5  # fw update supports 2..5 workers in parallel
    )
    # There are no additional create options for firmware update

    # define the delete command
    _ = setup_delete_cmd(sub_cmds)
    # define the apply command
    _ = setup_apply_cmd(sub_cmds)
    # define the abort command
    _ = setup_abort_cmd(sub_cmds)
    # define the show command
    _ = setup_show_cmd(sub_cmds)


def setup_kube_rootca_update_parser(commands):
    """Kubernetes RootCA Update Strategy Commands"""

    cmd_area = sw_update.CMD_NAME_KUBE_ROOTCA_UPDATE
    register_strategy(cmd_area, sw_update.STRATEGY_NAME_KUBE_ROOTCA_UPDATE)
    cmd_parser = commands.add_parser(cmd_area,
                                     help='Kubernetes RootCA Update Strategy')
    cmd_parser.set_defaults(cmd_area=cmd_area)

    sub_cmds = cmd_parser.add_subparsers(
        title='Kubernetes RootCA Update Commands',
        metavar='')
    sub_cmds.required = True

    # define the create command
    create_strategy_cmd = setup_create_cmd(
        sub_cmds,
        [sw_update.APPLY_TYPE_SERIAL,  # controller supports serial only
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # storage supports serial only
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # worker supports serial and parallel
         sw_update.APPLY_TYPE_PARALLEL,
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.INSTANCE_ACTION_STOP_START,  # instance actions
         sw_update.INSTANCE_ACTION_MIGRATE],
        [sw_update.ALARM_RESTRICTIONS_STRICT,  # alarm restrictions
         sw_update.ALARM_RESTRICTIONS_RELAXED],
        min_parallel=2,
        max_parallel=10  # kube rootca update support 2..10 workers in parallel
    )
    # add specific arguments to the create command for kube root ca update
    # The get_extra_create_args method is updated to align with these
    create_strategy_cmd.add_argument(
        '--expiry-date',
        required=False,
        help='When the generated certificate should expire (yyyy-mm-dd)')
    create_strategy_cmd.add_argument(
        '--subject',
        required=False,
        help='Subject for the generated certificate')
    create_strategy_cmd.add_argument(
        '--cert-file',
        required=False,
        help='Path to a file to be used, otherwise system will generate one')

    # define the delete command
    _ = setup_delete_cmd(sub_cmds)
    # define the apply command
    _ = setup_apply_cmd(sub_cmds)
    # define the abort command
    _ = setup_abort_cmd(sub_cmds)
    # define the show command
    _ = setup_show_cmd(sub_cmds)


def setup_kube_upgrade_parser(commands):
    """Kubernetes Upgrade Strategy Commands"""

    cmd_area = sw_update.CMD_NAME_KUBE_UPGRADE
    register_strategy(cmd_area, sw_update.STRATEGY_NAME_KUBE_UPGRADE)
    cmd_parser = commands.add_parser(cmd_area,
                                     help='Kubernetes Upgrade Strategy')
    cmd_parser.set_defaults(cmd_area=cmd_area)

    sub_cmds = cmd_parser.add_subparsers(title='Kubernetes Upgrade Commands',
                                         metavar='')
    sub_cmds.required = True

    # define the create command
    create_strategy_cmd = setup_create_cmd(
        sub_cmds,
        [sw_update.APPLY_TYPE_SERIAL,  # controller supports serial only
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # storage supports serial only
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # worker supports serial and parallel
         sw_update.APPLY_TYPE_PARALLEL,
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.INSTANCE_ACTION_STOP_START,  # instance actions
         sw_update.INSTANCE_ACTION_MIGRATE],
        [sw_update.ALARM_RESTRICTIONS_STRICT,  # alarm restrictions
         sw_update.ALARM_RESTRICTIONS_RELAXED],
        min_parallel=2,
        max_parallel=10  # kube upgrade supports 2..10 workers in parallel
    )

    # add kube specific arguments to the create command
    # The get_extra_create_args method is updated to align with these
    # kube upgrade create requires 'to-version'
    create_strategy_cmd.add_argument(
        '--to-version',
        required=True,
        help='The kubernetes version')

    # define the delete command
    _ = setup_delete_cmd(sub_cmds)
    # define the apply command
    _ = setup_apply_cmd(sub_cmds)
    # define the abort command
    _ = setup_abort_cmd(sub_cmds)
    # define the show command
    _ = setup_show_cmd(sub_cmds)


def setup_patch_parser(commands):
    """Patch Strategy Commands"""

    cmd_area = sw_update.CMD_NAME_SW_PATCH
    register_strategy(cmd_area, sw_update.STRATEGY_NAME_SW_PATCH)
    cmd_parser = commands.add_parser(cmd_area,
                                     help='Patch Strategy')
    cmd_parser.set_defaults(cmd_area=cmd_area)

    sub_cmds = cmd_parser.add_subparsers(title='Software Patch Commands',
                                         metavar='')
    sub_cmds.required = True

    # define the create command
    # alarm restrictions, defaults to strict
    _ = setup_create_cmd(
        sub_cmds,
        [sw_update.APPLY_TYPE_SERIAL,  # controller supports serial
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # storage supports serial and parallel
         sw_update.APPLY_TYPE_PARALLEL,
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # worker supports serial and parallel
         sw_update.APPLY_TYPE_PARALLEL,
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.INSTANCE_ACTION_STOP_START,  # instance actions
         sw_update.INSTANCE_ACTION_MIGRATE],
        [sw_update.ALARM_RESTRICTIONS_STRICT,  # alarm restrictions
         sw_update.ALARM_RESTRICTIONS_RELAXED],
        min_parallel=2,
        max_parallel=100  # patch supports 2..100 workers in parallel
    )

    # define the delete command
    _ = setup_delete_cmd(sub_cmds)
    # define the apply command
    _ = setup_apply_cmd(sub_cmds)
    # define the abort command
    _ = setup_abort_cmd(sub_cmds)
    # define the show command
    _ = setup_show_cmd(sub_cmds)


def setup_system_config_update_parser(commands):
    """System config update Strategy Commands"""

    cmd_area = sw_update.CMD_NAME_SYSTEM_CONFIG_UPDATE
    register_strategy(cmd_area, sw_update.STRATEGY_NAME_SYSTEM_CONFIG_UPDATE)
    cmd_parser = commands.add_parser(cmd_area,
                                     help='system config update Strategy')
    cmd_parser.set_defaults(cmd_area=cmd_area)

    sub_cmds = cmd_parser.add_subparsers(title='Sytem Config Update Commands',
                                         metavar='')
    sub_cmds.required = True

    # define the create command
    # alarm restrictions, defaults to strict
    _ = setup_create_cmd(
        sub_cmds,
        [sw_update.APPLY_TYPE_SERIAL,  # controller supports serial only
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # storage supports serial only
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # worker supports serial and parallel
         sw_update.APPLY_TYPE_PARALLEL,
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.INSTANCE_ACTION_STOP_START,  # instance actions
         sw_update.INSTANCE_ACTION_MIGRATE],
        [sw_update.ALARM_RESTRICTIONS_STRICT,  # alarm restrictions
         sw_update.ALARM_RESTRICTIONS_RELAXED],
        min_parallel=2,
        max_parallel=100  # config update supports 2..100 workers in parallel
    )

    # define the delete command
    _ = setup_delete_cmd(sub_cmds)
    # define the apply command
    _ = setup_apply_cmd(sub_cmds)
    # define the abort command
    _ = setup_abort_cmd(sub_cmds)
    # define the show command
    _ = setup_show_cmd(sub_cmds)


def setup_sw_deploy_parser(commands):
    """Software Deploy Strategy Commands"""

    cmd_area = sw_update.CMD_NAME_SW_DEPLOY
    # TODO(jkraitbe): Backend for sw-deploy will continue as old sw-upgrade for now
    register_strategy(cmd_area, sw_update.STRATEGY_NAME_SW_UPGRADE)
    cmd_parser = commands.add_parser(cmd_area,
                                     help='Software Deploy Strategy')
    cmd_parser.set_defaults(cmd_area=cmd_area)

    sub_cmds = cmd_parser.add_subparsers(title='Software Deploy Commands',
                                         metavar='')
    sub_cmds.required = True

    # define the create command
    # alarm restrictions, defaults to strict
    create_strategy_cmd = setup_create_cmd(
        sub_cmds,
        [sw_update.APPLY_TYPE_SERIAL,
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # storage supports serial and parallel
         sw_update.APPLY_TYPE_PARALLEL,
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.APPLY_TYPE_SERIAL,  # worker supports serial and parallel
         sw_update.APPLY_TYPE_PARALLEL,
         sw_update.APPLY_TYPE_IGNORE],
        [sw_update.INSTANCE_ACTION_STOP_START,  # instance actions
         sw_update.INSTANCE_ACTION_MIGRATE],
        [sw_update.ALARM_RESTRICTIONS_STRICT,  # alarm restrictions
         sw_update.ALARM_RESTRICTIONS_RELAXED],
        min_parallel=2,
        max_parallel=10  # SW Deploy supports 2..10 workers in parallel
    )

    # add sw-deploy specific arguments to the create command
    # The get_extra_create_args method is updated to align with these

    # VIM software deploy supports two modes: Upgrade and rollback.
    # The upgrade mode is enabled by passing the release parameter,
    # the rollback mode is enabled by passing the --rollback flag.
    # These modes are mutually exclusive.

    # sw-deploy create (upgrade)
    create_strategy_cmd.add_argument('release',
                                     help='software release for deployment',
                                     default=None,
                                     nargs="?")

    # sw-deploy create (rollback)
    create_strategy_cmd.add_argument('--rollback',
                                     help='Perform a rollback instead of upgrade',
                                     action="store_true",
                                     required=False)

    # define the delete command
    _ = setup_delete_cmd(sub_cmds)
    # define the apply command
    _ = setup_apply_cmd(sub_cmds)
    # define the abort command
    _ = setup_abort_cmd(sub_cmds)
    # define the show command
    _ = setup_show_cmd(sub_cmds)


def process_main(argv=sys.argv[1:]):  # pylint: disable=dangerous-default-value
    """
    Client - Main
    """
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--os-auth-url', default=None)
        parser.add_argument('--os-project-name', default=None)
        parser.add_argument('--os-project-domain-name', default=None)
        parser.add_argument('--os-username', default=None)
        parser.add_argument('--os-password', default=None)
        parser.add_argument('--os-user-domain-name', default=None)
        parser.add_argument('--os-region-name', default=None)
        parser.add_argument('--os-interface', default=None)

        commands = parser.add_subparsers(title='Commands', metavar='')
        commands.required = True

        # Add firmware update strategy commands
        setup_fw_update_parser(commands)

        # Add kubernetes rootca update strategy commands
        setup_kube_rootca_update_parser(commands)

        # Add kubernetes upgrade strategy commands
        setup_kube_upgrade_parser(commands)

        # Add software patch strategy commands
        setup_patch_parser(commands)

        # Add system config update strategy commands
        setup_system_config_update_parser(commands)

        # Add software sw-deploy strategy commands
        setup_sw_deploy_parser(commands)

        args = parser.parse_args(argv)

        if args.debug:
            # Enable Debug
            handler = urllib.request.HTTPHandler(debuglevel=1)
            opener = urllib.request.build_opener(handler)
            urllib.request.install_opener(opener)

        if args.os_auth_url is None:
            args.os_auth_url = os.environ.get('OS_AUTH_URL', None)

        if args.os_project_name is None:
            args.os_project_name = os.environ.get('OS_PROJECT_NAME', None)

        if args.os_project_domain_name is None:
            args.os_project_domain_name \
                = os.environ.get('OS_PROJECT_DOMAIN_NAME', 'Default')

        if args.os_username is None:
            args.os_username = os.environ.get('OS_USERNAME', None)

        if args.os_password is None:
            args.os_password = os.environ.get('OS_PASSWORD', None)

        if args.os_user_domain_name is None:
            args.os_user_domain_name = os.environ.get('OS_USER_DOMAIN_NAME', None)

        if args.os_region_name is None:
            args.os_region_name = os.environ.get('OS_REGION_NAME', None)

        if args.os_interface is None:
            args.os_interface = os.environ.get('OS_INTERFACE', None)

        if args.os_auth_url is None:
            print("Authentication URI not given")
            return

        if args.os_project_name is None:
            print("Project name not given")
            return

        if args.os_project_domain_name is None:
            print("Project domain name not given")
            return

        if args.os_username is None:
            print("Username not given")
            return

        if args.os_password is None:
            print("User password not given")
            return

        if args.os_user_domain_name is None:
            print("User domain name not given")
            return

        if args.os_region_name is None:
            print("Openstack region name not given")
            return

        if args.os_interface is None:
            print("Openstack interface not given")
            return

        strategy_name = get_strategy_name(args.cmd_area)
        if 'create' == args.cmd:
            extra_create_args = get_extra_create_args(args.cmd_area, args)
            sw_update.create_strategy(args.os_auth_url,
                                      args.os_project_name,
                                      args.os_project_domain_name,
                                      args.os_username,
                                      args.os_password,
                                      args.os_user_domain_name,
                                      args.os_region_name,
                                      args.os_interface,
                                      strategy_name,
                                      args.controller_apply_type,
                                      args.storage_apply_type,
                                      sw_update.APPLY_TYPE_IGNORE,
                                      args.worker_apply_type,
                                      args.max_parallel_worker_hosts,
                                      args.instance_action,
                                      args.alarm_restrictions,
                                      **extra_create_args)
        elif 'delete' == args.cmd:
            sw_update.delete_strategy(args.os_auth_url,
                                      args.os_project_name,
                                      args.os_project_domain_name,
                                      args.os_username,
                                      args.os_password,
                                      args.os_user_domain_name,
                                      args.os_region_name,
                                      args.os_interface,
                                      strategy_name,
                                      force=args.force)
        elif 'apply' == args.cmd:
            sw_update.apply_strategy(args.os_auth_url,
                                     args.os_project_name,
                                     args.os_project_domain_name,
                                     args.os_username,
                                     args.os_password,
                                     args.os_user_domain_name,
                                     args.os_region_name,
                                     args.os_interface,
                                     strategy_name,
                                     stage_id=args.stage_id)
        elif 'abort' == args.cmd:
            sw_update.abort_strategy(args.os_auth_url,
                                     args.os_project_name,
                                     args.os_project_domain_name,
                                     args.os_username,
                                     args.os_password,
                                     args.os_user_domain_name,
                                     args.os_region_name,
                                     args.os_interface,
                                     strategy_name,
                                     stage_id=args.stage_id)
        elif 'show' == args.cmd:
            sw_update.show_strategy(args.os_auth_url,
                                    args.os_project_name,
                                    args.os_project_domain_name,
                                    args.os_username,
                                    args.os_password,
                                    args.os_user_domain_name,
                                    args.os_region_name,
                                    args.os_interface,
                                    strategy_name,
                                    details=args.details,
                                    active=args.active,
                                    error_details=args.error_details)
        else:
            raise ValueError("Unknown command, %s, given for %s"
                             % (args.cmd, args.cmd_area))

    except KeyboardInterrupt:
        print("Keyboard Interrupt received.")

    except Exception as e:  # pylint: disable=broad-except
        _process_exit(e)


if __name__ == "__main__":
    process_main(sys.argv[1:])
