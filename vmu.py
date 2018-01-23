#!/usr/bin/python

'''A collection of functions that are used across the various VMU automated test
scripts'''

from glob import glob
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
            if set(param_contents) == set(['platforms', 'sources', 'package_sets']):
                param_contents['package_sets'] = [PackageSet.from_dict(x) for x in param_contents['package_sets']]
                run_params.append(param_contents)
    if not run_params:
        raise ParamError('Could not find parameter files in parameter directory: %s' % param_dir)
    return run_params

def flatten_run_params(params_list):
    '''Combines multiple run parameter files into a single dictionary eliminating duplicates in the 'platforms',
    'sources', and 'package_sets' sections. Sorts the 'package_sets' section, leaving the others unsorted. '''
    result = {'platforms': [], 'sources': [], 'package_sets': []}
    for param_file_contents in params_list:
        for section in param_file_contents.iterkeys():
            section_contents = param_file_contents[section]
            for item in section_contents:
                if item in result[section]:
                    continue
                result[section] += [item]
            if section == 'package_sets':
                result[section].sort(key=PackageSet.get_sort_val)
    return result

def package_mapping(flat_params):
    '''Takes the unique parameters (i.e. the output from flatten_run_params) and returns a dictionary of stringified
    lists of packages as keys and their labels as values'''
    return dict((', '.join(x.packages), x.label) for x in flat_params['package_sets'])

def canonical_os_string(os_release):
    '''Make the OS release from test parameters or /etc/redhat/release human readable'''
    # Handle OS string from /etc/redhat-release
    result = os_release.replace('Red Hat Enterprise Linux Server', 'RHEL')
    result = result.replace('Scientific Linux', 'SL')
    result = result.replace('CentOS Linux', 'CentOS')
    result = re.sub(r'(\d)\.\d+.*', r'\1', result)
    # Handle OS string from 'platforms' test parameters
    result = result.replace('rhel', 'RHEL')
    result = result.replace('sl', 'SL')
    result = result.replace('centos', 'CentOS')
    result = re.sub(r'_(\d)_.*', r' \1', result)
    return result

def canonical_src_string(sources):
    '''Make the repo source string human readable'''
    result = re.sub(r'\s*>\s*', ' -> ', sources)
    branch = None
    m = re.search(r'(^\w+:[./\w-]+)\s*;\s*(.*)', result)
    if m:
        branch, result = m.groups()
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
    if branch:
        result += " (%s)" % branch
    return result.strip()

class ParamError(Exception):
    """Exception for errors in parameter files"""
    pass

class PackageSet(object):
    """A class for comparing package sets as specified in VMU test parameters

    Instance parameters:

    label: string describing the package set, used for reporting
    packages: list of packages as strings
    selinux: boolean to turn on/off SELinux enforcing mode (default: False)
    java: boolean to pre-install OSG java packages (default: True)
    rng: boolean to pre-install entropy-generation package (for random numbers) (default: False)

    PackageSets are equal if their 'packages' lists are the same. If 'packages'
    lists are equal but 'label' is not, ParamError is raised.

    PackageSets are sorted by labels according to LABEL_ORDER. Unknown labels
    are sorted alphanumerically after the known labels.
    """

    OSG_JAVA_DEFAULT = True
    SELINUX_DEFAULT = True
    RNG_DEFAULT = False
    LABEL_ORDER = ['All', 'All + GRAM', 'All + GRAM (3.2)', 'HTCondor', 'GridFTP', 'BeStMan', 'VOMS', 'GUMS']
    LABEL_IDX = dict( (v,i) for i,v in enumerate(LABEL_ORDER) )

    def __init__(self, label, packages, selinux=SELINUX_DEFAULT, java=OSG_JAVA_DEFAULT, rng=RNG_DEFAULT):
        if not label:
            raise ParamError("PackageSet 'label' field cannot be blank")
        if not packages:
            raise ParamError("PackageSet 'packages' field must be non-empty list")
        self.label = label
        self.selinux = selinux
        self.java = java
        self.rng = rng

        # FIXME: PackageSet is currently a misnomer since 'packages' are a list rather than a set
        if self.java:
            self.packages = ['java-1.7.0-openjdk-devel', 'osg-java7-compat', 'osg-java7-devel-compat'] + packages
        else:
            self.packages = packages
        if self.selinux:
            self.packages.append('policycoreutils-python')
        if self.rng:
            self.packages.append('haveged')

    def __eq__(self, other):
        if isinstance(other, PackageSet):
            if self.packages == other.packages:
                if self.label != other.label:
                    raise ParamError("Different package set tags ('%s', '%s') refer to the same set of packages. " %
                                     (self.label, other.label) + "Check if java attributes are different.")
                return True
            elif self.label == other.label:
                raise ParamError("Package set label '%s' refers to different sets of packages" % self.label)
            return False
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def get_sort_val(self):
        return self.LABEL_IDX.get(self.label, self.label)

    def __lt__(self, other):
        return self.get_sort_val() < other.get_sort_val()

    def __hash__(self):
        # Treat similarly labeled sets of packages as equal for hashing;
        # SELinux status can differ on a per-run basis
        return hash(repr(self).replace('%s, ' % self.selinux, ''))

    def __repr__(self):
        return "PackageSet(label=%s, packages=%s, selinux=%s, rng=%s)" % (self.label, self.selinux, self.packages, self.rng)

    @classmethod
    def from_dict(cls, pkg_set_dict):
        '''Create a PackageSet object from a dictionary, setting selinux, java,
        and rng attributes to SELINUX_DEFAULT, OSG_JAVA_DEFAULT, or
        RNG_DEFAULT, respectively, if they're not defined
        '''
        return cls(pkg_set_dict['label'],
                   pkg_set_dict['packages'],
                   pkg_set_dict.get('selinux', cls.SELINUX_DEFAULT),
                   pkg_set_dict.get('osg_java', cls.OSG_JAVA_DEFAULT),
                   pkg_set_dict.get('rng', cls.RNG_DEFAULT))
