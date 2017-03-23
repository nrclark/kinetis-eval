#!/usr/bin/env python2

"""
exec(open("back_annotate.py").read())
"""

import pcbnew
import re

schematic_file = 'kinetis.sch'
dry_run = False

filename = pcbnew.GetBoard().GetFileName()
pcbnew.LoadBoard(filename)

def get_module_records():
    board = pcbnew.GetBoard()
    modules = board.GetModules()
    records = []

    for module in modules:
        reference = str(module.GetReference().encode("ASCII"))

        position = module.GetPosition()
        position = [position[0], position[1]]
        flipped = bool(module.IsFlipped())
        comp_type = re.findall("^[a-zA-Z]+",reference)[0]

        record = [reference, position, flipped, comp_type, module]
        records.append(record)
    return records

def scale_records(records):
    max_number = float('-Inf')
    for record in records:
        for coord in record[1]:
            if abs(coord) > max_number:
                max_number = float(abs(coord))

    for x in range(len(records)):
        records[x][1] = [float(k)/max_number for k in records[x][1]]

    return records

def sort_records(records, mult = 100):
    key = lambda x: (
        x[2],
        x[3],
        8*round(mult*x[1][0]) + round(mult*x[1][1]),
        round(mult*x[1][1]),
    )
    records = sorted(records, key=key)
    return records

def calculate_remaps(records):
    comp_type = ""
    index = 0
    for x in range(len(records)):
        if records[x][3] != comp_type:
            comp_type = records[x][3]
            index = 0
        index = index + 1
        records[x].append(comp_type+str(index))
    return records


def remap_schematic(schematic_file, records, dry_run = False):
    schematic_data = open(schematic_file,'r').read()

    for record in records:
        old_refdes = record[0]
        new_refdes = record[5]

        if old_refdes == new_refdes:
            continue

        regex = "^L[ \t]+.*?[ \t]+%s[ \t]*$" % old_refdes
        matches = re.findall(regex, schematic_data, flags=re.M)

        try: 
            assert(len(list(set(matches))) == 1)
        except AssertionError:
            open(schematic_file + ".dump", 'w').write(schematic_data)

        match = matches[0]
        comp_type = match.split()[1]
        
        old_line = match
        new_line = "L %s \x01%s" % (comp_type, new_refdes)
        if dry_run:
            print("Replacing [%s] with [%s]" % (old_line, new_line))
        else:
            schematic_data = re.sub(regex,new_line,schematic_data, flags=re.M)

        old_line = '"%s"' % old_refdes
        new_line = '"\x01%s"' % new_refdes

        if dry_run:
            print("Replacing [%s] with [%s]" % (old_line, new_line))
        else:
            schematic_data = schematic_data.replace(old_line, new_line)

    if dry_run:
        print("Stripping escapes")
    else:
        schematic_data = schematic_data.replace("\x01", "")

    if not dry_run:
        open(schematic_file, 'w').write(schematic_data)

def remap_pcb(records, dry_run = False):
    for record in records:
        if dry_run:
            print("Renaming %s to %s" % (record[0], record[5]))
        else:
            record[4].SetReference(record[5])
            record[4].SetSelected()

    if not dry_run:
        pcbnew.Refresh()
        pcbnew.GetBoard().SetModified()
        pcbnew.SaveBoard(filename, pcbnew.GetBoard())

    data = open(filename,'r').read()

    for record in records:
        old_refdes = record[0]
        new_refdes = record[5]
        regex = "Net-[(]%s-.*?[)]" % old_refdes

        nets = list(set(re.findall(regex, data)))

        for net in nets:
            replacement = net.replace("(%s" % old_refdes, "(\x01%s" % new_refdes)

            if dry_run:
                print("Replacing %s with %s" %(net, replacement))
            else:
                data = data.replace(net, replacement)

    if dry_run:
        print("Stripping escapes")
    else:
        data = data.replace("\x01", "")

    if not dry_run:
        open(filename,'w').write(data)
        pcbnew.LoadBoard(filename)
        pcbnew.Refresh()

def print_records(records):
    for record in records:
        print(record)

records = get_module_records()
records = scale_records(records)
records = sort_records(records, 100)
records = calculate_remaps(records)

print_records(records)

remap_schematic(schematic_file, records, dry_run)
remap_pcb(records, dry_run)

    
