#!/usr/bin/python

import os
import shutil

root = os.getcwd()
files = os.listdir(root)
files = filter(lambda f:f.endswith(".svg"), files)

for size in ["16", "24", "32", "48"]:
    parent = os.path.dirname(root)
    if not os.path.isdir(os.path.join(parent, size)):
        os.mkdir(os.path.join(parent, size))
    else:
        shutil.rmtree(os.path.join(parent, size))
        os.mkdir(os.path.join(parent, size))


    for file_ in files:
        print("convert -resize {}x{} {} {}/{}/{}".format(size, size, file_, parent, size, file_.replace(".svg", ".png")))
        os.system("convert -resize {}x{} {} {}/{}/{}".format(size, size, file_, parent, size, file_.replace(".svg", ".png")))