#!/usr/bin/python3

import glob
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, date
import yaml

import vmu

def run_command(command, shell=False):
    # Preprocess command
    if shell:
        if not isinstance(command, str):
            command = ' '.join(command)
    elif not (isinstance(command, list) or isinstance(command, tuple)):
        raise TypeError('Need list or tuple, got %r' % command)

    # Run and return command
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)
    (stdout, stderr) = p.communicate()
    return (p.returncode, stdout, stderr)

def read_file(path):
    data_file = open(path, 'r')
    data = data_file.read()
    data_file.close()
    return data

def load_yaml(filename):
    yaml_file = read_file(filename)
    return yaml.load(yaml_file)

def re_extract(regexp, data, flags=0, default=None, group=None):
    m = re.search(regexp, data, flags)
    if m is None:
        return default
    elif group is None:
        return m.groups()
    else:
        return m.group(group)

def extract_inet_address(run_job_log):
    eth0_block = re_extract(r'^\d:\s*eth0:(.*?)(?:^\d)', run_job_log, re.MULTILINE | re.DOTALL, group=1)
    ens3_block = re_extract(r'^\d:\s*ens3:(.*?)(?:^\d)', run_job_log, re.MULTILINE | re.DOTALL, group=1)
    enp1s0_block = re_extract(r'^\d:\s*enp1s0:(.*?)(?:^\d)', run_job_log, re.MULTILINE | re.DOTALL, group=1)
    if eth0_block:
        return re_extract(r'^\s+inet\s+(.*?)\/', eth0_block, re.MULTILINE, group=1)
    elif ens3_block:
        return re_extract(r'^\s+inet\s+(.*?)\/', ens3_block, re.MULTILINE, group=1)
    elif enp1s0_block:
        return re_extract(r'^\s+inet\s+(.*?)\/', enp1s0_block, re.MULTILINE, group=1)
    else:
        return None

def extract_last(run_job_log, regexp):
    all_installs = re.findall(regexp, run_job_log, re.MULTILINE)
    if len(all_installs) == 0:
        return None
    return all_installs[-1]

def write_yaml_value(value):
    if value is None:
        result = '~'
    elif isinstance(value, str):
        if re.search(r"['\"\n|>,#\[\]]", value):
            result = "'%s'" % value.replace("'", "''").replace('\n', '\\n')
        else:
            result = value
    elif isinstance(value, list):
        result = ''
        if len(value) > 0:
            for element in value:
                result += '\n    -%s' % write_yaml_value(element)
    else:
        result = str(value)
    if '\n' in result:
        return result
    return ' ' + result

def write_yaml_mapping(data, key):
    if key in data:
        if key in ('job_serial', 'job_id'):
            print(('  %s: \'%s\'' % (key, data[key])))
        else:
            value = data[key]
            print(('  %s:%s' % (key, write_yaml_value(value))))

def write_yaml(data):
    print('-')
    for key in sorted(data.keys()):
        write_yaml_mapping(data, key)

def write_failure_and_exit(data, status, message, extra=None):
    data['run_status'] = status
    data['run_summary'] = message
    if extra is not None:
        data['run_details'] = extra
    write_yaml(data)
    sys.exit(0)

def parse_log(osg_test_log, test_exceptions, components):
    # Extract problems
    today = date.today()
    run_status = ''
    problems = []
    ignored_failures = 0
    cleanup_failures = 0
    for m in re.finditer(r'^(ERROR|FAIL): (\w+) \(osgtest\.tests\.(\w+)\.(\w+).*\)', osg_test_log, re.MULTILINE):
        status, function, module, module_name = m.groups()
        if module == 'special_cleanup':
            cleanup_failures += 1
        if test_exceptions:
            for exception in test_exceptions:
                ex_function, ex_module, ex_start, ex_finish = exception
                if status == 'FAIL' and ex_function == function and ex_module == module and \
                   today >= ex_start and today <= ex_finish:
                    ignored_failures += 1
        problems.append('|'.join((module, function, module_name, status, '-')))

    if ignored_failures and ignored_failures == len(problems) - cleanup_failures:
        # Runs consisting only of 'ignored' and 'cleanup' failures should be marked
        # as 'ignored' since 'cleanup' failures are mostly due to errors in the
        # test framework and are thus less interesting. Checking that ignored_
        # failures is non-zero ensures that we don't capture cleanup-only failures.
        run_status = 'ignore'
    elif all('special_cleanup' in problem for problem in problems) and problems: # all() returns true for empty lists!
        run_status = 'cleanup'
    elif any('_update_' in problem for problem in problems):
        run_status = 'update'
    elif any('install_packages' in problem for problem in problems):
        run_status = 'install'

    m = re.search(r'^=+\nBAD SKIPS:\n-+\n(.*?)\n\n', osg_test_log, re.MULTILINE | re.DOTALL)
    if m is not None:
        for n in re.finditer(r'^(\w+) \(osgtest\.tests\.(\w+)\.(\w+)\) (.*)$', m.group(1), re.MULTILINE):
            function, module, module_name, comment = n.groups()
            problems.append('|'.join((module, function, module_name, 'SKIP', comment)))
    if not problems:
        run_status = 'pass'
    elif not run_status: # catch missed failures
        run_status = 'fail'

    okskips = {}
    m = re.finditer(r'\S+ \(osgtest\.tests\.([^\.]+).*okskip$', osg_test_log, re.MULTILINE)
    if m is not None:
        for module in m:
            try:
                tags = components[module.group(1)]
            except KeyError:
                continue
            try:
                for tag in tags:
                    okskips[tag] += 1
            except KeyError:
                okskips[tag] = 1
                
    if re.search('AssertionError: Retries terminated after timeout period', osg_test_log, re.MULTILINE):
        run_status += ' yum_timeout'

    return run_status, problems, okskips

