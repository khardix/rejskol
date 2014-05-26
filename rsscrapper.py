#!/usr/bin/python3
# -*- coding: utf-8 -*-

# rsscrapper - Python module for extracting data from http://rejskol.msmt.cz
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

import re
from collections import OrderedDict

try:
  import urllib.request as urlrequest
  import urllib.parse as urlparse
  import http.cookiejar as ckjar
except ImportError:
  print("Chybí urllib!", file=sys.stderr)
  raise ImportError

try:
  import bs4
except ImportError:
  print("Chybí BeautifulSoup4!", file=sys.stderr)
  raise ImportError

# Build URL opener that store cookies
cookiejar = ckjar.CookieJar()
urlopener = urlrequest.build_opener(urlrequest.HTTPCookieProcessor(cookiejar))

class entryForm:
  "Data from registry entry form"

  def __init__(self, frameurl="LoginPage.aspx", baseurl="http://rejskol.msmt.cz/"):
    """ Loads important data from entry form
    """
    self.initUrl = urlparse.urljoin(baseurl, frameurl)
    response = urlopener.open(self.initUrl)
    htmltree = bs4.BeautifulSoup(response.read())
    entryform = htmltree.find(id="form1")
    
    self.target_url = urlparse.urljoin(
        response.geturl(), # Frame URL
        entryform['action'], # Target of the form
    )

    self.hidden_items = {
        item['name']:item['value'] for item in entryform("input", type="hidden")
    }

    areaTag = entryform.find(id="lblKraj").find_next("select")
    self.areaTagName = areaTag['name']
    self.rawAreas = {
        opt.string.split(', ')[0]:(opt.string.split(', ')[1], opt['value'])
        for opt in areaTag('option') if opt.string != None
    }

    categoryTag = entryform.find(id="lblDruh").find_next("select")
    self.categoryTagName = categoryTag['name']
    self.categories = {
        opt['value']:opt.string
        for opt in categoryTag('option') if opt.string != None
    }

  def areas(self, filter='all'):
    """Returns list of valid areas"""
    if filter == 'all':
      return {code: name[0] for code, name in self.rawAreas.items()
          if not re.match('^CZ[0-9]{3}$', code)} # nevracet kraje, moc skol
    elif filter in self.rawAreas.keys():
      return {filter: self.rawAreas[filter][0]}
    else:
      return None

  def categories(self):
    "Return list of valid categories"
    return self.categories

  def submit(self, area, category='A'):
    "Submits the form and returns resulting page"

    formData = list(self.hidden_items.items()) # Hidden items
    formData += [(self.categoryTagName, category)] # category specification
    formData += [(self.areaTagName, self.rawAreas[area][1])] # area specification
    # arbitrary settings - name of the submit button and maximum items per page
    formData += [('btnVybrat', 'Vybrat'), ('txtPocetZaznamu', 400)]

    results = urlopener.open(self.target_url, data=urlparse.urlencode(formData).encode('utf-8'))
    
    return results.read()

class dataBuilder:
  "Retrieve the data from html list of schools"

  # list of interesting informations
  # format: Name => (htmlID, textREEdit)
  importantData = OrderedDict({
      'Druh školy':     ['lblNazevNoveSkoly'],
      'IZO':            ['lblIZONoveSkoly'],
      'Kapacita':       ['lblCilovaKapacita', re.compile('[0-9]+$')],
      'Místa':          ['lblMistaNoveSkoly_Nazvy'],
      'Právnická osoba':['lblVykonavaReditelstvi'],
      'IČO':            ['lblICPO'],
      'Identifikátor P. O.':['lblIdentifikatorPO'],
      'Adresa':         ['lblVykonavaRedAdresa'],
      'Zřizovatel':     [re.compile('lblZrizovatel$')],
      'Adresa zřizovatele - ulice':[re.compile('lblZrizUlice$')],
      'Adresa zřizovatele - obec':[re.compile('lblZrizPSCObec$')],
      'Ředitel/ka':     [re.compile('lblReditelZapis$')],
      'Adresa ředitele/ky - ulice':[re.compile('lblReditelUliceZapis$')],
      'Adresa ředitele/ky - obec':[re.compile('lblReditelPSCObecZapis$')]
      })

  def __init__(self, source_url, html_data):
    self._RE = { # Regular expressions for later use
        'school': re.compile('SkolaAZarizeni\.aspx'),
        'owner' : re.compile('PravOsoba\.aspx')
        }

    self.url = source_url # source url for full link construction
    self.reportUrl = urlparse.urljoin(source_url, '../VREJSablony/VypisSkolyAZarizeni.aspx')
    self.reportIdName = 'idKTisku'

    self._htree = bs4.BeautifulSoup(html_data)
    self.schoolLinks = [ link['href'] for link in self._htree('a', href=self._RE['school']) ]

    # storage for iteration
    self._data = []

  def getSchoolData(self, schoolLink):
    # get school id
    url = urlparse.urlparse(schoolLink)
    schoolId = urlparse.parse_qs(url.query)['pub_uid'][0]

    query = {self.reportIdName: schoolId}

    # open the page and get the code
    html_str = urlopener.open("{}?{}".format(self.reportUrl, urlparse.urlencode(query))).read().decode('utf-8')
    htree = bs4.BeautifulSoup(html_str)
    
    data = {}
    for label, instr in __class__.importantData.items():
      tag = htree.find(id=instr[0])
      if tag == None:
        continue
      else:
        text = ''
        text_part = 0
        for string in tag.strings:
          if text_part == 2: # place for separator
            text_part = 0
            text += ';'
          text += string
          text_part += 1

      if len(instr) > 1:
        text = instr[1].search(text).group() # only the matched portion of text
      data[label] = text

    return data

  def __iter__(self):
    self._index = 0
    return self

  def __next__(self):
    self._index += 1
    if self._index > len(self.schoolLinks):
      raise StopIteration
    if self._index > len(self._data):
      self._data.append(self.getSchoolData(self.schoolLinks[self._index - 1]))
    return self._data[self._index - 1]
