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
	def __init__(self, container):
		gtk.DrawingArea.__init__(self)
		self.player=instance.media_player_new()
		self.container = container
		def handle_embed(*args):
			if sys.platform == 'win32':
				self.player.set_hwnd(self.window.handle)
			else:
				self.player.set_xwindow(self.window.xid)
			return True
		self.connect("map", handle_embed)
		self.modify_bg(gtk.STATE_NORMAL, self.get_colormap().alloc_color("black"))
		self.set_size_request(320, 200)
		self.wt = WindowingTransformations(self.container)
		self.is_fs = False
		
		self.add_events(gtk.gdk.BUTTON_PRESS_MASK)
		self.connect("button_press_event", self.on_mouse_click)
		
		self.get_toplevel().connect("key-press-event", self.on_key_press)

	def on_key_press(self, widget, event, data=None):
		"key pressed"
		if event.keyval == gtk.keysyms.escape:
			if self.is_fullscreen():
				self.toggle_fullscreen()
			return True
		elif gtk.gdk.keyval_name(event.keyval) in ["f", "F"]:
			print "f pressed"
			self.toggle_fullscreen()
		return False
		
	def on_mouse_click(self, widget, event):
		if event.type == gtk.gdk._2BUTTON_PRESS:
			if self.is_playing():
				self.toggle_fullscreen()
		else:
			return True
			
	def toggle_fullscreen(self):
		if self.is_fs:
			self.unfullscreen()
		else:
			self.fullscreen()

	def set_media_url(self, url):
		self.player.set_mrl(url)
		
	def play_media(self):
		self.player.play()
		if len(self.container.get_children()) == 0:
			self.container.add(self)
		self.show()

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
		return self.is_fs
		
	def fullscreen(self):
		self.wt.fullscreen()
		self.is_fs = True
	
	def unfullscreen(self):
		self.wt.unfullscreen()
		self.is_fs = False
		
	def fullwindow(self):
		self.wt.fullwindow()
	
	def unfullwindow(self):
		self.wt.unfullwindow()
	
	def set_volume(self, level):
		self.player.audio_set_volume(level)
		
	def screenshot(self):
		return self.player.snapshot(0)

