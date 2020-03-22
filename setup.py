import setuptools

setuptools.setup(
    name='gdb-pounce',
    version='0.0.1',
    author='mephi42',
    author_email='mephi42@gmail.com',
    description='attach to a process precisely after a successful '
                'execve() / execveat()',
    url='https://github.com/mephi42/gdb-pounce',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    scripts=['gdb-pounce'],
)
