#!/usr/bin/env python2

""" Standalone command-line script for PCB location-based component annotation
in KiCAD (and back-annotation into a schematic). """

import argparse
import re
import os
import sys

import pcbnew

__version__ = "1.0"


def sanitize(path):
    """ Runs a number of path transformations to clean up and normalize
    an user-supplied path. """

    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    path = os.path.normcase(path)
    path = os.path.normpath(path)
    path = os.path.abspath(path)
    return path


def get_module_records(board=None):
    """ Locates all of the 'modules' in a loaded Kicad board. These will
    correspond with components in the design. Each module is turned into
    a record to be consumed by other functions in this script. """

    if board is None:
        board = pcbnew.GetBoard()

    modules = board.GetModules()
    records = []

    for module in modules:
        reference = str(module.GetReference().encode("ASCII"))

        if "**" in reference:
            continue

        position = module.GetPosition()
        position = [position[0], position[1]]
        flipped = bool(module.IsFlipped())
        comp_type = re.findall("^[a-zA-Z]+", reference)[0]

        record = [reference, position, flipped, comp_type, module]
        records.append(record)
    return records


def scale_records(records):
    """ Normalizes the X and Y coordinates of each record from -1.0 to 1.0,
    with +/-1.0 representing the farthest present co-ordinate in each
    direction. """

    max_number = float('-Inf')
    for record in records:
        for coord in record[1]:
            if abs(coord) > max_number:
                max_number = float(abs(coord))

    # pylint: disable=invalid-name, consider-using-enumerate
    for x in range(len(records)):
        records[x][1] = [float(k) / max_number for k in records[x][1]]

    return records


def sort_records(records, mult=100):
    """ Sorts records. This function controls the renaming order used
    by the reannotator. First, components are sorted by type. Next, they're
    sorted by board-side. Next, they're sorted by a mixture of their X and
    Y co-ordinates. Finally, they're sorted by their Y co-ordinates.

    The X and Y co-ordinates are first quantized by a 'mult' factor. """

    def key(record):
        """ Sorting function for component records """
        comp_type = record[2]
        comp_side = record[3]
        x_index = 8 * round(mult * record[1][0]) + round(mult * record[1][1])
        y_index = round(mult * record[1][1])
        return (comp_type, comp_side, x_index, y_index)

    records = sorted(records, key=key)
    return records


def calculate_remaps(records):
    """ Adds a record entry to each record indicating its new remapped value.
    The record list should already have been sorted prior to using this
    function. """

    comp_type = ""
    index = 0

    # pylint: disable=invalid-name, consider-using-enumerate
    for x in range(len(records)):
        if records[x][3] != comp_type:
            comp_type = records[x][3]
            index = 0
        index = index + 1
        records[x].append(comp_type + str(index))
    return records


def remap_pcb(board, pcb_file, records, dry_run=False, quiet=False):
    """ Renames components in the PCB based on their pre-calculated remaps.
    Any auto-generated refdes-derived nets are also renamed. """

    comp_renames = 0
    net_renames = 0

    for record in records:
        if record[0] == record[5]:
            continue

        comp_renames = comp_renames + 1

        if not quiet:
            sys.stdout.write("Renaming %s to %s\n" % (record[0], record[5]))

        if not dry_run:
            record[4].SetReference(record[5])
            record[4].SetSelected()

    if not dry_run:
        board.SetModified()
        pcbnew.SaveBoard(pcb_file, board)

    data = open(pcb_file, 'r').read()

    for record in records:
        if record[0] == record[5]:
            continue

        net_renames = net_renames + 1
        old_refdes = record[0]
        new_refdes = record[5]

        regex = "Net-[(]%s-.*?[)]" % old_refdes

        try:
            nets = list(set(re.findall(regex, data)))
        except Exception as err:
            sys.stderr.write("Failed on regex: %s\n" % repr(regex))
            raise err

        for net in nets:
            replacement = net.replace("(%s" % old_refdes,
                                      "(\x01%s" % new_refdes)

            if not quiet:
                sys.stdout.write("Replacing %s with %s\n" % (net, replacement))

            if not dry_run:
                data = data.replace(net, replacement)

    if not quiet:
        sys.stdout.write("Stripping escapes.\n")

    if not dry_run:
        data = data.replace("\x01", "")
        open(pcb_file, 'w').write(data)
        pcbnew.LoadBoard(pcb_file)

    if not quiet:
        sys.stdout.write("Components renamed on PCB: %d. " % comp_renames)
        sys.stdout.write("Nets renamed on PCB: %d.\n" % net_renames)


