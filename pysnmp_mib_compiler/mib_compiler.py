# -*- coding: utf-8 -*-
"""
    pysnmp_mib_compiler.mib_compiler
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    PySNMP MIB Compiler
    :copyright: (c) 2014-2015 Dmitry Korobitsin <https://github.com/korobitsin>
    :license: BSD, see LICENSE
"""
from __future__ import absolute_import
import logging
import argparse
import tempfile
import os
import shutil
import re
import subprocess
import jinja2
from pysnmp.smi import builder

log = logging.getLogger('mib_compiler')


class CompileError(Exception):
    pass


class MIBCompiler(object):
    def __init__(self, mibs_root):
        self.mibs_root = mibs_root
        self.mibs = {}
        self.tmp_dir = tempfile.mkdtemp()
        self.smi_conf = None

    def process(self, mib):
        self.generate_smi_conf()
        self.load_core_mibs()
        self.mibs[mib] = {'allow_overwrite': True}
        self.check_pysnmp()
        self.compile(mib)
        self.check_pysnmp()
        self.commit()

    def generate_smi_conf(self):
        self.smi_conf = tempfile.NamedTemporaryFile(suffix='.conf', delete=False)
        mib_paths = []
        for dirpaths, dirnames, filenames in os.walk(os.path.join(self.mibs_root, 'asn1')):
            if not dirnames:
                mib_paths.append(dirpaths)

        with open('{}/templates/smi.conf'.format(os.path.dirname(__file__))) as src:
            with self.smi_conf as dst:
                template = jinja2.Template(src.read())
                dst.write(template.render(mib_paths=mib_paths))
                log.info('smi.conf generated to {}'.format(self.smi_conf.name))

    def load_core_mibs(self):
        """To forbid compilation of core MIBs"""
        for mib_type in ('core', 'current'):
            for root, dirs, files in os.walk('{}/pysnmp/{}'.format(self.mibs_root, mib_type)):
                for filename in files:
                    if filename.endswith('.py') and filename != '__init__.py':
                        self.mibs[filename[:-3]] = {'allow_overwrite': False}

    def check_pysnmp(self):
        mibBuilder = builder.MibBuilder()
        mib_path = ['{}/pysnmp/{}'.format(self.mibs_root, mib_type) for mib_type in ('core', 'current', 'staging')]
        mibBuilder.setMibPath(*tuple(mib_path))
        try:
            mibBuilder.loadModules()
            mibBuilder.unloadModules()
        except Exception, e:
            log.exception('Failed to load PySNMP MIBs')
            raise CompileError('pysnmp inconsistency found, details=%s' % e)
        log.info("PySNMP consistency OK")

    def compile(self, mib):
        log.info("{mib}: starting compilation".format(mib=mib))
        self.mibs.setdefault(mib, {'allow_overwrite': False})

        self.check_info(mib)
        self.check_syntax(mib)
        if self.mibs[mib]['lang'] != 'SMIv2':
            self.convert_mib_to_smiv2(mib)
        self.convert_mib_to_python(mib)
        self.convert_mib_to_pysnmp(mib)
        modules = self.check_imports(mib)
        for module in modules:
            if module not in self.mibs:
                self.compile(module)

        log.info("{mib}: compiled successfully!".format(mib=mib))
        return False

    def check_info(self, mib):
        returncode, stdout, stderr = exec_cmd("smiquery -c {smi_conf} module {mib}".format(
            smi_conf=self.smi_conf.name, mib=mib))
        re_lang = re.compile('Language:\s*(.*?)\n')
        re_path = re.compile('Pathname:\s*(.*?)\n')
        re_lang_match = re_lang.search(stdout)
        re_path_match = re_path.search(stdout)
        if not re_lang_match or not re_path_match:
            raise CompileError('version info failed, mib={}'.format(mib))
        self.mibs[mib]['lang'] = re_lang_match.groups()[0]
        self.mibs[mib]['path'] = re_path_match.groups()[0]
        log.info('{mib}: info lang={lang}, path={path}'.format(
            mib=mib, lang=self.mibs[mib]['lang'], path=self.mibs[mib]['path']))

    def check_syntax(self, mib, severity=3):
        """ Levels 0-3 == Critical, 4-6 == Warnings
        smilint -c smi.conf -l 3 -s -r CISCO-RTTMON-MIB """
        log.info('{mib}: checking syntax, severity={severity}'.format(mib=mib, severity=severity))
        returncode, stdout, stderr = exec_cmd("smilint -c {smi_conf} -l {severity} -s -r {mib}".format(
            smi_conf=self.smi_conf.name, severity=severity, mib=self.mibs[mib]['path']))
        if returncode:
            raise CompileError('{mib}: mib syntax invalid'.format(mib=mib))
        for line in stderr.split('\n'):
            re_dep_match = re.match("^.*? failed to locate MIB module `(.*?)'", line)
            if re_dep_match:
                raise CompileError('{mib}: failed to locate MIB {missing_mib}'.format(
                    mib=mib, missing_mib=re_dep_match.group(1)))

    def convert_mib_to_smiv2(self, mib):
        log.info('{mib}: converting to SMIv2 format'.format(mib=mib))
        filename = os.path.join(self.tmp_dir, '{}.smiv2'.format(mib))
        returncode, stdout, stderr = exec_cmd(
            "smidump -c {smi_conf} -l 3 -k -s -f smiv2 -o {filename} {mib}".format(
                smi_conf=self.smi_conf.name, filename=filename, mib=self.mibs[mib]['path']))
        if returncode:
            raise CompileError('{mib}: convert to SMIv2 failed'.format(mib=mib))
        self.mibs[mib]['path'] = filename

    def convert_mib_to_python(self, mib):
        log.info('{mib}: converting to python format'.format(mib=mib))
        filename = os.path.join(self.tmp_dir, '{}.python'.format(mib))
        returncode, stdout, stderr = exec_cmd(
            "smidump -c {smi_conf} -l 3 -k -s -f python -o {filename} {mib}".format(
                smi_conf=self.smi_conf.name, filename=filename, mib=self.mibs[mib]['path']))
        if returncode:
            raise CompileError('{mib}: convert to python failed'.format(mib=mib))

    def convert_mib_to_pysnmp(self, mib):
        staging_dir = os.path.join(self.mibs_root, 'pysnmp', 'staging')
        os.path.isdir(staging_dir) or os.makedirs(staging_dir)
        log.info('{mib}: converting to PySNMP format'.format(mib=mib))
        fn_in = os.path.join(self.tmp_dir, '{}.python'.format(mib))
        fn_out = os.path.join(self.mibs_root, 'pysnmp', 'staging', '{}.py'.format(mib))
        returncode, stdout, stderr = exec_cmd("cat {} | libsmi2pysnmp > {}".format(
            fn_in, fn_out))
        if returncode:
            raise CompileError('{mib}: convert to pysnmp failed'.format(mib=mib))

    def check_imports(self, mib):
        """smiquery -c /opt/xee/etc/smi.conf imports CISCO-RTTMON-MIB
        Imports: SNMPv2-SMI::MODULE-IDENTITY
                 SNMPv2-SMI::OBJECT-TYPE
        """
        modules = {}
        returncode, stdout, stderr = exec_cmd("smiquery -c {smi_conf} imports {mib}".format(
            smi_conf=self.smi_conf.name, mib=mib))
        if returncode:
            raise CompileError('dependencies check failed mib={}'.format(mib))
        re_mod = re.compile("^.*?\s*([a-zA-Z\-0-9]*?)::(.*)$")
        for line in stdout.split('\n'):
            re_mod_match = re_mod.match(line)
            if re_mod_match:
                modules[re_mod_match.group(1)] = 1
        log.info("{mib}: imports = {imports}".format(mib=mib, imports=modules.keys()))
        return modules.keys()

    def commit(self):
        for root, dirs, files in os.walk(os.path.join(self.mibs_root, 'pysnmp', 'staging')):
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                mib = filename[:-3]
                fn_new = os.path.join(root, filename)
                size_new = os.path.getsize(fn_new)
                fn_old = '{}/pysnmp/current/{}'.format(self.mibs_root, filename)
                if os.path.isfile(fn_old):
                    size_old = os.path.getsize(fn_old)
                    log.warn('MIB file exists in current folder name={name} size={size_old} new size={size_new}, allow_overwrite={allow_overwrite}'.format(
                        name=filename, size_old=size_old, size_new=size_new, allow_overwrite=self.mibs[mib]['allow_overwrite']))
                    if self.mibs[mib]['allow_overwrite']:
                        os.unlink(fn_old)
                    else:
                        continue
                log.info('Exporting MIB file={}, size={}'.format(filename, size_new))
                shutil.move(fn_new, fn_old)
        self.smi_conf and os.unlink(self.smi_conf.name)


def exec_cmd(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode:
        log.exception('Command failed with exit code {code}, cmd={cmd}, stdout=\n{stdout}, std_err=\n{stderr}'.format(
            code=p.returncode, cmd=cmd, stdout=stdout, stderr=stderr))
    return p.returncode, stdout, stderr


def main():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(process)5d %(name)s %(levelname)-5s %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("mib", help="MIB file to compile")
    parser.add_argument("--revalidate", help="validate and commit changes", action="store_true")
    parser.add_argument("--mibs_root", help="MIBs location")
    args = parser.parse_args()

    mib_compiler = MIBCompiler(args.mibs_root)
    if args.revalidate:
        mib_compiler.check_pysnmp()
        mib_compiler.commit()
    else:
        mib_compiler.process(args.mib)


if __name__ == "__main__":
    main()