# ======================================================================================================================

if __name__ == '__main__':
    # Process command-line arguments
    if len(sys.argv) != 3:
        print(('usage: %s SERIAL JOBID' % os.path.basename(sys.argv[0])))
        sys.exit(1)
    job_serial = sys.argv[1]
    job_id = sys.argv[2]
    
    # Start hash
    data = {
        'job_serial': job_serial,
        'job_id': job_id,
        'run_directory': os.getcwd()
        }
    
    # Construct expected directory name
    test_run_dir = 'output-' + job_serial
    if not os.path.exists(test_run_dir):
        sys.exit("Missing output dir '%s'" % test_run_dir)
    
    # Read condor_history output for transfer-in time (in seconds)
    (rc, stdout, _) = run_command(('condor_history', '-format', '%d\\n ', 'JobCurrentStartExecutingDate - JobCurrentStartDate',
                                   job_id, '-match', '1'))
    if rc == 0:
        data['transfer_in'] = re_extract(r'^(\S+)$', stdout, group=1)
    
    # Separate query for hostname in case the JobAd's missing attributes
    (rc, stdout, _) = run_command(('condor_history', '-format', '%s\\n', 'LastRemoteHost', job_id, '-match', '1'))
    if rc ==0:
        data['host_name'] = re_extract(r'^\S+@(\S+)$', stdout, group=1)
    try:
        data['host_address'] = socket.gethostbyname(data['host_name'])
    except TypeError:
        # Missing hostname from condor_history
        data['host_name'] = 'unavailable'
        data['host_address'] = 'unavailable'
    except socket.gaierror:
        # When gethostbyname can't find address by hostname1
        data['host_address'] = 'unavailable'
    
    # Read osg-test.conf
    conf_file_name = os.path.join(test_run_dir, 'input', 'osg-test.conf')
    conf_file = read_file(conf_file_name)
    data['param_sources'] = re_extract(r'^sources\s*=\s*(.*)$', conf_file, re.MULTILINE, group=1)
    data['param_packages'] = re_extract(r'^packages\s*=\s*(.*)$', conf_file, re.MULTILINE, group=1)
    data['selinux'] = re_extract(r'^selinux\s*=\s*(.*)$', conf_file, re.MULTILINE, group=1)

    # Read free size left in the IO image
    io_free_size_file = os.path.join(test_run_dir, 'io_free_size')
    data['io_free_size'] = read_file(io_free_size_file)

    # Read run-job.log
    run_job_logfile = os.path.join(test_run_dir, 'run-job.log')
    run_job_log = read_file(run_job_logfile)
    
    # Get VM creation date
    data['vm_creation_date'] = re_extract(r'cat /etc/creation_date\n(.*?)\n==> OK', run_job_log, group=1)

    # Get and simplify OS release string
    os_long_string = re_extract(r'cat /etc/redhat-release\n(.*?)\n==> OK', run_job_log, group=1)
    os_string = re.sub(r'release\s+', '', os_long_string)
    os_string = re.sub(r'\s*\(.*\)$', '', os_string)
    data['os_release'] = os_string

    # Get the arch of the host
    # This can currently be found by RPM names in the logs, but we might want
    # to make it a first class log message
    platform = (re_extract(r'el[0-9]\.(aarch64|x86_64).rpm', run_job_log, group=1) or
                re_extract(r'(aarch64|x86_64)', run_job_log, group=1))
    data['platform'] = platform
    
    # Look for whole-run failures
    inet_address = extract_inet_address(run_job_log)
    if inet_address is None:
        write_failure_and_exit(data, 1, 'No apparent IP address')
    data['guest_address'] = inet_address
    
    # See if the rpm install of epel-release failed
    failed_epel_install = re.search(r'Could not install EPEL repository', run_job_log)
    if failed_epel_install:
        write_failure_and_exit(data, 1, 'rpm install of epel-release failed')

    # See if the final yum install of osg-test failed
    final_osgtest_install = extract_last(run_job_log, r'^.*install osg-test(?:.*\n)*?^==>.*$')
    if final_osgtest_install is not None:
        install_result = re_extract(r'^==> (\w+)', final_osgtest_install, re.MULTILINE, group=1)
        if install_result != 'OK':
            write_failure_and_exit(data, 1, 'yum install of osg-test failed', final_osgtest_install)

    # Extract osg-test source string
    for package in ['osg-test', 'osg-ca-generator']:
        source_re = r'^%s source: (.*)$' % package
        data[package.replace('-', '_') + '_version'] = re_extract(source_re, run_job_log, re.MULTILINE,
                                                                  default='(unknown)', group=1)

    # Read osg-test output
    osg_test_logfile_list = glob.glob(os.path.join(test_run_dir, 'output', 'osg-test-*.log'))
    if len(osg_test_logfile_list) == 0:
        write_failure_and_exit(data, 1, 'No osg-test-DATE.log file found')
    osg_test_logfile = osg_test_logfile_list[0]
    osg_test_log = read_file(osg_test_logfile)
    data['run_status'] = 0
    data['osg_test_logfile'] = osg_test_logfile
    
    data['osg_test_status'], data['tests_messages'], data['ok_skips'] = parse_log(osg_test_log,
                                                                                  load_yaml(vmu.TEST_EXCEPTIONS),
                                                                                  load_yaml(vmu.COMPONENT_TAGS))
  
    # Extract start time
    data['start_time'] = re_extract(r'^Start time: (.*)$', osg_test_log, re.MULTILINE, group=1)
    
    # Determine if the run timed out which can be found at the end of the log
    timeout_re = re.compile('Caught alarm:\n.*message: (.*):')
    reversed_osg_test_log = '\n'.join(reversed(osg_test_log.split('\n'))) 
    timeout_match = timeout_re.search(reversed_osg_test_log, re.MULTILINE)
    if timeout_match:
        data['osg_test_status'] = 'timeout'
    
        end_time = datetime.strptime(timeout_match.group(1), '%Y-%m-%d %H:%M:%S')
        start_time = datetime.strptime(data['start_time'], '%Y-%m-%d %H:%M:%S')
        data['run_time'] = end_time - start_time
    
        last_test_re = re.compile(r'File .*osgtest\/tests\/(.*)\".*in (.*)')
        last_test = last_test_re.search(reversed_osg_test_log)
        failed_module, failed_test = last_test.groups()
        data['timeout_test'] = failed_test + ' (' + failed_module + ')'
    
    # Extract summary statistics
    summary_re = re.compile(r'(Ran \d+ tests in .*)\s+((?:OK|FAILED)\s*\([^)]+\))\n(?!STDOUT)')
    summary_lines = re_extract(summary_re, osg_test_log)
    data['tests_total'] = data['tests_failed'] = data['tests_error'] = data['tests_bad_skip'] = data['tests_ok_skip'] = 0
    if summary_lines is None:
        data['run_time'] = 0.0
    else:
        tests_total, run_time = re_extract(r'Ran (\d+) tests in ([\d.]+)s', summary_lines[0])
        data['tests_total'] = int(tests_total)
        data['run_time'] = float(run_time)
        summary = summary_lines[1]
        overall, details = re_extract(r'(OK|FAILED)\s*\(([^)]+)\)', summary_lines[1])
        for detailed_count in re.split(r'\s*,\s*', details):
            label, value = detailed_count.split('=')
            if label == 'failures': data['tests_failed'] = int(value)
            elif label == 'errors': data['tests_error'] = int(value)
            elif label == 'badSkips': data['tests_bad_skip'] = int(value)
            elif label == 'okSkips': data['tests_ok_skip'] = int(value)
            else: raise ValueError()
    data['tests_ok'] = data['tests_total'] - \
      (data['tests_failed'] + data['tests_error'] + data['tests_bad_skip'] + data['tests_ok_skip'])

    if data['tests_ok'] == 0 and data['osg_test_status'] != 'timeout':
        data['osg_test_status'] = 'fail'

    write_yaml(data)
