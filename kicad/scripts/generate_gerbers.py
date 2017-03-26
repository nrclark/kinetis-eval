#!/usr/bin/env python2

""" Standalone command-line script for generating drill files for a PCB
designed in KiCAD. Script can optionally validate drill selection and
slots. """

import argparse
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


def generate_gerbers(args):
    """ Generates Gerber output files from a Kicad PCB design. Uses the
    arguments constructed elsewhere in this script. """

    pcb_file = sanitize(args.pcb_file)
    output_dir = sanitize(args.output_dir)

    board = pcbnew.LoadBoard(pcb_file)
    plotter = pcbnew.PLOT_CONTROLLER(board)
    options = plotter.GetPlotOptions()

    options.SetPlotFrameRef(False)
    options.SetPlotPadsOnSilkLayer(False)
    options.SetPlotValue(True)
    options.SetPlotReference(True)

    options.SetPlotInvisibleText(False)
    options.SetPlotViaOnMaskLayer(False)
    options.SetPlotPadsOnSilkLayer(False)
    options.SetExcludeEdgeLayer(True)

    options.SetUseAuxOrigin(True)

    options.SetUseGerberProtelExtensions(False)
    options.SetUseGerberAttributes(False)
    options.SetSubtractMaskFromSilk(True)

    options.SetLineWidth(pcbnew.FromMils(4))
    options.SetGerberPrecision(6)

    # At the time of this writing, KiCAD appears to have some kind of bug
    # that prevents SetOutputDirectory() from accepting absolute paths.
    # As a result, this script creates a relative path to args.tempdir,
    # and uses that instead.

    path_components = []
    result = os.path.split(args.pcb_file)

    while result[1] != "":
        path_components.append(result[1])
        result = os.path.split(result[0])

    rel_root = (os.path.pardir + os.path.sep) * (len(path_components) - 1)
    rel_root = rel_root[:-1 * len(os.path.sep)]
    tempdir = rel_root + args.tempdir
    options.SetOutputDirectory(tempdir)

    plot_plan = [
        ("CuTop", pcbnew.F_Cu, "Top layer"),
        ("CuBottom", pcbnew.B_Cu, "Bottom layer"),
        ("PasteBottom", pcbnew.B_Paste, "Paste Bottom"),
        ("PasteTop", pcbnew.F_Paste, "Paste top"),
        ("SilkTop", pcbnew.F_SilkS, "Silk top"),
        ("SilkBottom", pcbnew.B_SilkS, "Silk top"),
        ("MaskBottom", pcbnew.B_Mask, "Mask bottom"),
        ("MaskTop", pcbnew.F_Mask, "Mask top"),
        ("EdgeCuts", pcbnew.Edge_Cuts, "Edges"),
        ("FabTop", pcbnew.F_Fab, "Fab drawing top"),
        ("FabBottom", pcbnew.B_Fab, "Fab drawing bottom"),
    ]

    for layer_info in plot_plan:
        plotter.SetLayer(layer_info[1])
        plotter.OpenPlotfile(layer_info[0], pcbnew.PLOT_FORMAT_GERBER,
                             layer_info[2])
        plotter.PlotLayer()

    if not os.path.isdir(output_dir):
        try:
            os.mkdir(output_dir)
        except OSError:
            err_msg = "Error: Couldn't make output directory [%s]" % output_dir
            sys.stderr.write(err_msg + "\n")
            return 1

    for filename in os.listdir(args.tempdir):
        filename = os.path.join(args.tempdir, filename)
        if os.path.getsize(filename) != 0:
            shutil.copy(filename, output_dir)

    return 0


def make_parser():
    """ Creates the CLI's argparse instance. """

    description = """
Script for generating Gerber files from a KiCAD PCB design. Exports the
following Gerbers (plotted relative to KiCAD's aux-origin point):

     - Copper top/bottom
     - Paste top/bottom
     - Silkscreen top/bottom
     - Soldermask top/bottom
     - Fab drawing top/bottom
     - Edge cuts
"""
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('pcb_file', metavar="PCB_FILE",
                        help="Target .kicad_pcb file to re-annotate.")

    parser.add_argument('-q', '--quiet', default=False, action="store_true",
                        help="Suppress the process's normal stdout.")

    parser.add_argument('-o', '--output_dir', default='.',
                        help="Output directory (default: '.')")

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

    args.tempdir = tempfile.mkdtemp(prefix="tmp.kicad_gerber-")

    try:
        retval = generate_gerbers(args)

        if os.path.exists(args.tempdir):
            shutil.rmtree(args.tempdir)

        sys.exit(retval)

    except Exception as err:
        if os.path.exists(args.tempdir):
            shutil.rmtree(args.tempdir)
        raise err

if __name__ == "__main__":
    main()
