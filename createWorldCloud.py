# -*- coding: utf-8 -*-
import sys
sys.path.append("/Users/rory/Dropbox/dev/TableTalk/PyTagCloud/src/")
from pytagcloud import create_tag_image, create_html_data, make_tags, \
    LAYOUT_HORIZONTAL, LAYOUTS, LAYOUT_MIX
from pytagcloud.colors import COLOR_SCHEMES
from pytagcloud.lang.counter import get_tag_counts
import os
import time
import unittest
import pygame

TE_PHRASES_FILE = "tabletalk_te_phrases.txt"
WIDTH=1280
HEIGHT=900
IMAGE_FILE = 'cloud_large.png'

def main():	
	pyGameDisplay()

def createWordCloud():	
	words_file = open(TE_PHRASES_FILE,'r')
	tags = make_tags(get_tag_counts(words_file.read())[:120], maxsize=120, colors=COLOR_SCHEMES['audacity'])
	create_tag_image(tags, os.path.join(os.getcwd(), IMAGE_FILE), size=(WIDTH, HEIGHT), background=(0, 0, 0, 255), layout=LAYOUT_MIX, crop=True, fontname='Lobster', fontzoom=1)

def pyGameDisplay():
	pygame.init() #load pygame modules
	size = width, height = WIDTH, HEIGHT #size of window

	screen = pygame.display.set_mode(size) #make window
	tagCloud = pygame.image.load(IMAGE_FILE)
	
	while 1:
		createWordCloud()
		screen.blit(tagCloud, tagCloud.get_rect())
		pygame.display.update()
		time.sleep(2)

if __name__ == "__main__":
    main()