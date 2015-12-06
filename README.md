# pysnmp-mib-compiler

MIB Compiler for PySNMP.


## What it does?

    1. Checks MIB info: path, language
    2. Checks MIB syntax
    3. If MIB is not SMIv2 converts to it
    4. Exports to python format
    5. Converts to PySNMP format and places it to staging folder
    6. Compiles prerequisites if not yet compiled
    7. Checks PySNMP consistency state after compilation
    8. Moves all staging mibs to mibs/pysnmp/current


## with Docker

    $ git clone https://github.com/xeemetric/mibs.git
    $ docker run -v mibs:/mibs xeemetric/pysnmp-mib-compiler CISCO-SMI


## Known issues and workarounds:

    1. Too long import list (>255) --> can be fixed in compiled code manually


## Author

Developed and maintained by [Dmitry Korobitsin](https://github.com/korobitsin).
