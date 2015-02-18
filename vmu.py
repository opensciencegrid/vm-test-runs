#!/usr/bin/python

'''A collection of functions that are used across the various VMU automated test scripts'''

import re

def canonical_os_string(os_release):
    '''Make the OS release from /etc/redhat-release human readable'''
    result = os_release.replace('Red Hat Enterprise Linux Server', 'RHEL')
    result = result.replace('Scientific Linux', 'SL')
    result = re.sub(r'(\d)\.\d+', '\\1', result)
    return result

def canonical_pkg_string(package):
    '''Make the string of installed packages human readable'''
    mapping = {
        'condor.x86_64, osg-ce-condor, rsv': 'Condor',
        'osg-gridftp, edg-mkgridmap, rsv': 'GridFTP',
        'osg-gums, rsv': 'GUMS',
        'osg-se-bestman, rsv': 'BeStMan',
        'osg-tested-internal': 'All',
        'osg-voms, rsv': 'VOMS'
        }
    try:
        strip_java = re.sub(r'java-1.7.0-openjdk-devel,\s*osg-java7-compat,\s*osg-java7-devel-compat',
                            'Java', package)
        java_prefix, package = re.match(r'(Java[,\s]*)(.*)', strip_java).groups()
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
