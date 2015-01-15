#!/usr/bin/env python

#pylint: disable=C0301
#pylint: disable=R0904

import os
import sys
import unittest
from datetime import date

PATHNAME = os.path.realpath('../')
sys.path.insert(0, PATHNAME)

import analyze_job_output

class TestAnalyzeJobOutput(unittest.TestCase):

    def _run_parse_log(self, log_file, expected_status, expected_failures, exceptions_file=None):
        contents = analyze_job_output.read_file(log_file)

        try:
            test_exceptions = analyze_job_output.load_yaml(exceptions_file)
        except TypeError:
            test_exceptions = [('test_04_trace', 'test_55_condorce', date.today(), date.today()),
                               ('test_05_pbs_trace', 'test_55_condorce', date.today(), date.today())]

        status, failures = analyze_job_output.parse_log(contents, test_exceptions)
        self.assertEqual(status, expected_status)
        self.assertEqual(failures, expected_failures)

    def _test_fail_log(self, filename=None):
        # Tests should be marked as failed when there are failures other than ignored failures
        expected_failures = ['test_50_voms|test_06_rfc_voms_proxy_init|TestVOMS|FAIL|-',
                             'test_52_bestman|test_02_copy_local_to_server|TestBestman|FAIL|-',
                             'test_52_bestman|test_03_copy_server_to_local|TestBestman|FAIL|-',
                             'test_52_bestman|test_04_remove_server_file|TestBestman|FAIL|-',
                             'test_55_condorce|test_04_trace|TestCondorCE|FAIL|-',
                             'test_55_condorce|test_05_pbs_trace|TestCondorCE|FAIL|-',
                             'test_56_lcgutil|test_01_copy_local_to_server_lcg_util|TestLCGUtil|FAIL|-',
                             'test_56_lcgutil|test_02_copy_server_to_local_lcg_util|TestLCGUtil|FAIL|-',
                             'test_56_lcgutil|test_03_remove_server_file_lcg_util|TestLCGUtil|FAIL|-',
                             'test_58_gfal2util|test_01_copy_local_to_server_gfal2_util|TestGFAL2Util|FAIL|-',
                             'test_58_gfal2util|test_02_copy_server_to_local_gfal2_util|TestGFAL2Util|FAIL|-',
                             'test_58_gfal2util|test_03_remove_server_file_gfal2_util|TestGFAL2Util|FAIL|-',
                             'test_50_voms|test_07_rfc_voms_proxy_info|TestVOMS|SKIP|no proxy',
                             'test_50_voms|test_08_voms_proxy_check|TestVOMS|SKIP|no proxy']
        self._run_parse_log('fail.log', 'fail', expected_failures, filename)

    def test_read_file(self):
        log_file = analyze_job_output.read_file('pass.log')
        self.assert_(log_file)

    def test_passing_status(self):
        self._run_parse_log('pass.log', 'pass', [])

    def test_fail_status(self):
        self._test_fail_log()

    def test_install_status(self):
        expected_failures = ['special_install|test_03_install_packages|TestInstall|FAIL|-',
                             'special_install|test_04_update_osg_release|TestInstall|SKIP|Install did not succeed']
        self._run_parse_log('install.log', 'install', expected_failures)

    def test_update_status(self):
        expected_failures = ['special_install|test_05_update_packages|TestInstall|FAIL|-']
        self._run_parse_log('update.log', 'update', expected_failures)

    def test_ignored_status(self):
        # Ignored status' should trump cleanup status' since the latter is often due to
        # low priority issues with the test framework
        expected_failures = ['test_55_condorce|test_04_trace|TestCondorCE|FAIL|-',
                             'test_55_condorce|test_05_pbs_trace|TestCondorCE|FAIL|-',
                             'special_cleanup|test_03_remove_packages|TestCleanup|FAIL|-']
        self._run_parse_log('ignore.log', 'ignored', expected_failures)

    def test_cleanup_status(self):
        expected_failures = ['special_cleanup|test_03_remove_packages|TestCleanup|FAIL|-']
        self._run_parse_log('cleanup.log', 'cleanup', expected_failures)

    def test_exceptions_file(self):
        self._test_fail_log('../test-exceptions.yaml')

if __name__ == '__main__':
    SUITE = unittest.makeSuite(TestAnalyzeJobOutput)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
