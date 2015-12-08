from setuptools import setup

setup(
    name='pysnmp-mib-compiler',
    description='An alternative MIB Compiler for PySNMP',
    version='0.1.0',
    author='Dmitry Korobitsin',
    author_email='korobicin@gmail.com',
    url='https://github.com/korobitsin/pysnmp-mib-compiler',
    packages=[
        'pysnmp_mib_compiler'
    ],
    install_requires=[
        'pysnmp',
        'jinja2'
    ],
    entry_points={
        'console_scripts': [
            'mib_compiler = pysnmp_mib_compiler.mib_compiler:main',
        ],
    },
    include_package_data=True,
    platforms=['Any'],
    license='BSD',
    zip_safe=False,
)
