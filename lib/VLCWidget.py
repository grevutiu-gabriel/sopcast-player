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

class MakeFullscreen:
	def __init__(self, fs_widget):
		self.fs_widget = fs_widget
		self.hidden_widgets = []
		self.is_fullscreen = False
		self.is_fullwindow = False
	
	def fullscreen(self, fs=True):
		self.hidden_widgets = []
		
		self.hide_stuff(self.fs_widget)
		
		if fs == True:
			self.fs_widget.get_toplevel().fullscreen()
			self.is_fullscreen = True
		
	def hide_stuff(self, vis_widget):
		parent = vis_widget.get_parent()
		
		if parent is not parent.get_toplevel():
			for w in parent.get_children():
				if w is not vis_widget:
					if w.get_property("visible"):
						self.hidden_widgets.append(w)
						w.hide()
			self.hide_stuff(parent)
		else:
			return
	
	def unfullscreen(self):
		if self.is_fullscreen:
			self.fs_widget.get_toplevel().unfullscreen()
			self.is_fullscreen = False
			
		if self.is_fullwindow == False:
			for w in self.hidden_widgets:
				w.show()
			
	def fullwindow(self):
		self.is_fullwindow = True
		self.fullscreen(fs=False)
		
		
	def unfullwindow(self):
		self.is_fullwindow = False
		self.unfullscreen()
		

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
		self.mkfs = MakeFullscreen(self)

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
		self.mkfs.fullscreen()
	
	def unfullscreen(self):
		self.mkfs.unfullscreen()
	
	def set_volume(self, level):
		self.player.audio_set_volume(level)
		
	def screenshot(self):
		return self.player.snapshot(0)

