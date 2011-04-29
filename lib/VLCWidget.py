#! /usr/bin/python

#! /usr/bin/python
# Copyright (C) 2009-2011 Jason Scheunemann <jason.scheunemann@yahoo.com>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

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

from WindowingTransformations import WindowingTransformations

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
		self.modify_bg(gtk.STATE_NORMAL, self.get_colormap().alloc_color("black"))
		self.set_size_request(320, 200)
		self.wt = WindowingTransformations(self)

	def set_media_url(self, url):
		self.player.set_mrl(url)
		
	def play_media(self):
		self.realize()
		self.player.play()

	def is_playing(self):
		return self.player.is_playing()
		
	def media_loaded(self):
		return self.is_playing()
		
	def resume_media(self):
		self.player.resume()
		
	def stop_media(self):
		self.player.stop()
		
	def pause_media(self):
		self.player.pause()
		
	def exit_media(self):
		exit = True
		
	def display_text(self, text):
		self.player.display_text("%s" % text, 0, 5000)
		
	def is_fullscreen(self):
		return False
		
	def fullscreen(self):
		self.wt.fullscreen()
	
	def unfullscreen(self):
		self.wt.unfullscreen()
		
	def fullwindow(self):
		self.wt.fullwindow()
	
	def unfullwindow(self):
		self.wt.unfullwindow()
	
	def set_volume(self, level):
		self.player.audio_set_volume(level)
		
	def screenshot(self):
		return self.player.snapshot(0)

