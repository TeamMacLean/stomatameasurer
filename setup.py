from setuptools import setup


def readme():
    with open('README') as readme:
        return readme.read()

setup(name='stomatadetector',
      version='0.0.6dev',
      description='Stomata detection from FLEX/TIFF fluorescent images',
      long_description=readme(),
      url='https://github.com/TeamMacLean/stomatameasurer',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Topic :: Scientific/Engineering :: Image Recognition'
      ],
      author='Dan MacLean',
      author_email='dan.maclean@tsl.ac.uk',
      license='MIT',
      packages=['stomatadetector'],
      install_requires=[
          'numpy',
          'scipy',
          'scikit-image',
          'matplotlib',
          'ipywidgets',
          'xmltodict',
          'tifffile',
      ],
      zip_safe=False)
