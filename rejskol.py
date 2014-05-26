#!/usr/bin/python3
# -*- coding: utf-8 -*-

# rejskol - Data extractor for http://rejskol.msmt.cz
# Copyright © 2014 Jan Stanek - <khardix@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import argparse
from csv import DictWriter
import rsscrapper

arguments = argparse.ArgumentParser(
    description="Get data from http://rejskol.msmt.cz/ and drop them into CSV file."
    )
subcommands = arguments.add_subparsers(help='Informational commands', dest='command')

# Display functions
subcommands.add_parser('areas', description="Prints available areas")
subcommands.add_parser('categories', description="Prints available school categories")

# Flags
arguments.add_argument('-a','--area', default='all', dest='area',
    help="Area code, default to all.")
arguments.add_argument('-c','--category', default='A', dest='category',
    help="Catgory letter(s), default to A (kindergardens).")
arguments.add_argument('-o', '--output', help="Output file", default='rejskol.csv')

opts = arguments.parse_args()

# create form object - get entry information
entryForm = rsscrapper.entryForm()

if opts.command == 'areas':
  print("Code:\tArea:")
  for code, area in sorted(entryForm.areas('all').items()):
    print("{}\t{}".format(code, area))

elif opts.command == 'categories':
  print("Code:\tCategory:")
  for code, cat in sorted(entryForm.categories.items()):
    print("{}".format(cat))

else: # main function - generate CSV
  target_areas = entryForm.areas(opts.area)
  if target_areas == None:
    print('Invalid area', file=sys.stderr)
    sys.exit(1)

  if opts.category not in entryForm.categories.keys():
    print('Invalid category', file=sys.stderr)
    sys.exit(1)

  with open(opts.output, 'w') as csvfile:
    output = DictWriter(csvfile, rsscrapper.dataBuilder.importantData.keys(), dialect='unix')
    # write first line of column headings
    output.writerow({key:key for key in rsscrapper.dataBuilder.importantData.keys()})
    for area, name in sorted(target_areas.items()):
      data = rsscrapper.dataBuilder(entryForm.target_url, entryForm.submit(area, opts.category))
      print("Area {}: {} schools".format(name, len(data.schoolLinks)))
      schoolIndex = 0
      for school in data:
        schoolIndex += 1
        print("Writing school {}/{}".format(schoolIndex, len(data.schoolLinks)), end='\r', flush=True)
        output.writerow(school)
