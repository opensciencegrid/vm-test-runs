Running Tests as VM Jobs
========================

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

The procedure explained in this section replaces [this](https://twiki.opensciencegrid.org/bin/view/SoftwareTeam/SoftwareDevelopmentProcess) if and only if there are functional tests for each package being tested.

1.  From `osghost.chtc.wisc.edu`, make and populate a test run directory:

        [user@client ~]$ osg-run-tests '<RUN DESCRIPTION>'
2.  Change to the test run directory (see output of osg-run-tests)
3.  If you need to change `osg-test`, use one of the methods below:
    -   Make changes to a github fork of osg-test and prepend the source lines in the yaml parameters files (see below) with the following: `<GITHUB ACCOUNT>:<BRANCH OF OSG-TEST>;`
    -   Edit `test-changes.patch` with test module and library changes and/or edit `osg-test.patch` with osg-test script changes. These patches can be generated with `git diff`.

4.  If there are test failures that shouldn't be marked as failures in the reporting, edit `test-exceptions.yaml` you can add test failures to ignore with the following format:

        # - [test_function, test_module, start date, end date].
        [test_04_trace, test_55_condorce, 2014-12-01, 2015-01-14]

5.  If you want to change test run parameters, edit `parameters.d/osg32.yaml`, `parameters.d/osg33-el6.yaml`, or `parameters.d/osg33-el7.yaml` or you can add/remove yaml files with the same format. Each file in `paramaters.d` generates an osg-test run for every possible combination of the `platforms`, `sources`, and `package_sets` parameters in that file.
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
            # Run osg-test with packages from 3.1-release
            3.1; osg
            # Run osg-test with packages from 3.1-testing that are then upgraded to 3.2-testing
            3.1; osg-testing > 3.2/osg-testing
            # Run osg-test with packages from 3.2-release and 3.2-testing that are then upgraded to 3.3-testing and 3-3-upcoming-testing
            3.2; osg, osg-testing > 3.3/osg-testing, osg-upcoming-testing
            # Run osg-test from the 'opensciencegrid' github account using the 'master' branch (<https://github.com/opensciencegrid/osg-test.git>) with packages from 3.2-testing
            opensciencegrid:master; 3.2; osg-testing
    3. The `package_sets` section controls the packages that are installed, the label used for reporting, whether or not SELinux is enabled (default: disabled), and whether or not to pre-install the OSG Java packages (default: enabled): 

            package_sets:
            #### Required ####
            # label - used for reporting, should be consistent across param files
            # packages - list of packages to install in the test run
            #### Optional ####
            # selinux - enable SELinux for the package set, otherwise Permissive mode (default: False)
            # osg_java - Pre-install OSG java packages (default: True)
            ##################
            - label: All
              selinux: False
              osg_java: True
              packages:
                - osg-tested-internal
            - label: HTCondor
              selinux: False
              osg_java: True
              packages:
                - condor.x86_64
                - osg-ce-condor
                - rsv
    4. The test infrastructure can read multiple yaml files in `parameters.d`, which allows you to run different, mutually exclusive tests. For example, if you wanted to test 3.3 development on EL7 in addition to the standard tests, you could add the following to a file in `paramaters.d`:

            platform:
              - centos_7_x86_64
              - sl_7_x86_64

            sources:
              - 3.3; osg-development

            package_sets:
              - label: All
                selinux: False
                osg_java: True
                packages:
                  - osg-tested-internal
              # Explicitly add GRAM packages since they were dropped from osg-ce (SOFTWARE-2278, SOFTWARE-2291)
              - label: All + GRAM (3.2)
                selinux: False
                osg_java: True
                packages:
                  - osg-tested-internal-gram
              - label: HTCondor
                selinux: False
                osg_java: True
                packages:
                  - condor.x86_64
                  - osg-ce-condor
                  - rsv
              - label: GridFTP
                selinux: True
                osg_java: True
                packages:
                  - osg-gridftp
                  - edg-mkgridmap
                  - rsv
              - label: BeStMan
                selinux: False
                osg_java: True
                packages:
                  - osg-se-bestman
                  - rsv
              - label: VOMS
                selinux: False
                osg_java: True
                packages:
                  - osg-voms
                  - rsv
              - label: GUMS
                selinux: False
                osg_java: True
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

Notes about running osg-test as VM jobs
---------------------------------------

This page is my (cat) collected notes and ideas about running osg-test runs as VM jobs, either locally (e.g., CHTC) or in OSG.

### Using VM Universe in HTCondor

For HTCondor 8.4, the documentation for VM universe is in [section 2.11](http://research.cs.wisc.edu/htcondor/manual/v8.4/2_11Virtual_Machine.html) of [the manual](http://research.cs.wisc.edu/htcondor/manual/v8.4/ref.html).

Some quick notes:

-   `universe = vm`
-   `executable` is just a label
-   Omit `input`, `output`, and `error`, as they are not used and will cause submit failures
-   Must select a `vm_type` of `vmware`, `xen`, or `kvm`

### Using VM Universe in CHTC

The only VM universe support in CHTC was using a now-archaic version of [VMware](http://www.vmware.com); this was set up in support of the Thomas Jahns lab. Essentially, in July 2013, there is no current support. However, the CHTC infrastructure team is interested in adding real support for at least kvm.

On 3 July 2013, Nate Yehle proposed working with us to add kvm support in stages. Roughly:

1.  Nate will set up kvm on `osghost.chtc.wisc.edu` to create a playground
2.  Nate will show TimC how to run an arbitrary image on `osghost`
3.  TimC will iterate on a basic SL6 VM image (probably using BoxGrinder, see below) until it starts, runs a simple process, and exits cleanly
4.  Nate and TimC will work together to identify and solve any issues with the test VM image, especially concerning networking
5.  Nate will set up one CHTC node with kvm support
6.  TimC will try to run the test VM image on the CHTC node using HTCondor
7.  Iterate and grow as needed and possible

### Selecting a VM Type

On 2 July 2013, Jaime and ToddM suggested focusing on kvm as the VM type. People on the team have the most experience with kvm. Avoid VMware (no reasons recorded).

To run our test code, use the `rc.local` system (file? directory?). It should run last in the startup sequence, after all other services are running. Ask ToddM for help, if needed. Once the tests are done, shut down the VM from the same script.

### Creating VM Images

At the heart of each test run will be a base OS image, containing a relatively bare-bones OS installation along with a few key files to set up networking, users, certificates, etc.

The base images, one for each platform on which we wish to test, will need to be recreated periodically, say once a week, and reused many times. Thus, the process of creating a base OS image must be scriptable. There are tools to create Linux installations on VM images:

-   John Hover has used [BoxGrinder](http://boxgrinder.org) to do his virtualization work. It has not received an update since mid-2012, but has been sufficient for his needs.
-   [Oz](https://github.com/clalancette/oz/wiki) is newer and support some but not all of BoxGrinder’s features. Tony Tiradani at Fermi uses it.
-   [Image Factory](http://imgfac.org) builds on Oz by adding features to prepare and install VM images for cloud deployment. It is available via RPM on EL 6, Fedora 16, and Fedora 17 platforms from their own repository, as described in [the installation documentation](http://imgfac.org/documentation/install.html).

John H. (11 July 2013) noted that BoxGrinder may run only on the latest Fedora releases, such as 17 and 18; I did not check whether this is true. Also, John noted that he had some problems with BoxGrinder: He could not install both x86-64 and i386 RPMs at the same time, due to limitations in the tool; and there were some issues with EC2, but they would not affect us. John’s BoxGrinder patches are available in his source code repository.

One other thing to think about: BoxGrinder appliance files are fairly simple to understand and reference files contained in the same directory. However, imagefactory uses one giant XML file, with all installed files inlined. Yuck!

Tony Tiradani at Fermi also has experience with creating VM images. He uses Oz, and [has a GitHub repository](https://github.com/holzman/gwms-cloud-vms/tree/development) with an example of his TDL file.

[Another document](http://docs.openstack.org/trunk/openstack-image/content/ch_creating_images_automatically.html), on the OpenStack site, gives an example of using Oz with EPEL.

If there are performance issues with transferring this image, likely to be 4GB or so, the CHTC infrastructure folks could set up some kind of caching, possibly via the Ken Hahn Filesystem.

#### Commands

##### Oz

``` screen
oz-install -d 4 -p -u -x oz-generated-libvirt.xml sl64.tdl
```

-   The `-d 4` option yields maximum debugging output
-   The `-p` option removes the existing guest image file
-   The `-u` option runs the image customization steps (after installation is done)
-   The argument is the name of the TDL XML file

##### Virsh

To load the definition of the guest into virsh:

``` screen
virsh define cat-libvirt.xml
```

-   The second argument is the name of the libvirt domain definition file, as documented [on the libvirt website](http://libvirt.org/formatdomain.html). It is an XML file that defines what the VM guest configuration, including things like the guest name, memory size, VM image(s), networking configuration, etc.

To start the guest:

``` screen
virsh start cat.chtc.wisc.edu
```

-   The second argument is the guest name, as defined in the domain definition file.

To stop the guest, as though disconnecting the power:

``` screen
virsh destroy cat.chtc.wisc.edu
```

-   The second argument is the guest name, as defined in the domain definition file.

To remove the definition of the guest from virsh:

``` screen
virsh undefine cat.chtc.wisc.edu
```

-   The second argument is the guest name, as defined in the domain definition file.

#### Configuring for a Static IP Address

To make an image that will run as cat.chtc.wisc.edu, I need to tell both kvm (externally, on the host) and the image the same fixed MAC address. From within the original cat.chtc.wisc.edu machine, I found that `ifconfg` reports `eth0` as the primary interface. So this file:

    /etc/sysconfig/network-scripts/ifcfg-eth0

needs to contain:

    DEVICE=eth0
    ONBOOT=yes
    HWADDR=00:16:3E:45:66:99
    TYPE=Ethernet
    BOOTPROTO=dhcp

#### Hostname and Host Certificates

The test runs will need a valid host certificate. How to accomplish this?

Jaime and ToddM suggested getting a single, static hostname from the CSL. Then, the networking system in the base OS images would be set up such that this name would resolve, but only on the VM itself, not going out to the network. Then, we could request a host certificate from DigiCert for this fixed hostname, and that host certificate would be shipped with the base OS VM image. Jaime and ToddM know how to set up the fake hostname lookups in the VM configuration.

### Handling Input and Output

To handle input and output, Jaime and ToddM recommended having separate, small image files for them. Thus, two extra images, beyond the OS base install itself, may be needed:

-   An input image, containing only a single text file with test run conditions.
-   An output image, initially empty and for saving the output log file(s). This image would be the only file transferred back from the run.

The `qemu-img` tool make images and may be sufficient for the input and output images.

Alternatively, John (11 July 2013) noted that there are tools designed for supplying a limited amount of input to an otherwise static VM image. He called this the “HEPIX contextualization approach”, although the HEPIX system is just one implementation. One possibility is the `cloud-init` package from Ubuntu, available on all Linux systems that we care about. I found [a project page](https://launchpad.net/cloud-init) and [some documentation](http://cloudinit.readthedocs.org/en/latest/).

#### libguestfs

To get `guestfish` and other tools, I had to install an extra package:

``` screen
yum install libguestfs-tools-c
```

This brought along another package:

``` screen
Installed:
  libguestfs-tools-c.x86_64 1:1.16.34-2.el6

Dependency Installed:
  libconfig.x86_64 0:1.3.2-1.1.el6
```

To get `virt-make-fs` (recommended by Dave B.), there was another install:

``` screen
yum install libguestfs-tools
```

More packages:

``` screen
Installed:
  libguestfs-tools.x86_64 1:1.16.34-2.el6

Dependency Installed:
  perl-Sys-Guestfs.x86_64 1:1.16.34-2.el6
  perl-Sys-Virt.x86_64 0:0.9.10-4.el6
  perl-XML-Parser.x86_64 0:2.36-7.el6
  perl-XML-Writer.noarch 0:0.606-6.el6
  perl-XML-XPath.noarch 0:1.13-10.el6
  perl-libintl.x86_64 0:1.20-1.el6
```

##### Creating the Input/Output Image

1.  Create an input directory:

        mkdir input
2.  Create an input options file in `input/options.txt`:

        --add-user --dump-output --verbose --install=ndt
3.  Make the input/output image file (raw format):

        virt-make-fs --size=1M input /var/lib/libvirt/images/vm-io-disk.raw

##### Getting Files from the Image Manually

1.  Create a mount point:

        mkdir /mnt/output
2.  Mount the input/output image locally:

        mount -o loop /var/lib/libvirt/images/vm-io-disk.raw /mnt/stuff
3.  Copy files to local disk:

        cp -p /mnt/output/*.log output/
4.  Unmount the input/output image:

        umount /mnt/stuff

##### Getting Files from the Image Automatically

``` screen
guestfish --ro --add vm-io-disk.raw --mount /dev/vda:/ download /osg-test-20130802.log osg-test-20130802.log
```

### Interactively connecting to a VM

Unfortunately, VM Universe jobs don't have the ssh\_to\_job capacity that's available to other Condor jobs so if we need to investigate test failures in VMU, we'll have to spin up our own VM's. We can do this by taking the images that Neil automatically generates and create new ones from them that don't automatically run osg-test (Right now, Neil has to manually copy over the updated images. Eventually, we should have an automated way to get the most updated VMU images). Here are the steps you need to follow to set up your own VM:

1.  Grab the make-interactive-image from git:

        git clone git@github.com:opensciencegrid/vm-test-runs.git
2.  Run `make-interactive-image` using the flavor and version of Linux you need, VMU images are in `/kvm` (NOTE: the output image needs to be in a directory that's readable by the `qemu` user):

        vm-test-runs/make-interactive-image /kvm/<INPUT IMAGE> <OUTPUT IMAGE>
3.  Make a copy of `/kvm/libvirt-template.xml` and edit the `@DOMAIN@` and `@IMAGEFILE@` to a name that will be used by virsh and the path to the output file you created in the previous step:

        <domain type="kvm">

        <name>@DOMAIN@</name>

        <memory unit="KiB">4145152</memory>
        <vcpu>1</vcpu>
        <os>
          <type>hvm</type>
          <boot dev="hd"/>
        </os>
        <features><acpi/></features>

        <devices>

          <emulator>/usr/libexec/qemu-kvm</emulator>

          <disk type="file" device="disk">
            <source <file="@IMAGEFILE@"/>
            <target dev="hda" bus="virtio"/>
          </disk>

          <interface type="bridge">
            <mac address="00:16:3e:45:66:99"/>
            <source bridge="br0"/>
            <target dev="vnet1"/>
            <model type="virtio"/>
          </interface>

          <graphics type="vnc" autoport="yes" listen="128.105.244.224"/>

          </devices>

        </domain>

4.  Edit the init script that kicks off tests to not shutdown the machine:
    1.  Run `virt-copy-out -a <IMAGEFILE> /etc/osg-test.init /tmp` where `IMAGEFILE` is your disk image from step 2
    2.  Edit `/tmp/osg-test.init` and put `exit 0` right after the mount command
    3.  Run `virt-copy-in -a <IMAGEFILE> /tmp/osg-test.init /etc`
5.  Define and start the VM with your copy of the xml file:

        virsh create <XML FILE>
6.  Connect to the VM (consult BrianL, Mat or Carl for the password). You can use either the domain name or the ID returned by `virsh list`:

        virsh console <DOMAIN>
7.  Cleanup the VM. You can use either the domain name or the ID returned by `virsh list`:

        virsh destroy <DOMAIN>

