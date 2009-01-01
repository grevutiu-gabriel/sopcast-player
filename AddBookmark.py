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

import gobject
from gettext import gettext as _
import gtk
import gtk.glade
import sys
import threading
import time
import os

sys.path.append(os.path.abspath("%s/%s") % (os.path.dirname(sys.argv[0]), 'lib/'))
import fork
import listen
import vlc
import VLCWidget


class AddBookmark(object):

	def __init__(self, parent, title=None, url=None):
		self.window = None
		self.parent = parent
		self.title = title
		self.url = url
		
	def main(self):
		gladefile = os.path.abspath("%s/%s") % (os.path.dirname(sys.argv[0]), 'ui/AddBookmark.glade')
		self.glade_window = gtk.glade.XML(gladefile, "window")
		self.window = self.glade_window.get_widget("window")
		self.window.set_modal(True)
		self.window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
		self.window.set_transient_for(self.parent.window)
		
		dic = { "on_window_destroy" : gtk.main_quit,
			"on_cancel_clicked" : self.on_cancel_clicked,
			"on_done_clicked" : self.on_done_clicked }
		
		if self.title != None:
			self.channel_name.set_text(self.title)
			self.channel_name.select_region(0, -1)
			
		self.glade_window.signal_autoconnect(dic)
		
		gtk.main()
		
	def set_title(self, title):
		self.title = title
		
	def set_url(self, url):
		self.url = url
		
	def on_cancel_clicked(self, src, data=None):
		self.window.destroy()
		
	def on_done_clicked(self, src, data=None):
		self.parent.add_bookmark(self.channel_name.get_text(), self.url)
		
		self.window.destroy()
		
	def __getattribute__(self, key):
		value = None
		try:
			value = object.__getattribute__(self, key)
		except AttributeError:
			glade_window = object.__getattribute__(self, 'glade_window')
			value = glade_window.get_widget(key)	

		return value
