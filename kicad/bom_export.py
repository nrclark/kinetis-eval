#!/usr/bin/env python3
# fucnk

"""FSDKFJSLDKF"""

import sys
import os
import re
import xml.etree.ElementTree as ET


def get_footprint(component_element):
    """ Returns the footprint field of a component. If no footprint is present,
    an empty string is returned. """

    try:
        footprint = component_element.findall("footprint")[0].text
    except IndexError:
        footprint = ""

    return footprint


def get_refdes(component_element):
    """ Returns the reference designator a component. If no value is present,
    an empty string is returned. """

    refdes = component_element.attrib['ref']
    return refdes


def get_value(component_element):
    """ Returns the value field of a component. If no value is present, an
    empty string is returned. """

    try:
        value = component_element.findall("value")[0].text
    except IndexError:
        value = ""

    return value


def get_fields(component_element):
    """ Finds and returns all custom 'field' entries associated with a
    part. """

    result = {}
    for fields_element in component_element.findall("fields"):
        for field in fields_element.findall("field"):
            value = field.text
            name = field.attrib['name']
            result[name] = value
    return result


def get_components(xml_file):
    """ Returns a list of all components in the design, each represented as
    a dict. """

    xml_file = os.path.abspath(os.path.normpath(xml_file))
    tree = ET.parse(xml_file)
    root = tree.getroot()
    component_elements = root.findall('components')[0].findall("*")
    results = []

    for element in component_elements:
        component_dict = {}
        component_dict['refdes'] = get_refdes(element)
        component_dict['footprint'] = get_footprint(element)
        component_dict['value'] = get_value(element)
        field_dict = get_fields(element)
        for key in field_dict.keys():
            component_dict[key] = field_dict[key]

        results.append(component_dict)
    return results


def sort_refdes_string(refdes_string):
    """ Accepts a comma-separated string of reference designators, splits it
    into a list, sorts the list, and reassembles it into a string. """

    refdes_list = refdes_string.split(',')
    refdes_list = [x.strip() for x in refdes_list]
    sorted_list = []
    final_list = []

    for refdes in refdes_list:
        number = re.findall("[0-9]+$", refdes)[0]
        refdes = refdes.replace(number, number.zfill(8))
        sorted_list.append(refdes)

    for refdes in sorted(sorted_list):
        number = re.findall("[0-9]+$", refdes)[0]
        refdes = refdes.replace(number, str(int(number)))
        final_list.append(refdes)

    return ", ".join(final_list)


def group_items(components):
    """ Groups identical components from a list of individual components (as
    emitted by the get_components function). The resulting list is ordered
    alphabetically. """

    line_dict = {}
    for component in components:
        refdes = component.pop('refdes')

        descriptor = ""
        for key in sorted(component.keys()):
            descriptor += "%s\f%s\t" % (key, component[key])

        descriptor = descriptor[:-1]
        if descriptor not in line_dict.keys():
            line_dict[descriptor] = []

        line_dict[descriptor] = line_dict[descriptor] + [refdes]

    bom_list = []
    for key in line_dict.keys():
        params = key.split('\t')
        params = [x.split('\f') for x in params]

        fields = {}
        for param in params:
            fields[param[0]] = param[1]

        refdes_string = ','.join(line_dict[key])
        quantity = len(line_dict[key])
        fields['refdes'] = sort_refdes_string(refdes_string)
        fields['quantity'] = str(quantity)
        bom_list.append(fields)

    bom_list = [[x['refdes'], x] for x in bom_list]
    bom_list = [x[1] for x in sorted(bom_list)]
    return bom_list


def main():
    """ Main BOM generation routine. """

    infile = os.path.abspath(os.path.normpath(sys.argv[1]))
    outfile = os.path.abspath(os.path.normpath(sys.argv[2]))

    if outfile[-4:].lower() != ".txt":
        outfile += ".txt"

    components = get_components(infile)
    line_items = group_items(components)

    # pylint: disable=consider-using-enumerate
    for count in range(len(line_items)):
        line_items[count]['bom_index'] = str(count + 1)

    fields = [['Line Item', ['bom_index']]]
    fields.append(['Quantity', ['quantity']])
    fields.append(['Reference Designator', ['refdes']])
    fields.append(['Description', ['Description', 'value']])
    fields.append(['Value', ['value']])
    fields.append(['Manufacturer', ['Manufacturer']])
    fields.append(['Manufacturer', ['Manufacturer PN']])
    fields.append(['Footprint', ['footprint']])

    result_lines = []
    result_lines.append('\t'.join([field[0] for field in fields]))

    for line in line_items:
        values = []
        for field in fields:
            value = ""
            for index in field[1]:
                if index in line.keys():
                    value = line[index]
                    break
            values.append(value)
        result_lines.append('\t'.join(values))

    result = "\n".join(result_lines)

    with open(outfile, 'w') as handle:
        sys.stdout.write(result + "\n")
        handle.write(result + "\n")

    return

if __name__ == "__main__":
    main()
