#!/usr/bin/python

'''A collection of functions that are used across the various VMU automated test scripts'''

from glob import glob
import re
import sys
import yaml
import copy

def die(message, code=1):
    '''Write message to STDERR and exit with code'''
    sys.stderr.write(message + '\n')
    sys.exit(code)

def write_file(contents, file_path):
    '''Write contents to file_path'''
    f = open(file_path, 'w')
    f.write(contents)
    f.close()

def load_run_params(param_dir):
    '''Read all yaml parameter files in a directory and add them to the list'''
    run_params = []
    # Slurp param files in reverse order so that the latest OSG versions show
    # at the top of the results 
    for param_file in reversed(sorted(glob("%s/*" % param_dir))):
        with open(param_file, 'r') as yaml_file:
            yaml_contents = yaml_file.read()
        try:
            param_contents = yaml.load(yaml_contents)
        except (yaml.scanner.ScannerError, yaml.reader.ReaderError):
            # skip non-yaml files
            pass
        else:
            if param_contents.has_key('platform') \
               and param_contents.has_key('sources') \
               and param_contents.has_key('packages'):
                run_params.append(param_contents)
    if not run_params:
        die("Could not find parameter files in parameter directory '%s'" % param_dir)
    return run_params

def flatten_run_params(params_list):
    '''Combines multiple run parameters files into a single dictionary (eliminating duplicates)'''
    primary = copy.deepcopy(params_list[0])
    for param in primary.iterkeys():
        for secondary in params_list[1:]:
            primary[param] += [val for val in secondary[param] if val not in primary[param]]
    return primary

def pkg_mapping(run_params):
    '''Takes a list of params (i.e. output of load_run_params) and extracts the unique packages and their labels, 
    if any, returning a dictionary with strings of packages and labels as key/value pairs'''
    mapping = {}
    labels = {} # for verifying uniqueness of labels
    flat_params = flatten_run_params(run_params)
    for pkg_list in flat_params['packages']:
        # Items in the 'packages' section can be dicts or lists (i.e. labeled or not)
        if type(pkg_list) is dict:
            label, pkg_list = pkg_list.items()[0]
            pkg_list = ', '.join(pkg_list)
        else:
            continue
        if mapping.has_key(pkg_list):
            if mapping[pkg_list] == label:
                continue
            else:
                die("ERROR: Two different labels ('%s', '%s') are being used to describe the same package set:\n"
                    % (label, mapping[pkg_list]) + "[%s]" % pkg_list, code=2)
        elif labels.has_key(label):
            die("ERROR: The label '%s' describes two different package sets:\n" % label +
                "[%s]\n[%s]" % (labels[label], pkg_list), code=2)
        else:
            mapping.update({pkg_list: label})
            labels.update({label: pkg_list})
    return mapping

def canonical_os_string(os_release):
    '''Make the OS release from test parameters or /etc/redhat/release human readable'''
    # Handle OS string from /etc/redhat-release
    result = os_release.replace('Red Hat Enterprise Linux Server', 'RHEL')
    result = result.replace('Scientific Linux', 'SL')
    result = result.replace('CentOS Linux', 'CentOS')
    result = re.sub(r'(\d)\.\d+.*', r'\1', result)
    # Handle OS string from 'platform' test parameters
    result = result.replace('rhel', 'RHEL')
    result = result.replace('sl', 'SL')
    result = result.replace('centos', 'CentOS')
    result = re.sub(r'_(\d)_.*', r' \1', result)
    return result

def canonical_pkg_string(package, mapping):
    '''Take a package set and a dictionary mapping of package sets to packages human readable strings'''
    try:
        return mapping[package]
    except KeyError:
        # Replace commonly installed java packages with an *
        return re.sub(r'java-1.7.0-openjdk-devel,\s*osg-java7-compat,\s*osg-java7-devel-compat,\s+',
                      '*', package)

def canonical_src_string(sources):
    '''Make the repo source string human readable'''
    result = re.sub(r'\s*>\s*', ' -> ', sources)
    result = re.sub(r'osg-minefield', 'Minefield', result)
    result = re.sub(r'osg-development', 'Development', result)
    result = re.sub(r'osg-testing', 'Testing', result)
    result = re.sub(r'osg-prerelease', 'Prerelease', result)
    result = re.sub(r'osg-upcoming', 'Upcoming', result)
    result = re.sub(r'osg-upcoming-testing', 'Upcoming Testing', result)
    result = re.sub(r'osg', 'Release', result) # Must come after other repos
    result = re.sub(r'(^\w*/\w*)(.*)', '\\2 (\\1)', result)
    result = re.sub(r';', '', result)
    result = re.sub(r'/', ' ', result)
    result = re.sub(r'\((\w*) (\w*)\)', '(\\1/\\2)', result)
    result = re.sub(r',', ' + ', result)
    result = re.sub(r'^(\d+\.\d+)(.*-> )(?!\d)', '\\1\\2\\1 ', result) # Duplicate release series, when needed
    return result.strip()
