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

import sys

import zipfile
import subprocess
import copy
import random

from PyPDF2 import PdfFileReader, PdfFileWriter
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

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

def convertOdtToPdf(input_path):
    subprocess.check_call(['libreoffice', '--headless', '--convert-to', 'pdf', input_path])

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
    challenge_variants = makeChallengeVariants(loadChallenges('challenges.txt'), 10, 10)

    generateOdt('challenges.odt', challenge_variants)
    convertOdtToPdf('challenges.odt')
    mergePDFs('agenda_a4.pdf', 'challenges.pdf', 'output.pdf')
