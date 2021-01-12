import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="easy-py",
    version="0.3.5",
    author="Kaspar Papli",
    author_email="kaspar.papli@gmail.com",
    description="Python SDK for Easy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kspar/easy-py",
    packages=setuptools.find_packages(),
    package_data={
        'easy': ['auth-templates/*']
    },
    install_requires=[
        'flask~=1.1.2',
        'requests~=2.24.0',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
