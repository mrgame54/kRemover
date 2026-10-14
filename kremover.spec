Name:           kremover
Version:        0.9.1
Release:        1%{?dist}
Summary:        Fedora KDE RPM Uninstaller and Data Cleaner
License:        MIT
BuildArch:      noarch
Source0:        %{name}-%{version}.tar.gz

# requirements
Requires:       python3
Requires:       python3-pyside6
Requires:       python3-send2trash
Requires:       polkit

%description
kRemover safely locates and trashes leftover user configuration data in XDG directories after an RPM package is removed via DNF.

%prep
%setup -q

%install
rm -rf $RPM_BUILD_ROOT

# Create the standard Linux system directories
mkdir -p $RPM_BUILD_ROOT/usr/share/%{name}
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/usr/share/applications
mkdir -p $RPM_BUILD_ROOT/usr/share/pixmaps

# Copy your Python files and UI assets into the system share directory
cp -r src ui assets main.py $RPM_BUILD_ROOT/usr/share/%{name}/

# Copy your dark logo to the system icons directory so the app menu can use it
cp assets/dark.png $RPM_BUILD_ROOT/usr/share/pixmaps/%{name}.png

# Create the global terminal launcher command
cat << 'EOF' > $RPM_BUILD_ROOT/usr/bin/%{name}
#!/bin/bash
python3 /usr/share/kremover/main.py "$@"
EOF
chmod 755 $RPM_BUILD_ROOT/usr/bin/%{name}

# Create the App Menu Shortcut using your custom icon
cat << 'EOF' > $RPM_BUILD_ROOT/usr/share/applications/%{name}.desktop
[Desktop Entry]
Name=kRemover
Comment=Fedora KDE Uninstaller
Exec=kremover
Icon=kremover
Terminal=false
Type=Application
Categories=System;Utility;
EOF

%files
/usr/share/%{name}/
/usr/bin/%{name}
/usr/share/applications/%{name}.desktop
/usr/share/pixmaps/%{name}.png
