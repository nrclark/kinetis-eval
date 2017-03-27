#!/usr/bin/env python2

""" Standalone command-line script for generating drill files for a PCB
designed in KiCAD. Script can optionally validate drill selection and
slots. """

import argparse
import re
import os
import sys
import tempfile
import shutil

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


def check_drills(allowed_drill_file, drill_report_file, metric=False):
    """ Verifies that the drills called out in a KiCAD drill report can all
    be found in a whitelisted drill file. Returns 'True' if all drill
    selections are valid, and 'False' otherwise. """

    allowed_drill_data = open(allowed_drill_file, 'r').read()
    drill_report_data = open(drill_report_file, 'r').read()

    used_drills = []
    matches = re.findall('^[ \t]*T[0-9]+[ \t].+$', drill_report_data,
                         flags=re.M)

    for match in matches:
        match = match.strip().split()
        drill = float(match[2][:-1])
        used_drills.append(drill)

    allowed_drills = []

    for line in allowed_drill_data.split('\n'):
        line = re.sub("[#].*", "", line).strip()
        if line != "":
            allowed_drills.append(float(line))

    if metric:
        allowed_drills = [x / 25.4 for x in matches]

    for used_drill in used_drills:
        match = False
        for allowed_drill in allowed_drills:
            if abs(allowed_drill - used_drill) < 0.0001:
                match = True
                break

        if match is False:
            msg = "Error: Drill [%0.04f mils / %0.01f mm] not in whitelist.\n"
            msg = msg % (used_drill, used_drill * 25.4)
            sys.stderr.write(msg)
            return False

    return True


def generate_drill_files(args):
    """ Generates the drill files for a KiCAD design, including a drill
    report. The options/arguments consumed by this function are all provided
    by the argument parser. Returns 0 if everything was successful, or 1
    otherwise. """

    pcb_file = sanitize(args.pcb_file)
    output_dir = sanitize(args.output_dir)

    file_base = os.path.splitext(os.path.basename(pcb_file))[0]
    drill_report_file = "%s-drill_report.txt" % file_base
    drill_report_file = os.path.join(args.tempdir, drill_report_file)

    board = pcbnew.LoadBoard(pcb_file)
    origin_point = board.GetAuxOrigin()

    writer = pcbnew.EXCELLON_WRITER(board)
    writer.SetMapFileFormat(pcbnew.PLOT_FORMAT_GERBER)
    writer.SetFormat(args.metric, pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT)
    writer.SetOptions(False, False, origin_point, False)

    writer.GenDrillReportFile(drill_report_file)
    writer.CreateDrillandMapFilesSet(args.tempdir, True, True)

    if args.check != "":
        drills_ok = check_drills(sanitize(args.check), drill_report_file,
                                 args.metric)
        if drills_ok is False:
            return 1

    if args.no_slots:
        drill_report_data = open(drill_report_file, 'r').readlines()
        for line in drill_report_data:
            if re.findall("with [1-9][0-9]* slot", line) != []:
                sys.stderr.write("Error: One or more slots reported in ")
                sys.stderr.write("design.\n%s" % line)
                return 1

    if not os.path.isdir(output_dir):
        try:
            os.mkdir(output_dir)
        except OSError:
            err_msg = "Error: Couldn't make output directory [%s]" % output_dir
            sys.stderr.write(err_msg + "\n")
            return 1

    for filename in os.listdir(args.tempdir):
        filename = os.path.join(args.tempdir, filename)
        shutil.copy(filename, output_dir)

    return 0


def make_parser():
    """ Creates the CLI's argparse instance. """

    description = """Script for generating drill files from a KiCAD PCB
    design. Outputs can be in imperial or metric, and can optionally be
    verified against several manufacturing checks. """

    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('pcb_file', metavar="PCB_FILE",
                        help="Target .kicad_pcb file to re-annotate.")

    parser.add_argument('-q', '--quiet', default=False, action="store_true",
                        help="Suppress the process's normal stdout.")

    parser.add_argument('-o', '--output_dir', default='.',
                        help="Output directory (default: '.')")

    parser.add_argument('-c', '--check', default='',
                        help="Check generated drills against a list of " +
                        "allowed values. Refuse to generate outputs if one" +
                        "or more holes in the design is out-of-spec.")

    parser.add_argument('-m', '--metric', default=False, action="store_true",
                        help="Generate outputs in metric (default: imperial).")

    parser.add_argument('-n', '--no_slots', default=False, action="store_true",
                        help="Refuse to generate outputs if slots are " +
                        "present in the design")

    version_string = "%(prog)s" + " v%s" % __version__
    parser.add_argument('--version', action='version', version=version_string)

    parser.epilog = """Copyright 2017, Nicholas Clark."""
    return parser


def main():
    """ Main function for this script. """

    parser = make_parser()
    args = parser.parse_args()
    args.pcb_file = sanitize(args.pcb_file)

    if not os.access(args.pcb_file, os.R_OK):
        sys.stderr.write("Error: can't open file [%s]\n" % args.pcb_file)
        sys.exit(1)

    args.tempdir = tempfile.mkdtemp(prefix="tmp.kicad_drill-")

    try:
        retval = generate_drill_files(args)

        if os.path.exists(args.tempdir):
            shutil.rmtree(args.tempdir)

        sys.exit(retval)

    except Exception as err:
        if os.path.exists(args.tempdir):
            shutil.rmtree(args.tempdir)
        raise err

if __name__ == "__main__":
    main()
