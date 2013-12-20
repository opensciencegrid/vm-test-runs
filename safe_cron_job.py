"""
A library for making "safe" cron jobs.
Safety features:
* timing out and aborting after a certain number of minutes
* using locks to prevent concurrent runs
"""
# This library was adapted from oasis-ca-updater

import errno
import fcntl
import os
import pwd
import signal
import smtplib
import socket
import sys
import traceback
from optparse import OptionGroup, OptionParser

# Pylint import checks don't handle conditional imports well
try:
    from email.mime.text import MIMEText # Python 2.6; pylint: disable=F0401,E0611
except ImportError:
    from email.MIMEText import MIMEText # Python 2.4; pylint: disable=F0401,E0611

class AlarmException(Exception):
    "Raised in the alarm handler"
    pass

class LockException(Exception):
    "Raised if another process has the lock"
    pass

class EmailNotifier(object):
    """Class for sending simple email notifications."""

    def __init__(self, recipients, dry_run=False):
        self.recipients = recipients or []
        self.dry_run = dry_run

        username = pwd.getpwuid(os.getuid()).pw_name
        hostname = socket.gethostname()
        self.from_address = username + "@" + hostname

    def send_notification(self, subject, text):
        """Send a notification to the addresses in self.recipients.
        If self.dry_run is true, the email is printed to stdout instead of sent.
        Requires a Mail Transfer Agent running on localhost

        """
        msg = MIMEText(text)

        msg['Subject'] = subject
        msg['To'] = ', '.join(self.recipients)
        msg['From'] = self.from_address

        if self.dry_run:
            print msg.as_string()
        else:
            smtp = smtplib.SMTP('localhost')
            smtp.sendmail(self.from_address, self.recipients, msg.as_string())
            smtp.quit()


class SafeCronJob(object):
    """Primitives for making a safe cron job. Includes functions for setting
    up a timer and a lockfile.

    """
    def __init__(self, timeout_secs, lockfile_path):
        if not isinstance(timeout_secs, int):
            raise TypeError('timeout_secs must be an integer')
        if not isinstance(lockfile_path, str):
            raise TypeError('lockfile_path must be a string')
        if not timeout_secs > 0:
            raise ValueError('timeout_secs must be positive')
        if not lockfile_path:
            raise ValueError('lockfile_path cannot be empty')

        # TODO Additional safety checks:
        # * we must be able to write to lockfile_path
        # * lockfile_path must not be on AFS or any other networked filesystem

        self.timeout_secs = timeout_secs
        self.lockfile_path = lockfile_path
        self.lockfile_filehandle = None

    @staticmethod
    # don't complain about unused arguments
    # pylint: disable=W0613
    def alarm_handler(signum, frame):
        "Handles SIGALRM"
        raise AlarmException()

    def acquire_lock(self):
        filehandle = open(self.lockfile_path, 'w')
        filedescriptor = filehandle.fileno()
        # Get an exclusive lock on the file (LOCK_EX) in non-blocking mode
        # (LOCK_NB), which causes the operation to raise IOError if some other
        # process already has the lock
        try:
            fcntl.flock(filedescriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError, err:
            if err.errno == errno.EWOULDBLOCK:
                raise LockException()
            else:
                raise
        self.lockfile_filehandle = filehandle

    def release_lock(self):
        filedescriptor = self.lockfile_filehandle.fileno()
        fcntl.flock(filedescriptor, fcntl.LOCK_UN)
        self.lockfile_filehandle.close()

    def start_timer(self):
        signal.signal(signal.SIGALRM, SafeCronJob.alarm_handler)
        signal.alarm(self.timeout_secs)

    def stop_timer(self):
        signal.alarm(0)

    def start(self):
        self.acquire_lock()
        self.start_timer()

    def stop(self):
        self.stop_timer()
        self.release_lock()

def type_of_exception(exception_object):
    """Get the type of an exception object as a string or None"""
    if isinstance(exception_object, Exception):
        return str(exception_object.__class__.__name__)

class SafeCronJobWrapper(object):
    """Class for wrapping a function around the safe cron job classes.
    Requires a predefined SafeCronJob object and EmailNotifier object.
    Will run your main function, catch exceptions and send the appropriate
    notifications via the EmailNotifier object.
    """
    def __init__(self, script_name, safe_cron_job, email_notifier):
        self.script_name = script_name
        self.safe_cron_job = safe_cron_job
        self.email_notifier = email_notifier

    def wrap_main(self, main, *args, **kwargs):
        """Start up the safety features, run main, catch exceptions and send
        them as notifications, and clean up afterward
        """
        try:
            try:
                self.safe_cron_job.start()

                return main(*args, **kwargs)
            except AlarmException:
                self.email_notifier.send_notification(
                    '%s timed out' % self.script_name,
                    "Traceback follows:\n%s\n" % traceback.format_exc())
            except LockException:
                self.email_notifier.send_notification(
                    '%s already running; not starting a second time' % self.script_name,
                    "")
            except Exception, err:
                self.email_notifier.send_notification(
                    '%s died with exception %s' % (self.script_name, type_of_exception(err)),
                    "Traceback follows:\n%s\n" % traceback.format_exc())
                raise
        finally:
            self.safe_cron_job.stop()

def get_cron_job_parser_group(parser, default_timeout_mins, default_lockfile_path):
    """Convenience function for setting up the command-line arguments for
    the parameters used by the cron job. Returns an OptionGroup which can be
    added to an OptionParser object 'parser' by running parser.add_option_group(group).
    Requires default values for the timeout (in minutes) and lockfile path, as
    well as a predefined OptionParser object.
    """
    if not isinstance(parser, OptionParser):
        raise TypeError("parser must be an OptionParser")

    cron_group = OptionGroup(parser, "cron job options")
    cron_group.add_option("--timeout", metavar="MINUTES", type="int", default=default_timeout_mins,
                          help="The maximum duration this script should run for, in minutes")
    cron_group.add_option("--notify", metavar="EMAIL", action="append", default=None,
                          help="An email address to send a notification to in case of failure. "
                          "Can be specified multiple times to have multiple recipients")
    cron_group.add_option("--lockfile", metavar="PATH", default=default_lockfile_path,
                          help="Where to place the lock file that prevents multiple copies of "
                          "this script from running simultaneously")
    cron_group.add_option("--nomail", default=False, action="store_true",
                          help="Do not send email, but print what we would have sent")

    return cron_group

def make_wrapper_from_options(options, default_notify=None, script_name=None):
    """Convenience function for taking the options returned by OptionParser
    and creating a SafeCronJobWrapper object based on them.
    In addition to the options object itself, it can also take a default list of
    people to notify in case none were specified in the options. This is a bit
    of an ugly hack.
    """
    script_name = script_name or os.path.basename(sys.argv[0])
    safe_cron_job = SafeCronJob(options.timeout * 60, options.lockfile)
    notify = getattr(options, 'notify', None) or default_notify
    email_notifier = EmailNotifier(notify, options.nomail)

    return SafeCronJobWrapper(script_name, safe_cron_job, email_notifier)

