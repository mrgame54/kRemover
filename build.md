### Building from Source
---
If you want to compile the `.rpm` package yourself from scratch, follow these steps:

**1. Install Build Tools**

```bash
sudo dnf install rpm-build rpmdevtools
rpmdev-setuptree
```
**2. Prepare the Source Tarball**

Clone this repository, organize the files into a versioned folder, and compress them into the RPM `SOURCES` directory.

```bash
git clone [https://github.com/mrgame54/kRemover.git](https://github.com/mrgame54/kRemover.git)
cd kRemover

# Create the strictly named release folder
mkdir kremover-0.9.0

# Copy the necessary files
cp -r src ui assets main.py kremover-0.9.0/

# Compress it into the RPM build tree
tar -czvf ~/rpmbuild/SOURCES/kremover-0.9.0.tar.gz kremover-0.9.0/

# Clean up the temporary folder
rm -rf kremover-0.9.0/

```

**3. Build the Package**

Create a fitting `.spec` file to the `SPECS` folder and compile:

```bash
cp kremover.spec ~/rpmbuild/SPECS/
rpmbuild -ba ~/rpmbuild/SPECS/kremover.spec

```

The ready-to-install `.rpm` file will be in `~/rpmbuild/RPMS/noarch/`.
