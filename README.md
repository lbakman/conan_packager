# conan_packager

This is an attempt to integrate conan into my TeamCity build system. This was created when conan was still version 0.6 something and since conan has evolved a lot since I am not sure that it is really required any more. That is something I intend to find out.

I use it in five steps:

## Step 1: Clean

Perform a cleanup of the local package that we are going to build. The varaibles channel_name and profile_name are set from TeamCity.

```python
from packager import ConanPackager


packager = ConanPackager(channel="%channel_name%", profile="%profile_name%")
packager.remove()
```

## Step 2: Determine pacakges to upload

Obtain a list of packages that will be built. This will be used later when uploading packages.

```python
from cmake import ConanPackager
import os
import json


packages_file = "%package_list%"
packager = ConanPackager(channel="%channel_name%", profile="%profile_name%")

if os.path.isfile(packages_file):
    os.remove(packages_file)

to_upload = packager.determine_packages_to_upload()
with open(packages_file, 'w') as outfile:
    json.dump(to_upload, outfile)
```

## Step 3: Build

Perform a build of the package, including dependencies if necesarry.

```python
from packager import ConanPackager


packager = ConanPackager(channel="%channel_name%", profile="%profile_name%")
packager.create()
```

## Step 4: Upload packages

Upload package and all built dependencies.

```python
from cmake import ConanPackager
import os
import json


packages_file = "%package_list%"
packager = ConanPackager(profile="%profile_name%")

to_upload = None
with open(packages_file, 'r') as infile:
    to_upload = json.load(infile)

packager.upload_packages(to_upload)
```

## Step 5: Deploy

As the packages are built in the conan data directory, deploy the packages to the build directory for TeamCity to pick up.

```python
from cmake import ConanPackager
import os
import json


metadata_file = "%metadata_file%"
packager = ConanPackager(channel="%channel_name%", profile="%profile_name%")
if os.path.isfile(metadata_file):
    os.remove(metadata_file)

with open(metadata_file, 'w') as outfile:
    json.dump(packager.metadata, outfile)

packager.deploy()
```
