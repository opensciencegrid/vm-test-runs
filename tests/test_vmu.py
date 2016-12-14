#!/usr/bin/env python
# python -m unittest -v test_vmu[.TestClass][.test_function]

#pylint: disable=C0301
#pylint: disable=R0904

import copy
import mock
import os
import sys
import unittest

PATHNAME = os.path.realpath('../')
sys.path.insert(0, PATHNAME)

import vmu

def results_msg(expected, actual, msg):
    divider = '='*70 + '\n'
    return '%s\n' % msg + divider + \
        'EXPECTED:\n%s\n' % str(expected) + divider + \
        'ACTUAL:\n%s\n' % str(actual)

class TestVmu(unittest.TestCase):

    def assertEqualWithResults(self, expected, actual, msg=None):
        """Assert equality with pre-built failure message"""
        self.assertEqual(expected, actual, results_msg(expected, actual, msg))

    def assertNotEqualWithResults(self, expected, actual, msg=None):
        """Assert inequality with pre-built failure message"""
        self.assertNotEqual(expected, actual, results_msg(expected, actual, msg))

class TestPackageSet(TestVmu):

    def test_missing_label(self):
        self.assertRaises(vmu.ParamError, vmu.PackageSet, '', [1, 2, 3])

    def test_empty_packages(self):
        self.assertRaises(vmu.ParamError, vmu.PackageSet, 'foo', [])

    def test_equality(self):
        self.assertEqualWithResults(vmu.PackageSet('foo', [1, 2, 3], True, False),
                                    vmu.PackageSet('foo', [1, 2, 3], True, False),
                                    'PackageSet label or packages equality broken')
        self.assertEqualWithResults(vmu.PackageSet('foo', [1, 2, 3], True, False),
                                    vmu.PackageSet('foo', [1, 2, 3], False, False),
                                    'PackageSet SELinux equality broken')
        # Test mismatched tags
        self.assertRaises(vmu.ParamError, vmu.PackageSet.__eq__,
                          vmu.PackageSet('foo', [1, 2, 3], True, False),
                          vmu.PackageSet('bar', [1, 2, 3], False, False))

    def test_inequality(self):
        self.assertNotEqualWithResults(vmu.PackageSet('foo', [1, 2, 3]),
                                       vmu.PackageSet('bar', [4, 5, 6]),
                                       'PackageSet packages inequality broken')
        self.assertNotEqualWithResults(vmu.PackageSet('foo', [1, 2, 3]),
                                       vmu.PackageSet('foo', [4, 5, 6]),
                                       'PackageSet packages inequality broken')
        self.assertNotEqualWithResults(vmu.PackageSet('foo', [1, 2, 3], java=True),
                                       vmu.PackageSet('foo', [1, 2, 3], java=False),
                                       'PackageSet java inequality broken')
        # Test mismatched tags
        self.assertRaises(vmu.ParamError, vmu.PackageSet.__eq__,
                          vmu.PackageSet('foo', [1, 2, 3], True, False),
                          vmu.PackageSet('bar', [1, 2, 3], False, False))

    def test_sorting(self):
        unsorted_pkgs = [vmu.PackageSet('All + GRAM', [1]),
                vmu.PackageSet('GridFTP', [1]),
                vmu.PackageSet('VOMS', [1]),
                vmu.PackageSet('All + GRAM (3.2)', [1]),
                vmu.PackageSet('All', [1]),
                vmu.PackageSet('HTCondor', [1]),
                vmu.PackageSet('GUMS', [1]),
                vmu.PackageSet('BeStMan', [1]),
                vmu.PackageSet('foo', [1])]
        unsorted_pkgs.sort()
        self.assertEqualWithResults(vmu.PackageSet.LABEL_ORDER + ['foo'],
                                    [x.label for x in unsorted_pkgs],
                                    'Unexpected sort order')

    def test_defaults(self):
        pkg_set = vmu.PackageSet('foo', [1, 2, 3])
        self.assertEqual(pkg_set.selinux, vmu.PackageSet.SELINUX_DEFAULT, 'Failed to set SELinux default')
        self.assertEqual(pkg_set.java, vmu.PackageSet.OSG_JAVA_DEFAULT, 'Failed to set OSG Java default')


    def test_hashable(self):
        selinux_enabled = vmu.PackageSet('foo', [1, 2, 3], True, True)
        self.assert_(set([selinux_enabled]),
                     'PackageSet.__hash__() broken')
        self.assertEqualWithResults(set([selinux_enabled]),
                                    set([selinux_enabled, selinux_enabled]),
                                    'PackageSet hash equality')

    def test_from_dict(self):
        pkg_set_dict = {'label': 'gums', 'packages': ['osg-gums', 'rsv'], 'selinux': False, 'osg_java': True}
        self.assertEqualWithResults(vmu.PackageSet.from_dict(pkg_set_dict),
                                    vmu.PackageSet('gums', ['osg-gums', 'rsv'], False, True),
                                    'Manually generated PackageSet differs from one generated from a dict')

