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
from lxml import etree
from PyPDF2 import PdfFileReader, PdfFileWriter

def generateOdtContent(out_file, text_lines):
    '''
    text_lines should be a list of lists of text lines;
    each sublist will be used on a separate page.
    '''
    OFFICE_NAMESPACE = 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
    TEXT_NAMESPACE   = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
    OFFICE = '{%s}' % OFFICE_NAMESPACE
    TEXT   = '{%s}' % TEXT_NAMESPACE

    NSMAP = {'office': OFFICE_NAMESPACE, 'text': TEXT_NAMESPACE}

    root = etree.Element(OFFICE+"document-content", nsmap=NSMAP)
    root.set(OFFICE+'version', '1.2')

    body_elem = etree.SubElement(root, OFFICE+'body')
    text_elem = etree.SubElement(body_elem, OFFICE+'text')

    for page in text_lines:
        first = True
        for line in page:
            para_elem = etree.SubElement(text_elem, TEXT+'p')
            para_elem.set(TEXT+'style-name', 'Body_first' if first else 'Body')
            para_elem.text = line
            first = False

    etree.ElementTree(root).write(out_file, encoding='UTF-8')

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

    for page_num in range(challenges.getNumPages()):
        page = copy.copy(orig.getPage(1))
        page.mergePage(challenges.getPage(page_num))
        output.addPage(page)

    with open(output_file, 'wb') as out_f:
        output.write(out_f)


generateOdt('challenges.odt', [['one', 'two'], ['three', 'four']])
convertOdtToPdf('challenges.odt')
mergePDFs('agenda_a5.pdf', 'challenges.pdf', 'output.pdf')
