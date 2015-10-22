#!/usr/bin/python

'''A collection of functions that are used across the various VMU automated test scripts'''

import os
import re
import sys
import yaml

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
    for param_file in os.listdir(param_dir):
        param_path = "%s/%s" % (param_dir, param_file)
        yaml_file = open(param_path)
        yaml_contents = yaml_file.read()
        yaml_file.close()
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

def canonical_pkg_string(package):
    '''Make the string of installed packages human readable'''
    mapping = {
        'condor.x86_64, osg-ce-condor, rsv': 'Condor',
        'osg-gridftp, edg-mkgridmap, rsv': 'GridFTP',
        'osg-gums, rsv': 'GUMS',
        'osg-se-bestman, globus-proxy-utils, rsv': 'BeStMan',
        'osg-tested-internal': 'All',
        'osg-voms, rsv': 'VOMS'
        }
    try:
        strip_java = re.sub(r'java-1.7.0-openjdk-devel,\s*osg-java7-compat,\s*osg-java7-devel-compat',
                            '*', package)
        java_prefix, package = re.match(r'(\*)[,\s]*(.*)', strip_java).groups()
    except AttributeError:
        java_prefix = ''

    try:
        return java_prefix + mapping[package]
    except KeyError:
        return java_prefix + package

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
    result = re.sub(r';', '', result)
    result = re.sub(r'/', ' ', result)
    result = re.sub(r',', ' + ', result)
    result = re.sub(r'^(\d+\.\d+)(.*-> )(?!\d)', '\\1\\2\\1 ', result) # Duplicate release series, when needed
    result = re.sub(r'^trunk\s*(.*)$', '\\1 (TRUNK)', result)
    return result
