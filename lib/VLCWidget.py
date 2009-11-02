# Copyright (C) 2009 Jason Scheunemann <jason.scheunemann@yahoo.com>.
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

import gtk
import sys
import vlc

from gettext import gettext as _

instance=vlc.Instance()

class VLCWidget(gtk.DrawingArea):
	def __init__(self, *p):
		gtk.DrawingArea.__init__(self)
		self.player=instance.mediacontrol_new_from_instance()
		def handle_embed(*args):
			if sys.platform == 'win32':
				self.player.set_hwnd(self.window.handle)
			else:
				self.player.set_xwindow(self.window.xid)
			return True
		self.connect("map-event", handle_embed)
		self.set_size_request(320, 200)
        
	def set_media_url(self, url):
		self.player.set_mrl(url)
		
	def play_media(self):
		self.realize()
		self.player.set_visual(self.window.xid)
		self.player.start(0)
		
	def resume_media(self):
		self.player.resume()
		
	def stop_media(self):
		self.player.stop()
		
	def pause_media(self):
		self.player.pause()
		
	def exit_media(self):
		self.player.exit()
		
	def display_text(self, text):
		self.player.display_text("%s" % text, 0, 5000)
		
	def is_fullscreen(self):
		if self.player.get_fullscreen() == 1:
			return True
		else:
			return False
		
	def fullscreen(self):
		self.player.set_fullscreen(True)
	
	def set_volume(self, level):
		self.player.sound_set_volume(level)
		
	def screenshot(self):
		return self.player.snapshot(0)

