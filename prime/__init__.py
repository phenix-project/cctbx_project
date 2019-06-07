from __future__ import division
import boost.python
ext = boost.python.import_ext("prime_ext")
from prime_ext import *

prime_description = ''' The Post-RefInement and MErging (PRIME) program for
the scaling, merging and post-refinement of integrated diffraction images.

Reference: Uervirojnangkoorn, et al., eLife, 2015'''

prime_license = ''' PRIME is distributed under open source license'''
