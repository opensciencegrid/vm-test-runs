#!/usr/bin/python

import guestfs
import os
import sys

blacklist = set(['/lost+found'])

def print_now(message):
    print message,
    sys.stdout.flush()

g = guestfs.GuestFS()

# add careful checking of argv
image_filename = sys.argv[1]
output_dir = sys.argv[2]

if os.path.exists(output_dir):
    print "Output directory '%s' already exists, will not overwrite, try again" % (output_dir)
    sys.exit(1)
os.makedirs(output_dir)

g.add_drive_opts(image_filename, readonly=1, format="raw")

print_now("Extracting files from '%s'..." % (image_filename))
g.launch()

g.mount('/dev/vda', '/')
paths = g.find('/')
for image_path in paths:
    full_image_path = os.path.join('/', image_path)
    # if full_image_path in blacklist:
        # print "Skipping '%s'" % (full_image_path)

    if not g.is_dir(full_image_path):
        image_dir = os.path.dirname(image_path)
        local_dir = os.path.join(output_dir, image_dir)
        if not os.path.exists(local_dir):
            # print "Creating directory '%s'" % (local_dir)
            os.mkdir(local_dir)
            # print "Extracting '%s'" % (full_image_path)
        g.download(full_image_path, os.path.join(output_dir, image_path))

print "ok"
