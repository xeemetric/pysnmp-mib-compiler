# pysnmp-mib-compiler

An alternative MIB Compiler for PySNMP.


## Why yet another one?

In most cases it is recommended to use a pure Python and feature rich [PySMI mibdump](http://pysmi.sourceforge.net/user-perspective.html)
utility written by Ilya Etingof.

However in some cases given the complexity of the MIB files PySMI might fail
while the MIB can still be parsed by the standard [libsmi](https://www.ibr.cs.tu-bs.de/projects/libsmi/) utility.
This is why pysnmp-mib-compiler relying on libsmi for parsing of MIB modules can be more useful.


## What it does?

    1. Checks MIB info: path, language
    2. Checks MIB syntax
    3. If MIB is not SMIv2 converts to it
    4. Exports to python format
    5. Converts to PySNMP format and places it to staging folder
    6. Compiles prerequisites if not yet compiled
    7. Checks PySNMP consistency state after compilation
    8. Moves all staging mibs to destination directory


## Installation

    $ git clone https://github.com/xeemetric/pysnmp-mib-compiler.git
    $ sudo apt-get update && apt-get install smitools
    $ sudo pip install -r pysnmp-mib-compiler/requirements.txt && pip install pysnmp-mib-compiler


## How to use?


    $ mib_compiler --mib-source <path to asn1 mibs> <MIB module name>


## Troubleshooting

    - MIB compilation failing
        If the dependency MIB is missing, download it and place into mibs/asn1 directory
    - PySNMP MIB is created in mibs/pysnmp/staging, but validation fails, e.g. (too long import list >255)
        Fix it manually in staging directory and re-run mib_compiler with --revalidate argument


## Author

Developed and maintained by [Dmitry Korobitsin](https://github.com/korobitsin).
