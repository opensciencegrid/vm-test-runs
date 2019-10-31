Running Tests as VM Jobs
========================

- [Setting up credentials](#setting-up-credentials)
- [Running osg-test in VM Universe](#running-osg-test-in-vm-universe)
- [Troubleshooting](#troubleshooting)
  - [Missing unicode fonts](#missing-unicode-fonts)
  - [Interactively connecting to a VM](#interactively-connecting-to-a-vm)

This repository drives the OSG Software nightly tests. Whenever updating [osg-run-tests](osg-run-tests), make sure to update the copy in `/usr/bin/` on `osghost`.

Setting up credentials
----------------------

**Note:** This one time setup must be performed before submitting any test jobs.

1.  Contact Brian L. or Tim C. to have an account created on `osghost.chtc.wisc.edu`
2.  SSH to `osghost` (you will need to do this from the UW-Madison network) and create a password-less SSH key:

        [user@client ~]$ ssh-keygen -C 'VMU test result upload key for <USER>@osghost' -f ~/.ssh/test_result_upload.key

3.  Contact BrianL or Mat with your public key. They will add your public key to the `authorized_keys` file of the `cndrutil` user on `ingwe`.
4.  Add `ingwe's` pubkey to your `known_hosts` file by initiating an SSH connection. You do not need to login:

        [user@client ~]$ ssh ingwe.cs.wisc.edu
        The authenticity of host 'ingwe.cs.wisc.edu (128.105.121.64)' can't be established.
        RSA key fingerprint is 8c:44:ac:fd:c5:9e:1c:7a:c1:e1:42:40:c3:e5:4b:fc.
        Are you sure you want to continue connecting (yes/no)? yes
        Warning: Permanently added 'ingwe.cs.wisc.edu,128.105.121.64' (RSA) to the list of known hosts.
        blin@ingwe.cs.wisc.edu's password:

Running osg-test in VM Universe
-------------------------------

The procedure explained in this section replaces [this](https://opensciencegrid.github.io/technology/software/development-process/) if and only if there are functional tests for each package being tested.

1.  From `osghost.chtc.wisc.edu`, make and populate a test run directory:

        [user@client ~]$ osg-run-tests '<RUN DESCRIPTION>'
2.  Change to the test run directory (see output of osg-run-tests)
3.  If you need to change `osg-test`, use one of the methods below:
    -   Make changes to a github fork of osg-test and prepend the source lines in the yaml parameters files (see below) with the following: `<GITHUB ACCOUNT>:<BRANCH OF OSG-TEST>;`
    -   Edit `test-changes.patch` with test module and library changes and/or edit `osg-test.patch` with osg-test script changes. These patches can be generated with `git diff`.

4.  If there are test failures that shouldn't be marked as failures in the reporting, edit `test-exceptions.yaml` you can add test failures to ignore with the following format:

        # - [test_function, test_module, start date, end date].
        [test_04_trace, test_55_condorce, 2014-12-01, 2015-01-14]

5.  If you want to change test run parameters, edit `parameters.d/*.yaml`, or add/remove yaml files with the same format.
    Each file in `parameters.d` generates an osg-test run for every possible combination of the `platforms`, `sources`,
    and `package_sets` parameters in that file.
    1.  To change the distribution, modify the `platforms` section. Accepted values are listed below:

              platforms:
                - centos_6_x86_64
                - rhel_6_x86_64
                - sl_6_x86_64
                - centos_7_x86_64
                - rhel_7_x86_64
                - sl_7_x86_64

    2.  To change the repos that packages are installed from, edit the sources section, which has the following format:

            [<GITHUB ACCOUNT>:<BRANCH OF OSG-TEST>;] <INITIAL OSG VERSION>; <INTIAL YUM REPO> [>] [<UPDATE OSG VERSION>/][<UPDATE YUM REPO>]
            # Run osg-test from the 'opensciencegrid' github account using the 'master' branch (<https://github.com/opensciencegrid/osg-test.git>) with packages from 3.2-testing
            opensciencegrid:master; 3.2; osg-testing
            # Run osg-test (from 3.1-minefield) with packages from 3.1-release
            3.1; osg
            # Run osg-test (from 3.1-minefield) with packages from 3.1-testing that are then upgraded to 3.2-testing
            3.1; osg-testing > 3.2/osg-testing
            # Run osg-test (from 3.2-minefield) with packages from 3.2-release and 3.2-testing that are then upgraded to 3.3-testing and 3-3-upcoming-testing
            3.2; osg, osg-testing > 3.3/osg-testing, osg-upcoming-testing

    3. The `package_sets` section controls the packages that are installed, the label used for reporting, whether or not SELinux is enabled (default: disabled), and whether or not to pre-install the OSG Java packages (default: enabled): 

            package_sets:
            #### Required ####
            # label - used for reporting, should be consistent across param files
            # packages - list of packages to install in the test run
            #### Optional ####
            # selinux - enable SELinux for the package set, otherwise Permissive mode (default: True)
            # osg_java - Pre-install OSG java packages (default: False)
            ##################
            - label: All
              packages:
                - osg-tested-internal
            - label: HTCondor
              packages:
                - condor.x86_64
                - osg-ce-condor
                - rsv

    4. The test infrastructure can read multiple yaml files in `parameters.d`, which allows you to run different,
       mutually exclusive tests.
       For example, if you wanted to test 3.3 development on EL7 in addition to the standard tests, you could add the
       following to a file in `parameters.d`:

            platform:
              - centos_7_x86_64
              - sl_7_x86_64

            sources:
              - opensciencegrid:master; 3.3; osg-development

            package_sets:
              - label: All
                packages:
                  - osg-tested-internal
              # Explicitly add GRAM packages since they were dropped from osg-ce (SOFTWARE-2278, SOFTWARE-2291)
              - label: All + GRAM (3.2)
                packages:
                  - osg-tested-internal-gram
              - label: HTCondor
                packages:
                  - condor.x86_64
                  - osg-ce-condor
                  - rsv
              - label: GridFTP
                packages:
                  - osg-gridftp
                  - edg-mkgridmap
                  - rsv
              - label: BeStMan
                packages:
                  - osg-se-bestman
                  - rsv
              - label: VOMS
                packages:
                  - osg-voms
                  - rsv
              - label: GUMS
                packages:
                  - osg-gums
                  - rsv

6.  Submit the test run (you must submit the DAG from the run directory):

        [user@client ~]$ ./master-run.dag

7.  Monitor the test run (as desired):

        [user@client ~]$ condor_q -dag

8.  When the test run finishes, an email will go out to members of the software team (hardcoded in `email-analysis`). In the e-mail will be links to the web interface which will often not work immediately because the test results only get transferred over every 15 minutes.

Troubleshooting
---------------

### Missing Unicode Fonts

The HTML reports for the testing results utilize unicode characters (namely the padlock to represent that SELinux was enabled). If these characters are appearing as the character code in a block, that means that the font you're using does not support these characters. To render these characters properly, perform the following steps:

1.  Download a suitable Unicode Emoji font. We have had success with the "Noto Emoji" font available from <https://www.google.com/get/noto/>
2.  Create a `~/.fonts/` dir if one does not already exist
3.  Copy the `.ttf` file from the downloaded font `.zip` file into `~/.fonts/`
4.  Run `fc-cache -f`

### Interactively connecting to a VM

Unfortunately, VM Universe jobs don't have the ssh\_to\_job capacity that's available to other Condor jobs so if we need to investigate test failures in VMU, we'll have to spin up our own VM's. We can do this by taking the images that Neil automatically generates and create new ones from them that don't automatically run osg-test (Right now, Neil has to manually copy over the updated images. Eventually, we should have an automated way to get the most updated VMU images). Here are the steps you need to follow to set up your own VM:

1.  Grab the make-interactive-image from git:

        git clone https://github.com/opensciencegrid/vm-test-runs.git
2.  Run `make-interactive-image` using the flavor and version of Linux you need, VMU images are in `/mnt/gluster/chtc/VMs/` (NOTE: the output image needs to be in a directory that's readable by the `qemu` user):

        vm-test-runs/make-interactive-image /mnt/gluster/chtc/VMs/<INPUT IMAGE> <OUTPUT IMAGE>
3.  Make a copy of `libvirt-template.xml` and edit the `@DOMAIN@` and `@IMAGEFILE@` to a name that will be used by virsh and the path to the image file you created in the previous step
4.  Define and start the VM with your copy of the xml file:

        virsh create <XML FILE>
5.  Connect to the VM (consult BrianL, Mat or Carl for the password). You can use either the domain name or the ID returned by `virsh list`:

        virsh console <DOMAIN>
6.  Cleanup the VM. You can use either the domain name or the ID returned by `virsh list`:

        virsh destroy <DOMAIN>

