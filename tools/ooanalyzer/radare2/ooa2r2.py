#!/usr/bin/env python3

""" Convert output JSON file from OOAnalyzer into a radare2 script

$ ooa2r2.py -h

usage: ooa2r2.py [-h] (-j JSON_FILE) -o OUT_FILE [-liu | -dcn]

Export OOAnalyzer's output JSON file into a radare2 initialization script

arguments:
  -h, --help            show this help message and exit
  -j JSON_FILE, --JSONFile JSON_FILE
                        Path to the OOAnalyzer's output JSON file
  -o OUT_FILE, --OutputFile OUT_FILE
                        Export to a specified file path(ex: OutputFileName.r2)
  -liu, --leave-import-usage-info   Don't export OOAnalyzer's usage info to Radare2
  -dcn, --use-demangled-class-names   Will try to use demangled class names(if available) while initializing classes
"""

__author__ = "Udit kumar agarwal(@madaari)"


import argparse
import json

# CONSTANTS
FLAG_PREFIX="ooa."

def get_args():
    ''' Handle arguments using argparse
    '''

    arg_parser = argparse.ArgumentParser(
        description="Export OOAnalyzer's output JSON file into a radare2 initialization script")

    arg_parser.add_argument("-j", "--JSONFile",
                            action="store",
                            dest="json_file",
                            required=True,
                            help="Path to the OOAnalyzer's output JSON file")

    arg_parser.add_argument("-o", "--OutputFile",
                            action="store",
                            dest="out_file",
                            required=True,
                            help="Export to a specified file path(ex: OutputFileName.r2)")

    arg_parser.add_argument("-liu", "--leave-import-usage-info",
                           dest="is_import",
                           action="store_false",
                           help="Don't export OOAnalyzer's usage info to Radare2")

    arg_parser.add_argument("-dcn", "--use-demangled-class-names",
                           dest="is_demangled_class_names",
                           action="store_true",
                           help="Will try to use demangled class names(if available) while initializing classes")

    arg_parser.set_defaults(is_import=True, is_demangled_class_names=False)

    args = arg_parser.parse_args()
    return args

# ----------------------------------------------------------------------

def write_header():
            outfile.write("""########################################################
#
# This file was generated by the ooa2r2.py script.
# Source: https://github.com/madaari/pharos
#
########################################################""")

# ----------------------------------------------------------------------

### Remove special_chars from input string as they are incompatible with radare2 

def format_name(ip_str):
    return FLAG_PREFIX+''.join(e for e in ip_str if (e.isalnum() or e == '_'))

# ----------------------------------------------------------------------

### Convert class info to r2 commands

def ooa2r2_export_class(name, method_list, vftable_list):
    outfile.write("\n")
    outfile.write("ac "+name+"\n")

    for vft in vftable_list.keys():
        outfile.write("acv "+name+" "+vft+" "+vftable_list[vft]+"\n")

    for met in method_list.keys():
        temp = method_list[met]
        met_type = temp[1]
        if "virt" in met_type:
            virt_offset = met_type.split('_')[2];
            outfile.write("acm "+name+" "+temp[0]+" "+met+" "+virt_offset+"\n")
        else:
            outfile.write("acm "+name+" "+temp[0]+" "+met+"\n")

# ----------------------------------------------------------------------

### Export Member usages as Radare2 comments

def ooa2r2_export_usage(use_info):
    outfile.write("\n")

    for key in use_info.keys():
        outfile.write("CCu Member usage: "+use_info[key]+" @"+key+"\n")

# ----------------------------------------------------------------------

def ooa2r2_set_classes(args, structs):

    for st in structs:
        name = format_name(st['Name'])

        if args.is_demangled_class_names:
            if len(st['DemangledName']) != 0:
                name = format_name(st['DemangledName']);

        method_list = {}
        for met in st['Methods']:
            method_list["0x"+str(met['ea'])] = [format_name(str(met["name"])), str(met['type'])]

        vftable_list = {}
        try:
            for vir in st['Vftables']:
                try:
                    for ent in vir['entries']:
                        method_list["0x"+str(ent['ea'])] = [format_name(str(ent["name"])), 'virt_'+str(ent['type']+'_')+ent['offset']]

                # In case there are no entries in vftable
                except KeyError as e:
                    # Do nothing, just skip the VFTable
                    pass;

            
            for vir in st['Vftables']:
                vftable_list["0x"+vir['ea']] = vir['vfptr']
        except KeyError as e:
            # Likely to happen if Vftables are not found
            pass;

        # Convert info to r2 commands for importing matadata
        ooa2r2_export_class(name, method_list, vftable_list)

# ----------------------------------------------------------------------

def ooa2r2_set_usage(args, usage_info):
    use_info = {}
    for us in usage_info:
        use_info["0x"+str(us['ea'])] = format_name(us['class'])

    ooa2r2_export_usage(use_info)

# ----------------------------------------------------------------------

### OOAnalyzer JSON parser

def json_parse(args, inp_file):

    global outfile

    try:
        outfile = open(args.out_file, 'w')
    except:
        print("Error making the output file")
        exit()

    write_header()

    print("[+] Starting conversion from '%s' to '%s'" %
            (args.json_file, args.out_file))

    try:
        ooa2r2_set_classes(args, inp_file['Structures'])
    except KeyError as e:
        print("No Structures found! "%e)

    if args.is_import:
        try:
            ooa2r2_set_usage(args, inp_file['Usages'][0]['Members'])
        except KeyError as e:
            print("No Usage info found! "%e)

    print("[+] Conversion done.")
    print("[!] Execute: r2 -i %s [program]" %
        (args.out_file))
   
#
# End of JSON Parsing
###

# ----------------------------------------------------------------------

def main():
    ''' Gets arguments from the user. Perform convertion of the OOAnalyzer's output JSON file into a radare2 initialization script
    '''
    args = get_args()

    if args.json_file:

        # Try to open, parse and validate the input JSON file
        try:
            inp_file = json.loads(open(args.json_file).read())
            json_parse(args, inp_file)

        # In case the JSON file isn't valid
        except ValueError as e:
            print('Invalid input json file: %s' % e)
            exit()

        # In any other case, most likely if there's any error while opening the file
        except OSError as e:
            print('Error opening input file: %s' % e)
            exit()
    else:
        # Should not happen
        print('Error parsing input JSON file')
        exit()



if __name__ == "__main__":
    main()
