#! /usr/bin/python

"""VLC Widget classes.

This module provides two helper classes, to ease the embedding of a
VLC component inside a pygtk application.

VLCWidget is a simple VLC widget.

DecoratedVLCWidget provides simple player controls.

$Id$
"""

import gtk
import sys
import vlc

from gettext import gettext as _

# Create a single vlc.Instance() to be share by (possible) multiple players.
instance=vlc.Instance()

class VLCWidget(gtk.DrawingArea):
    """Simple VLC widget.

    Its player can be controlled through the 'player' attribute, which
    is a vlc.MediaPlayer() instance.
    """
    def __init__(self, *p):
        gtk.DrawingArea.__init__(self)
        self.player=instance.media_player_new()
        def handle_embed(*args):
            if sys.platform == 'win32':
                self.player.set_hwnd(self.window.handle)
            else:
                self.player.set_xwindow(self.window.xid)
            return True
        self.connect("map", handle_embed)
        self.set_size_request(320, 200)

    def set_media_url(self, url):
        self.player.set_mrl(url)
        
    def play_media(self):
        self.realize()
        # self.player.set_visual(self.window.xid)
        self.player.play()
        
    def resume_media(self):
        self.player.resume()
        
    def stop_media(self):
        self.player.stop()
        
    def pause_media(self):
        self.player.pause()
        
    def exit_media(self):
	exit = True
        #self.player.exit()
        
    def display_text(self, text):
        self.player.display_text("%s" % text, 0, 5000)
        
    def is_fullscreen(self):
        return False
        
    def fullscreen(self):
	w=gtk.Window()
	self.reparent(w)
        self.player.set_fullscreen(True)
    
    def set_volume(self, level):
        self.player.audio_set_volume(level)
        
    def screenshot(self):
        return self.player.snapshot(0)