class TestLoadRunParams(TestVmu):

    param_dir = '../parameters.d'

    def missing_param_section(self, section):
        patch_glob = mock.patch('vmu.glob')
        mock_glob = patch_glob.start()
        mock_glob.return_value = [1]

        params = {'platform': ['foo'], 'sources': ['bar'], 'package_sets': [{'label': 'foo', 'packages': [1, 2, 3]}]}
        params.pop(section, None)

        patch_yaml_load = mock.patch('vmu.yaml.load')
        mock_yaml_load = patch_yaml_load.start()
        mock_yaml_load.return_value = params

        self.addCleanup(mock._patch_stopall)

        with mock.patch('__builtin__.open', mock.mock_open()):
            self.assertRaises(vmu.ParamError, vmu.load_run_params, self.param_dir)

    @mock.patch('vmu.glob')
    def test_no_yaml(self, mock_glob):
        mock_glob.return_value = []
        self.assertRaises(vmu.ParamError, vmu.load_run_params, self.param_dir)

    def test_no_platform_section(self):
        self.missing_param_section('platform')

    def test_no_sources_section(self):
        self.missing_param_section('sources')

    def test_no_package_sets_section(self):
        self.missing_param_section('package_sets')

    def test_actual_param_dir(self):
        params = vmu.load_run_params('../parameters.d')
        self.assert_(params, 'Failed to read parameters.d')
        for param_set in params:
            for pkg_set in param_set['package_sets']:
                self.assert_(isinstance(pkg_set, vmu.PackageSet),
                             'Did not convert package_set dicts into PackageSet objects')

class TestFlattenParams(TestVmu):

    def test_single_file(self):
        run_params = [
            {'platform': ['foo'],
             'sources': ['bar', 'foo'],
             'package_sets':
             [
                 vmu.PackageSet('foo', ['foo', 'bar'])
             ]
            }
        ]
        self.assertEqualWithResults(run_params[0], vmu.flatten_run_params(run_params),
                                    'Unexpectedly modified single yaml file')

    def test_mismatched_tags(self):
        pkgs = ['foo', 'bar']
        run_params = [
            {'package_sets':
             [
                 vmu.PackageSet('foo', pkgs),
                 vmu.PackageSet('bar', pkgs),
             ]
            }
        ]
        self.assertRaises(vmu.ParamError, vmu.flatten_run_params, run_params)

    def test_multi_file_single_param(self):
        list1 = ['foo', 'bar']
        list2 = ['baz']
        run_params = [
            {'platform': list1},
            {'platform': list1},
            {'platform': list2},
        ]
        expected = list1 + list2
        self.assertEqualWithResults(expected, vmu.flatten_run_params(run_params)['platform'],
                                    "Failed to combine multiple files with single 'platforms' section sections")

    def test_multi_file_multi_param(self):
        run_params = [
            {'platform': ['foo'],
             'sources': ['foo', 'bar'],
             'package_sets':
             [
                 vmu.PackageSet('foo', ['foo', 'bar'])
             ]
            },
            {'platform': ['foo'],
             'sources': ['foo', 'bar'],
             'package_sets':
             [
                 vmu.PackageSet('foo', ['foo', 'bar'])
             ]
            }
        ]
        expected = copy.deepcopy(run_params).pop()
        self.assertEqualWithResults(expected, vmu.flatten_run_params(run_params),
                                    'Failed to flatten identical files')

    def test_multi_file_multi_pkg_sets(self):
        set1 = [vmu.PackageSet('All', ['osg-tested-internal']),
                vmu.PackageSet('GridFTP', ['osg-gridftp'])]
        set2 = set1 + [vmu.PackageSet('GUMS', ['osg-gums'])]

        run_params = [{'package_sets': set1},
                      {'package_sets': set2}]

        self.assertEqualWithResults(set2, vmu.flatten_run_params(run_params)['package_sets'],
                                    'Failed to combine multiple files with unique package sets')

class TestPackageMapping(TestVmu):

    foo_pkg_set = ['foo']
    bar_pkg_set = ['bar', 'baz']
    flat_params = {
        'package_sets':
        [
            vmu.PackageSet('foo', foo_pkg_set, java=False),
            vmu.PackageSet('bar', bar_pkg_set, java=False)
        ]
    }

    def test_mapping(self):
        expected = {', '.join(self.foo_pkg_set): 'foo', ', '.join(self.bar_pkg_set): 'bar'}
        self.assertEqualWithResults(expected, vmu.package_mapping(self.flat_params),
                                    'Bad mapping for simple case with single package set')

if __name__ == "__main__":
    unittest.main(verbosity=2)
