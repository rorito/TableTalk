#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# worlde.py
# Copyright (c) 2009 - Nicolas P. Rougier
#
# wordle.py is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# wordle.py is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# wordle.py. If not, see <http://www.gnu.org/licenses/>.
#
# -----------------------------------------------------------------------------
import cairo
import numpy as np
import pyglet, pyglet.gl as gl


def np_crop(Z, empty=255):
    ''' Crop an array by removing empty margins around it

    :Parameters:
        `Z` : numpy array
             Array to be cropped
        `empty` : scalar
             Value to be considered empty
    :Return:
        Cropped array, Z center shift
    '''
    if len(Z.shape) == 2:
        Z = Z.reshape (Z.shape+(1,))
    height,width,depth = Z.shape

    x = 0
    while x >= 0 and (Z[:,x,:] == empty).all(): x += 1
    x_left = max(0,x-1)
    x = width-1
    while x >= 0 and (Z[:,x,:] == empty).all(): x -= 1
    x_right = min(width,x+1)
    y = 0
    while y >= 0 and (Z[y,:,:] == empty).all(): y += 1
    y_bottom = max(0,y-1)
    y = height-1
    while y >= 0 and (Z[y,:,:] == empty).all(): y -= 1
    y_top = min(height,y+1)

    dx = -(x_left+(x_right-x_left)//2 - Z.shape[1]//2)
    dy = -(y_bottom+(y_top-y_bottom)//2 - Z.shape[0]//2)
    return Z[y_bottom:y_top:,x_left:x_right], (dx,dy)


def np_text(text, fontname='sans', fontsize=48, angle=0):
    ''' Generate an text within an array

    :Parameters:
        `text` : str
            Text to be generated
        `fontname` : str
            Font family name
        `fontsize` : int
            Font size
        `angle` : float
            Text angle
    '''

    # Dummy surface to get text extents
    surface = cairo.ImageSurface(cairo.FORMAT_A8, 1, 1)
    ctx = cairo.Context(surface)
    ctx.select_font_face(fontname)
    ctx.set_font_size(fontsize)
    (x, y, w, h, dx, dy) = ctx.text_extents(text)
    size = (int(np.sqrt(w**2+h**2)+1)//4)*4+4
    
    # Actual surface
    surface = cairo.ImageSurface(cairo.FORMAT_A8, size, size)
    ctx = cairo.Context(surface)
    options = cairo.FontOptions()
    options.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
    options.set_hint_style(cairo.HINT_STYLE_FULL)
    ctx.set_font_options(options)
    ctx.set_source_rgba(0,0,0,0)
    ctx.paint()
    ctx.set_source_rgba(1,1,1,1)
    ctx.select_font_face(fontname)
    ctx.set_font_size(fontsize)
    ctx.move_to(size//2,size//2)
    ctx.rotate(angle)
    ctx.rel_move_to(-w//2,h//2)
    ctx.show_text(text)

    # Make an array oput of surface
    buf = surface.get_data()
    Z = np.frombuffer(buf, np.uint8)
    Z.shape = (size,size,1)
    return np_crop(Z,0)




class Word(object):
    def __init__(self, text, link, weight, x, y, w, h ,angle):
        self.text = text
        self.link = link
        self.weight = weight
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.angle = angle


class WordCloud(object):

    def __init__(self, words):
        ''' Initialize the cloud

        :Parameters:
            `words`: [(word,link,weight),...]
                List of words with associated links and relative weights
        '''

        # Determine minimum and maximum weights
        min_weight = words[0][2]
        max_weight = words[0][2]
        for word in words:
            text, link, weight = word
            min_weight = min(min_weight, weight)
            max_weight = max(max_weight, weight)

        # Normalize weights
        self.words = []
        for word in words:
            text, link, weight = word
            weight = (weight-min_weight)/float(max_weight-min_weight)
            self.words.append (Word(text,link,weight,-1,-1,0,0,0))
        
        # Set a color palette
        self.palette = [(204,204,204,255),
                        (153,102,102,255),
                        (102,0,0,255),
                        (51,0,0,255),
                        (102,102,102,255)]

        # Font to be used
        self.fontname = 'sans'
        self.fontsize_min = 20
        self.fontsize_max = 60


    def generate(self, width, height):
        ''' Generate the cloud on a surface of dimensions width x height
        '''
        self._width = width
        self._height = height

        # Cairo surface that will hold the final result
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(self.surface)
        options = cairo.FontOptions()
        options.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        options.set_hint_style(cairo.HINT_STYLE_FULL)
        ctx.set_font_options(options)
        ctx.set_source_rgba(1,1,1,1)
        ctx.paint()

        # numpy array that will serve for collisions tests
        Z = np.zeros((height,width), dtype=np.int8)

        for i in range(len(self.words)):
            word = self.words[i]
            #txt,link,weight,x,y,w,h,angle = self.words[i]

            fontname = self.fontname
            fontsize = self.fontsize_min + \
                        int(word.weight*(self.fontsize_max - self.fontsize_min))

            # Choose angle
            angle = 0
            if np.random.uniform() < 0.25:
                angle = -np.pi/2
            #angle = np.random.normal(0.0,0.05)
                
            angle += np.random.normal(0.0,0.025)

            # Get an array with text in it
            z,(dx,dy) = np_text(word.text,fontname,fontsize,angle)
            h,w,d = z.shape
            z.shape = z.shape[:2]

            hit = 250
            r = .01
            while hit > 0:

                # Choose a random center
                theta = np.random.random()*np.pi*2
                x = .5+.5*np.cos(theta)*r
                y = .5+.5*np.sin(theta)*r
                r += .005
                x = min(max(int(x*width), w//2), width-1-w//2)
                y = min(max(int(y*height), h//2), height-1-h//2)

                # Test collision
                if (Z[y-h//2:y-h//2+h,x-w//2:x-w//2+w]*z).sum() == 0:
                    Z[y-h//2:y-h//2+h,x-w//2:x-w//2+w] += z
                    r,g,b,a = self.palette[np.random.randint(0, len(self.palette))]
                    ctx.save()
                    ctx.select_font_face(fontname)
                    ctx.set_font_size(fontsize)
                    (xt, yt, wt, ht, tdx, tdy) = ctx.text_extents(word.text)
                    ctx.set_source_rgba(g/255.,b/255.,r/255.,1)
                    ctx.move_to(x+dx,y+dy)
                    ctx.rotate(angle)
                    ctx.rel_move_to(-wt//2, ht//2)
                    ctx.show_text(word.text)
                    ctx.restore()
                    hit = 0
                    word.x = x+dx
                    word.y = y+dy
                    word.w = wt
                    word.h = ht
                    word.angle = angle
                else:
                    word.x, word.y = -1, -1
                    hit -= 1
                    
        # Generate a texture fro pyglet display
        buf = self.surface.get_data()
        Z = np.frombuffer(buf, np.uint8)
        Z.shape = (height,width,4)
        Z = Z[::-1]
        self.image = pyglet.image.ImageData(width,height, format='RGBA', data=Z.tostring())


    def save(self):

        # Generate a pyglet image from cairo surface
        buf = self.surface.get_data()
        Z = np.frombuffer(buf, np.uint8)
        width, height = self._width, self._height
        Z.shape = (height,width,4)
        Z = Z[::-1]
        height, width, depth = Z.shape
        image = pyglet.image.ImageData(width,height, format='RGBA', data=Z.tostring())

        filename = 'cloud'
        image.save(filename+'.png')
        f = open(filename+'.map', 'w')
        f.write('<img src="%s" width="%d" height="%d" border="0" usemap="#map" />\n' % (filename+'.png',width,height))
        f.write('<map name="map">\n')
        for i in range(len(self.words)):
            word = self.words[len(self.words)-1-i]
            link = word.link
            if not link:
                link = word.text.replace(' ', '_')+'.html'
            if word.x >= 0 and word.y >=0:
                dx = int(np.cos(word.angle)*word.w/2+np.sin(word.angle)*word.h/2)
                dy = int(np.cos(word.angle)*word.h/2+np.sin(word.angle)*word.w/2)
                x0,y0 = word.x-dx,word.y-dy
                x1,y1 = word.x-dx,word.y+dy
                x2,y2 = word.x+dx,word.y+dy
                x3,y3 = word.x+dx,word.y-dy
                f.write('<area shape="poly" coords="%d,%d,%d,%d,%d,%d,%d,%d" href="%s" />\n' % (
                        x0,y0,x1,y1,x2,y2,x3,y3,link))
        f.write('</map>\n')
        f.close()


    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.SPACE:
            self.generate(self.image.width,self.image.height)
        elif symbol == pyglet.window.key.S:
            self.save()

    def on_draw(self):
        gl.glClearColor(1,1,1,1)
        self.window.clear()
        gl.glColor4f(1,1,1,1)
        w,h = self.image.width, self.image.height
        self.image.blit(x=0,y=0,width=w,height=h)


    def show(self):
        self.generate(600,400)
        self.window = pyglet.window.Window(self.image.width,self.image.height)
        gl.glClearColor(0,0,0,1)
        gl.glBlendFunc (gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_BLEND)
        self.window.push_handlers(self)
        pyglet.app.run()



if __name__ == '__main__':

    words = [('nicolas rougier', 'http://www.loria.fr/~rougier/', 700),
             ('home',          'http://www.loria.fr/~rougier/', 500),
             ('research',     'http://www.loria.fr/~rougier/research.html', 500),
             ('demos',        'http://www.loria.fr/~rougier/demos.html', 500),
             ('software',     'http://www.loria.fr/~rougier/software.html', 500),
             ('artwork',      'http://www.loria.fr/~rougier/artwork.html', 500),
             ('loria',        'http://www.loria.fr', 400),
             ('inria',        'http://www.inria.fr', 400),
             ('cortex',       'http://cortex.loria.fr', 400),
             ('publications', 'http://hal.inria.fr/autlab/rougier/cortex/',              400),
             ('neuroscience',   '',              400),
             ('computational', '',              400),
             ('brain',         '',              300),
             ('perception',    '',              300),
             ('action',        '',              300),
             ('robotics',      '',              300),
             ('emergence',     '',              300),
             ('learning',      '',              300),
             ('attention',     '',              300),
             ('memory',        '',              300),
             ('mathematics',   '',              300),
             ('neural fields', '',              300),
             ('dana',          '',              300),
             ('glumpy',        '',              300),
             ('python',        '',              200),
             ('numpy',         '',              200),
             ('scipy',         '',              200),
             ('opengl',        '',              200),
             ('matplotlib',    '',              200),
             ('pyglet',        '',              200),
             ('pyroom',        '',              200),
             ('gtk',           '',              200),
             ('simulations',   '',              200),
             ('CNFT',          '',              200),
             ('neurons',       '',              200),
             ('scigl',         '',              200),
             ('gnubiff',       '',              200),
             ('emacs',         '',              200)]

    cloud = WordCloud(words)
    cloud.show()