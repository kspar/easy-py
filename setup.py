import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="easy-py",
    version="0.8.0",
    author="Kaspar Papli",
    author_email="kaspar.papli@gmail.com",
    license="MIT",
    description="Python SDK for Easy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kspar/easy-py",
    packages=setuptools.find_packages(),
    package_data={
        'easy': ['auth-templates/*']
    },
    install_requires=[
        # The auth server no longer uses the werkzeug.server.shutdown environ hook (removed in
        # Werkzeug 2.1), so the old ~=2.0.0 pin is gone. The floor is 3.0 rather than 2.0 because
        # Werkzeug 2.0 cannot run on Python 3.12+ at all (it calls the removed ast.Str while
        # compiling URL rules), and a lower floor would count the broken 2.0.3 as satisfying the
        # requirement and leave it installed. The code itself works with 2.0 as well.
        'flask>=3.0',
        'requests>=2.28.2,<2.32.4',
        'werkzeug>=3.0'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
)