def remap_schematic(schematic_file, records, dry_run=False, quiet=False):
    """ Uses pre-calculated component records to back-annotate a Kicad
    schematic. """

    comp_renames = 0

    schematic_data = open(schematic_file, 'r').read()

    for record in records:
        old_refdes = record[0]
        new_refdes = record[5]

        if old_refdes == new_refdes:
            continue

        comp_renames = comp_renames + 1
        regex = "^L[ \t]+.*?[ \t]+%s[ \t]*$" % old_refdes
        matches = re.findall(regex, schematic_data, flags=re.M)

        try:
            assert len(list(set(matches))) == 1
        except AssertionError:
            open(schematic_file + ".dump", 'w').write(schematic_data)

        match = matches[0]
        comp_type = match.split()[1]

        old_line = match
        new_line = "L %s \x01%s" % (comp_type, new_refdes)

        if not quiet:
            sys.stdout.write("Replacing [%s] with [%s]\n" %
                             (old_line, new_line))

        if not dry_run:
            schematic_data = re.sub(regex, new_line, schematic_data,
                                    flags=re.M)

        old_line = '"%s"' % old_refdes
        new_line = '"\x01%s"' % new_refdes

        if not quiet:
            sys.stdout.write("Replacing [%s] with [%s]\n" %
                             (old_line, new_line))

        if not dry_run:
            schematic_data = schematic_data.replace(old_line, new_line)

    if not quiet:
        sys.stdout.write("Stripping escapes\n")

    if not dry_run:
        schematic_data = schematic_data.replace("\x01", "")
        open(schematic_file, 'w').write(schematic_data)

    if not quiet:
        sys.stdout.write("Components renamed on schematic: %d.\n" %
                         comp_renames)


def print_records(records):
    """ Prints a human-readable list of all located components. """

    for record in records:
        refdes = record[0]
        location = record[1]

        if record[2]:
            side = "bottom"
        else:
            side = "top"

        comp_type = record[3]

        sys.stdout.write("Found component [%s] of type [%s]. Side: [%s]. " %
                         (refdes, comp_type, side))
        sys.stdout.write("Position: [%.5f, %.5f]\n" %
                         (location[0], location[1]))


def make_parser():
    """ Creates the CLI's argparse instance. """

    description = """Script for renaming all components on a KiCAD PCB by their
    relative placement. Optionally back-annotates chances onto an accompanying
    schematic. Note that KiCAD should be closed before running this script. """

    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('pcb_file', metavar="PCB_FILE",
                        help="Target .kicad_pcb file to re-annotate.")

    parser.add_argument('-q', '--quiet', default=False, action="store_true",
                        help="Suppress the process's normal stdout.")

    parser.add_argument('-d', '--dry_run', default=False, action="store_true",
                        help="Does a dry-run instead of actually changing " +
                        "anything in the design.")

    parser.add_argument('-s', '--schematic', metavar="SCHEMATIC_FILE",
                        default="", help="Kicad schematic file to " +
                        "back-annotate. (default: none).")

    version_string = "%(prog)s" + " v%s" % __version__
    parser.add_argument('--version', action='version', version=version_string)

    parser.epilog = """Copyright 2017, Nicholas Clark."""
    return parser


def main():
    """ Main function for this script. """
    parser = make_parser()
    args = parser.parse_args()
    args.pcb_file = sanitize(args.pcb_file)

    if args.dry_run:
        access_flag = os.R_OK
    else:
        access_flag = os.W_OK

    if not os.access(args.pcb_file, access_flag):
        sys.stderr.write("Error: can't open file [%s]\n" % args.pcb_file)
        sys.exit(1)

    if args.schematic != "":
        args.schematic = sanitize(args.schematic)
        if not os.access(args.schematic, access_flag):
            sys.stderr.write("Error: can't open file [%s]\n" % args.schematic)
            sys.exit(1)

    board = pcbnew.LoadBoard(args.pcb_file)

    records = get_module_records(board)
    records = scale_records(records)
    records = sort_records(records, 100)
    records = calculate_remaps(records)

    if not args.quiet:
        print_records(records)

    remap_pcb(board, args.pcb_file, records, args.dry_run, args.quiet)

    if args.schematic != "":
        remap_schematic(args.schematic, records, args.dry_run, args.quiet)

if __name__ == "__main__":
    main()
