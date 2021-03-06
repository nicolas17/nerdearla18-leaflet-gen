#!/usr/bin/env python3

# Copyright (c) 2018 Nicolás Alvarez <nicolas.alvarez@gmail.com>
# Licensed under the MIT license; see LICENSE.txt for details.

"""

Steps:
- read list of challenges
- get random subsets
- generate content.xml with the text lines
- zip it up into challenges.odt
- convert to challenges.pdf
- overlay challenges.pdf onto base PDF

"""

import os

import zipfile
import subprocess
import copy
import random
import collections

import yaml
from PyPDF2 import PdfFileReader, PdfFileWriter
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

class Challenges:
    def __init__(self, path):
        with open(path, 'r') as f:
            self.data = yaml.load(f)

        self.categories = {category['name']: category for category in self.data}

        self.lines = []
        for category in self.data:
            for line in category['lines']:
                self.lines.append({'text': line, 'category': category['name'], 'style': 'strike' if category.get('strikeout', False) else None})

    def makePage(self, count):
        result = []

        # how many items of each category we already added into 'results'
        category_count = collections.defaultdict(lambda: 0)

        # this should be done with a more generic "min_per_page=1", but for now this HACK will do
        strike_item = random.choice([line for line in self.lines if line['category'] == 'tachadas'])
        result.append(strike_item)
        category_count['tachadas'] += 1

        while len(result) < count:
            item = random.choice(self.lines)
            if item in result:
                continue
            if category_count[item['category']] >= self.categories[item['category']].get('max_per_page',999):
                print("too many from %s in this page already" % item['category'])
                continue
            category_count[item['category']] += 1
            result.append(item)

        # shuffle again since the order may be skewed
        random.shuffle(result)
        return result

def loadChallenges(filename):
    with open(filename, 'r') as f:
        return [line.rstrip() for line in f.readlines()]

def makeChallengeVariants(input_challenges, page_count, challenges_per_page):
    for n in range(page_count):
        yield random.sample(input_challenges, challenges_per_page)

def generateOdtContent(out_file, text_lines):
    '''
    text_lines should be a list of lists of text lines;
    each sublist will be used on a separate page.
    '''

    from jinja2 import Environment, FileSystemLoader
    env = Environment(
        loader=FileSystemLoader('.')
    )

    template = env.get_template('content.xml.j2')

    template.stream(pages=text_lines).dump(out_file, encoding='UTF-8')

def generateOdt(filename, text_lines):
    with zipfile.ZipFile(filename, 'w') as zipout:
        # the mimetype file *must* be uncompressed
        zipout.compression = zipfile.ZIP_STORED
        zipout.write('odt/mimetype', 'mimetype')

        zipout.compression = zipfile.ZIP_DEFLATED
        zipout.write('odt/META-INF/manifest.xml', 'META-INF/manifest.xml')
        zipout.write('odt/styles.xml', 'styles.xml')

        # FIXME write correct timestamp for this file; currently it's set to 1980
        with zipout.open('content.xml', 'w') as content_f:
            generateOdtContent(content_f, text_lines)

def convertOdtToPdf(tempdir, input_file):
    subprocess.check_call(['libreoffice', '-env:UserInstallation=file://%s' % os.path.join(os.path.abspath(tempdir), 'loenv'), '--headless', '--convert-to', 'pdf', input_file], cwd=tempdir)

def mergePDFs(base_file, overlay_file, output_file):
    output = PdfFileWriter()

    orig = PdfFileReader(open(base_file,'rb'))
    challenges = PdfFileReader(open(overlay_file,'rb'))

    for page_num in tqdm(range(challenges.getNumPages()), unit='page'):
        page = copy.copy(orig.getPage(0))
        page.mergePage(challenges.getPage(page_num))
        output.addPage(page)

    with open(output_file, 'wb') as out_f:
        output.write(out_f)

if __name__ == '__main__':
    tempdir='tmp'

    inputs = Challenges('challenges.yaml')
    challenge_variants = []
    for pagenum in range(10):
        print("Generating data for page %d" % (pagenum+1))
        challenge_variants.append(inputs.makePage(count=10))

    #challenge_variants = makeChallengeVariants(loadChallenges('challenges.txt'), 10, 10)

    try:
        os.mkdir(tempdir)
    except FileExistsError:
        pass

    generateOdt(os.path.join(tempdir, 'challenges.odt'), challenge_variants)
    convertOdtToPdf(tempdir, 'challenges.odt')

    mergePDFs('agenda_a4.pdf', os.path.join(tempdir, 'challenges.pdf'), 'output.pdf')
