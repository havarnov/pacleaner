#!/usr/bin/env python3

import os
import errno
import argparse
from operator import attrgetter

PACKAGES = "/var/cache/pacman/pkg/"
INSTALLED = "/var/lib/pacman/local"
EXTENSIONS = ["pkg.tar.xz", "pkg.tar.gzip"]
ARCHES = ["any", "x86_64", "i686"]
NR_OF_PKG = 2


class Package(object):
    '''base class for all kinds of packages, installed or package files'''

    def __str__(self):
        return self.name + "-" + self.version + "-" + self.pkg_version
    
    def __repr__(self):
        return repr((self.name, self.version, self.pkg_version, self.arch))

    def __eq__(self, other):
        assert isinstance(other, Package)
        return self.name == other.name and self.version == other.version and self.pkg_version == other.pkg_version and self.arch == other.arch

    def __ne__(self, other):
       return not self.__eq__(other)

    def __lt__(self, other):
        if self.__eq__(other):
            return false
        elif self.name == other.name:
            if self.version == other.version:
                return self.pkg_version < other.pkg_version
            else:
                return self.version < other.version
        else:
            return self.name < other.name
                    
    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

class PkgFile(Package):
    '''Class for holding info about on specific package'''

    def __init__(self, filename, path):
        self.filename = filename
        self.fullpath = os.path.join(path, filename)
        self.name, self.version, self.pkg_version, rest = filename.rsplit('-', 3)
        self.arch, self.file_ext = rest.split('.',1)

class InstalledPkg(Package):
    '''class for installed packages on the system'''

    def __init__(self, name, version, arch):
        self.name = name
        self.version, self.pkg_version = version.split('-')
        self.arch = arch

class PkgList(object):
    '''Class for holding a complete list over package files on the system'''


    def __str__(self):
        res = ""
        for pkg in self.pkg_list:
            if pkg != self.pkg_list[0]:
                res += "\n"
            res += pkg.__str__()
        return res

    def sort(self):
        self.pkg_list = sorted(self.pkg_list, key = attrgetter("name", "version", "pkg_version"))

    def names(self):
        return [i.name for i in self.pkg_list ]

    def get_by_name(self, name):
        result = []
        for pkg in self.pkg_list:
            if pkg.name == name:
                result.append(pkg)
        return result

    def unique(self):
        result = []
        for pkg in self.pkg_list:
            if pkg.name not in result:
                result.append(pkg.name)
        return result

class PkgFileList(PkgList):
     
    def __init__(self, path):
        self.path = path
        self.pkg_list = []
        filelist = [ f for f in os.listdir(path) if f.endswith(tuple(EXTENSIONS)) ]
        for f in filelist:
            self.pkg_list.append(PkgFile(f, path))

class InstalledPkgList(PkgList):

    def __init__(self, path):
        self.path = path
        self.pkg_list = []
        pkgs = [ p for p in os.listdir(path) if os.path.isdir(os.path.join(path, p)) ]
        for p in pkgs:
            filepath = os.path.join(path, p, "desc")
            with open(filepath) as f:
                lines  = [ i.strip('\n') for i in f.readlines() ]
                name = lines[lines.index("%NAME%") + 1]
                version = lines[lines.index("%VERSION%") + 1]
                arch = lines[lines.index("%ARCH%") + 1]
                self.pkg_list.append(InstalledPkg(name, version, arch))

def uninstalled_packages(pkgfiles, installed):
    result = []
    for pkgfile in pkgfiles.pkg_list:
        if pkgfile.name not in installed.names():
            result.append(pkgfile)
    return result

def older_than(pkgfiles, installed, number):
    result = []
    for pkg in installed.unique():
        full_list = pkgfiles.get_by_name(pkg)
        if(len(full_list) > number):
            full_list = sorted(full_list, key = attrgetter("name", "version",
"pkg_version"))
            #print(full_list)
            if len(full_list[0:-number]) > 0:
                #result.append(full_list[0:-number])
                for pkg in full_list[0:-number]:
                    result.append(pkg)
    return result

def find_files(packages, pkgfiles):
    res = []
    for package in packages:
        for pkgfile in pkgfiles.pkg_list:
            if pkgfile == package:
                res.append(pkgfile)
    return res

def print_packages(packages):
    for pkg in packages:
        print(pkg)

def print_installed(packages):
    for pkglist in packages:
        for pkg in pkglist:
            print(pkg)

def remove_packages(packages):
    for pkg in packages:
        assert isinstance(pkg, PkgFile)
        print("deleting... " + pkg.__str__())
        try:
            os.remove(pkg.fullpath)
        except OSError as e:
            if e.errno == errno.EACCES:
                print("You don't have premissions to delete this file. Run as Root?")
                exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Clean up pacman\'s cache. More flexible than "pacman -Sc[c]"')

    # REQUIRED ARGUMENTS
    parser.add_argument('--uninstalled', '-u', action = 'store_true', help='list packages that is not installed on the system')
    parser.add_argument('--morethan', '-m', action = 'store_true', help='list packages that has more than the specified number of files in the cache')

    # OPTIONAL ARGUMENTS
    parser.add_argument('--delete', action = 'store_true', help='if this option is set, the packages listed by "uninstalled" or "morethan" is deleted.')
    parser.add_argument('--number', '-n', metavar='n', type=int, default=NR_OF_PKG, help='number of packages that you want to keep as a backup. Defaults to 2.')
    parser.add_argument('--cache_path', '-c', metavar='PATH', type=str, default=PACKAGES, help='optional path to pacman\'s cache')
    parser.add_argument('--installed_path', '-i', metavar='PATH', type=str, default=INSTALLED, help='optional path to pacman\'s installed package db')

    args = parser.parse_args()

    if not (args.uninstalled or args.morethan):
        parser.error("Need to specify -u, -t or both")
    
    installed = InstalledPkgList(args.installed_path)
    pkgfiles = PkgFileList(args.cache_path)
    old = older_than(pkgfiles, installed, args.number)
    uninstalled = uninstalled_packages(pkgfiles, installed)

    if not args.delete:
        if args.uninstalled:
            print_packages(uninstalled)
        if args.morethan:
            print_packages(old)

    else:
        if args.uninstalled:
            remove_packages(uninstalled)
        if args.morethan:
            old_files = find_files(old, pkgfiles)
            remove_packages(old_files)
