#!/usr/bin/env python2
# This file is part of Archivematica.
#
# Copyright 2010-2013 Artefactual Systems Inc. <http://artefactual.com>
#
# Archivematica is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Archivematica is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Archivematica.  If not, see <http://www.gnu.org/licenses/>.

# @package Archivematica
# @subpackage archivematicaClientScript
# @author Joseph Perry <joseph@artefactual.com>

from __future__ import print_function
import argparse
import os
import sys

import django
django.setup()

# archivematicaCommon
from archivematicaFunctions import get_setting
from custom_handlers import get_script_logger
from executeOrRunSubProcess import executeOrRun


def run_bag(arguments):
    """ Run Bagit's create bag command. """
    command = "/usr/share/bagit/bin/bag"
    print('Command to run:', command, "Arguments: ", arguments)
    exit_code, std_out, std_err = executeOrRun("command", [command], arguments=arguments, printing=False)
    if exit_code != 0:
        print("Error with command: ", command, file=sys.stderr)
        print("Standard OUT:", file=sys.stderr)
        print(std_out, file=sys.stderr)
        print("Standard Error:", file=sys.stderr)
        print(std_err, file=sys.stderr)
        exit(exit_code)
    else:
        print(std_out)
        print(std_err, file=sys.stderr)


def get_sip_directories(sip_dir):
    """ Get a list of directories in the SIP, to be created after bagged. """
    directory_list = []
    for directory, subdirs, _ in os.walk(sip_dir):
        for subdir in subdirs:
            path = os.path.join(directory, subdir).replace(sip_dir + "/", "", 1)
            directory_list.append(path)
    print("directory list:")
    for sip_dir in directory_list:
        print("\t", sip_dir)
    return directory_list


def create_directories(base_dir, dir_list):
    """ Create all the SIP's directories in the bag's data/ folder.

    Some directories should have been created in the data/ folder by the bagit
    command, but create any empty (or unspecified) directories. """
    for directory in dir_list:
        directory = os.path.join(base_dir, directory)
        try:
            os.makedirs(directory)
        except os.error:
            pass


def bag_with_empty_directories(operation, destination, sip_directory, payload_entries, writer, algorithm):
    """ Run bagit create bag command, and create any empty directories from the SIP. """
    # Get list of directories in SIP
    dir_list = get_sip_directories(sip_directory)

    # These are passed to this script as paths relative to their location in
    # the SIP; passing the full SIP location each time has the potential to
    # overflow the 1000-character limit the job's command has in the database,
    # especially with long SIP names.
    full_paths = [os.path.join(sip_directory, p) for p in payload_entries]
    # Ensure all payload items actually exist
    payload_entries = [e for e in full_paths if os.path.exists(e)]

    # Reconstruct bagit arguments
    # Goal: bagit <operation> <destination> <flattened payload list> <optional args>
    bagit_args = [operation, destination]
    bagit_args.extend(payload_entries)
    bagit_args.extend(['--writer', writer, '--payloadmanifestalgorithm', algorithm])

    # Run bagit bag creator
    run_bag(bagit_args)
    create_directories(os.path.join(destination, "data"), dir_list)


if __name__ == '__main__':
    logger = get_script_logger("archivematica.mcp.client.bagWithEmptyDirectories")
    # Parse arguments
    parser = argparse.ArgumentParser(description='Convert folder into a bag.')
    parser.add_argument('operation')
    parser.add_argument('destination')
    parser.add_argument('sip_directory')
    parser.add_argument('payload_entries', metavar='Payload', nargs='+',
                        help='All the files/folders that should go in the bag.')
    parser.add_argument('--writer', dest='writer')

    algorithm = get_setting('checksum_type', 'sha512')

    args = parser.parse_args()
    bag_with_empty_directories(args.operation, args.destination, args.sip_directory, args.payload_entries, args.writer, algorithm)
