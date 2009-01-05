#! /usr/bin/python

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
import AddBookmark
import ChannelGuide
import DatabaseOperations
import dynamic_ports
import fork
import listen
import pySocket
import pySopCastConfigurationManager
import signal
import vlc
import VLCWidget

#mma: sop://broker.sopcast.com:3912/65416

class UpdateUIThread(threading.Thread):
	def __init__ (self, parent):
		threading.Thread.__init__(self)
		self.daemon = True
		self.parent = parent
		self.sleep_time = .1
		self.terminate = False
		self.run_thread = False
		self.play_stream = False
		self.wait_before_retry_time = 3 / self.sleep_time
		self.wait_before_restart = 3 / self.sleep_time
		self.time_waiting = 0
		self.retry = False
		
	def run(self):
		i = 0
		loading = False
		retry = False
		was_playing = False
		while self.terminate == False:
			if self.run_thread == True:
				if self.parent.fork_sop.is_running() == True:
					stats = self.parent.sop_stats.update_stats()
					
					if stats == None:
						if was_playing == True:
							self.parent.stop_vlc()							
							was_playing = False
							
						if retry == True:
							self.time_waiting += 1
						
							if self.time_waiting > self.wait_before_restart:
								self.parent.fork_sop.kill_sop()
							else:
								gtk.gdk.threads_enter()
								self.parent.update_statusbar("%s" % _("Retrying channel"))
								gtk.gdk.threads_leave()
						else:
							if loading == True:
								self.time_waiting += 1
								if self.time_waiting > self.wait_before_retry_time:
									retry = True
									self.time_waiting = 0
							loading = True
							
							gtk.gdk.threads_enter()
							self.parent.update_statusbar("%s" % _("Connecting"))
							gtk.gdk.threads_leave()
					
							if self.play_stream == True:
								self.play_stream = False
					else:
						self.time_waiting = 0
						loading = False
						retry = False
						if int(stats[0]) < 10:
							if i == 5:
								if int(stats[0]) > 0:
									gtk.gdk.threads_enter()
									self.parent.update_statusbar("%s: %s%%" % (_("Buffering"), stats[0]))
									gtk.gdk.threads_leave()
								else:
									gtk.gdk.threads_enter()
									self.parent.update_statusbar("%s" % _("Connecting"))
									gtk.gdk.threads_leave()
								i = 0
						else:
							if i == 5:
								gtk.gdk.threads_enter()
								self.parent.update_statusbar("%s: %s%%" % (_("Buffer"), stats[0]))
								gtk.gdk.threads_leave()
								i = 0
								
							if self.play_stream == False:
								gtk.gdk.threads_enter()
								self.parent.update_statusbar("%s: %s%%" % (_("Buffer"), stats[0]))
								gtk.gdk.threads_leave()
								
								gtk.gdk.threads_enter()
								started = self.parent.start_vlc()
								gtk.gdk.threads_leave()
								
								if started == True:
									self.play_stream = True
									was_playing = True
							
							loading = False
						i += 1

				else:
					gtk.gdk.threads_enter()
					self.parent.update_statusbar("")
					gtk.gdk.threads_leave()
					
					self.play_stream = False
					loading = False
					
					gtk.gdk.threads_enter()
					self.parent.play_channel()
					gtk.gdk.threads_leave()
					
					self.time_waiting = 0
					loading = False
					retry = False
									
			time.sleep(self.sleep_time)
		self = None
		
	def startup(self):
		self.run_thread = True
		
	def shutdown(self):
		self.run_thread = False
		self.play_stream = False
			
	def stop(self):
		self.terminate = True
		self = None


class PlayerStatus:
	Undefined = 0	
	Initializing = 1
	Buffering = 2
	Playing = 3
	Paused = 4
	Stopped = 5
	Forward = 6
	Backward = 7
	EndOfStream = 8
	Error = 9

class pySopCast(object):

	def __init__(self, *p):
		gtk.gdk.threads_init()
		self.vlc = VLCWidget.VLCWidget(*p)
		self.player = self.vlc.player
		self.ui_worker = None
		self.fork_sop = fork.ForkSOP()
		self.last_update = 0
		self.status_bar_text = None
		self.status_bar_text_changed = False
		self.db_operations = DatabaseOperations.DatabaseOperations()
		self.channel_url = None
		self.static_ports = False
		self.server = self.get_server()
		self.inbound_port, self.outbound_port = self.get_ports()
		self.sop_stats = listen.SOPStats(self.server, self.outbound_port)
		self.display_message_from_main_thread = False
		self.start_display_time = None
		self.display_message_time = 5
		
	def main(self, sop_address=None, sop_address_name=None):
		gladefile = os.path.abspath("%s/%s") % (os.path.dirname(sys.argv[0]), 'ui/pySopCast.glade')
		self.glade_window = gtk.glade.XML(gladefile, "window")
		self.window = self.glade_window.get_widget("window")
		self.window.set_title("%s" % _("SopCast Player"))
		
		dic = { "on_mainWindow_destroy" : self.on_exit,
			"on_play_button_clicked" : self.on_play_button_clicked,
			"on_channel_url_entry_activate" : self.on_play_button_clicked,
			"on_menu_quit_activate" : self.on_exit,
			"on_menu_fullscreen_activate" : self.on_fullscreen_activate,
			"on_menu_add_bookmark_activate" : self.on_add_bookmark,
			"on_toolbar_bookmark_clicked" : self.on_add_bookmark,
			"on_toolbar_channel_guide_clicked" : self.on_toolbar_channel_guide_clicked,
			"on_toolbar_fullscreen_clicked" : self.on_fullscreen_activate,
			"on_stop_clicked" : self.on_stop_clicked,
			"on_volume_adjust_bounds" : self.on_volume_adjust_bounds,
			"on_menu_about_activate" : self.on_menu_about_activate }

		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		self.volume.set_value(config_manager.getint("player", "volume"))
			
		self.glade_window.signal_autoconnect(dic)
		self.eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
		
		self.populate_bookmarks()
		self.load_channel_url_entry_autocompletion()
		
		self.ui_worker = UpdateUIThread(self)
		self.ui_worker.start()
		
		self.window.show_all()
		
		if sop_address != None:
			if sop_address[:len("sop://".lower())] == "sop://".lower():
				self.play_channel(sop_address, sop_address_name)
		
		self.window.show_all()
		
		gtk.gdk.threads_enter()
		gtk.main()
		gtk.gdk.threads_leave()
		
	def __getattribute__(self, key):
		value = None
		try:
			value = object.__getattribute__(self, key)
		except AttributeError:
			glade_window = object.__getattribute__(self, 'glade_window')
			value = glade_window.get_widget(key)	

		return value
	
	def get_server(self):
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		return config_manager.get("player", "server")
	
	def get_ports(self):
		inbound_port = None
		outbound_port = None
		
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		if config_manager.getboolean("player", "static_ports") == True:
			inbound_port = config_manager.getint("player", "inbound_port")
			outbound_port = config_manager.getint("player", "outbound_port")
			self.static_ports = True
			s = pySocket.pySocket()
			if not s.is_available(self.server, inbound_port) or not s.is_available(self.server, outbound_port):
				dyn = dynamic_ports.DynamicPorts()
				inbound_port, outbound_port = dyn.get_ports()
				self.static_ports = False
		else:
			dyn = dynamic_ports.DynamicPorts()
			inbound_port, outbound_port = dyn.get_ports()
		
		return inbound_port, outbound_port
		
	def load_channel_url_entry_autocompletion(self):
		completion = gtk.EntryCompletion()
		self.channel_url_entry.set_completion(completion)
		possibility_store = gtk.ListStore(str)
		
		for bookmark in self.db_operations.retrieve_bookmarks():
			possibility_store.append([bookmark[1]])
		
		completion.set_model(possibility_store)
		completion.set_text_column(0)
		
	def populate_bookmarks(self):
		self.clear_bookmarks()
		for bookmark in self.db_operations.retrieve_bookmarks():
			menu_item = gtk.MenuItem(bookmark[1])
			menu_item.connect("activate", self.on_menu_bookmark_channel_activate, bookmark)
			self.menu_bookmarks.get_submenu().append(menu_item)
			self.menu_bookmarks.get_submenu().show_all()
			
	def clear_bookmarks(self):
		menu_items = self.menu_bookmarks.get_submenu().get_children()
		
		if len(menu_items) > 2:
			i = 2
			while i < len(menu_items):
				self.menu_bookmarks.get_submenu().remove(menu_items[i])
				i += 1
		
	def on_menu_bookmark_channel_activate(self, src, channel_info):
		self.play_channel(channel_info[2])
		self.channel_url_entry.set_text(channel_info[1])
		
	def on_add_bookmark(self, src, data=None):
		if self.channel_url_entry.get_text()[:len("sop://".lower())] != "sop://".lower():
			add_bookmark_dialog = AddBookmark.AddBookmark(self, self.channel_url_entry.get_text())
		else:
			add_bookmark_dialog = AddBookmark.AddBookmark(self)
			
		add_bookmark_dialog.main()
	
	def on_stop_clicked(self, src, data=None):
		self.stop_vlc()
		
		self.ui_worker.shutdown()
		if self.fork_sop.is_running() == True:
			self.fork_sop.kill_sop()
		
		self.update_statusbar("")
		
	def on_volume_adjust_bounds(self, src, data=None):
		self.vlc.set_volume(int(src.get_value()))
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		config_manager.set("player", "volume", int(src.get_value()))
		config_manager.write()
	
	def on_menu_about_activate(self, src, data=None):
		gladefile = os.path.abspath("%s/%s") % (os.path.dirname(sys.argv[0]), 'ui/About.glade')
		about_file = gtk.glade.XML(gladefile, "about")
		about = about_file.get_widget("about")
		about.set_transient_for(self.window)
		about.run()
		about.destroy()
		
	def update_status_bar_text(self, txt):
		self.status_bar_text = txt
		self.status_bar_text_changed = True
		
	def start_vlc(self):
		if self.vlc.get_parent() == None:
			self.eb.add(self.vlc)
			self.window.show_all()
			return False
			
		if self.vlc.get_parent() == self.eb:
			self.vlc.play_media()
			return True
		else:
			return False
			
	def stop_vlc(self):
		if self.eb != None:
			self.vlc.stop_media()
			if self.vlc.get_parent() == self.eb:
				self.eb.remove(self.vlc)
				if self.window != None:
					self.window.show_all()
		
	def play_channel(self, channel_url=None, title=None):
		if self.fork_sop.is_running() == True:
			self.fork_sop.kill_sop()
		
		s = pySocket.pySocket()
		if not s.is_available(self.server, self.inbound_port) or not s.is_available(self.server, self.outbound_port):
			self.inbound_port, self.outbound_port = self.get_ports()
			
		if channel_url != None:
			self.channel_url = channel_url
			if title == None:
				self.channel_url_entry.set_text(channel_url)
			
		if title != None:
			self.channel_url_entry.set_text(title)
		else:
			records = self.db_operations.retrieve_bookmark_by_address(self.channel_url)
			if len(records) > 0:
				self.channel_url_entry.set_text(records[0][0])
			else:
				records = self.db_operations.retrieve_channel_guide_record_by_address(self.channel_url)
				if len(records) > 0:
					self.channel_url_entry.set_text(records[0][0])
			
		self.fork_sop.fork_sop(self.channel_url, str(self.inbound_port), str(self.outbound_port))
		
		self.menu_add_bookmark.set_sensitive(True)
		self.toolbar_bookmark.set_sensitive(True)
		self.toolbar_fullscreen.set_sensitive(True)
		self.menu_fullscreen.set_sensitive(True)
		
		url = "http://%s:%d/tv.asf" % (self.server, self.outbound_port)
		self.vlc.set_media_url(url)
		self.ui_worker.startup()

	def on_play_button_clicked(self, src, data=None):
		if len(self.channel_url_entry.get_text()):
			if self.channel_url_entry.get_text()[:len("sop://".lower())] != "sop://".lower():
				records = self.db_operations.retrieve_bookmark_by_channel_name(self.channel_url_entry.get_text())
			
				if len(records) > 0:
					self.play_channel(records[0][2], records[0][1])
				else:
					records = self.db_operations.retrieve_channel_guide_record_by_channel_name(self.channel_url_entry.get_text())
					if len(records) > 0:
						self.play_channel(records[0][0], self.channel_url_entry.get_text())
					else:
						self.update_statusbar("%s %s" % (self.channel_url_entry.get_text(), _("could not be found in bookmarks or channel guide")), 3)
			else:
				self.play_channel(self.channel_url_entry.get_text())
		else:
			self.update_statusbar("%s" % _("Please enter a bookmark name or sop address or use the channel guide to select a channel"))
			
		return True
		
	def lookup_title(self, title):
		if self.title[:len("sop://".lower())] == "sop://".lower():
			records = self.db_operations.retrieve_bookmark_by_address(channel_url)
			if len(records) > 0:
				self.channel_url_entry.set_text(records[0][0])
			else:
				records = self.db_operations.retrieve_channel_guide_record_by_address(channel_url)
				if len(records) > 0:
					self.channel_url_entry.set_text(records[0][0])
				else:
					self.play_channel(channel_url)
		else:
			
			if len(records) > 0:
				self.play_channel(records[0][2], title)
			else:
				'''Invalid channel'''
	
	def on_fullscreen_activate(self, src, data=None):
		if self.ui_worker.play_stream == True:
			self.vlc.fullscreen()
			self.vlc.display_text("         %s" % _("Press Esc to exit fullscreen"))
			
	def on_exit(self, widget, data=None):
		if self.ui_worker.run_thread == True:
			self.fork_sop.kill_sop()
			self.ui_worker.stop()
			self.vlc.stop_media()
			self.vlc.exit_media()
			
		gtk.main_quit()
		self = None

	def on_eb_key_press_event(self, widget, event, data=None):
		key = event.keyval
		
		if self.eb.is_focus() == True:
			if key == 70 or key == 102:
				self.vlc.fullscreen()
				self.vlc.display_text("         %s" % _("Press Esc to exit fullscreen"))
		
		return False
		
	def on_toolbar_channel_guide_clicked(self, src, data=None):
		channel_guide = ChannelGuide.ChannelGuide(self)
		channel_guide.main()
	
	def add_bookmark(self, channel_name, url=None):
		if url == None:
			url = self.channel_url
		
		self.db_operations.insert_bookmark(channel_name, url)
		self.populate_bookmarks()
		
		if url == self.channel_url:
			self.channel_url_entry.set_text(channel_name)
	
	def update_statusbar(self, text, display_time=None):
		if self.status_bar != None:
			if display_time != None:
				self.status_bar.push(1, text)
				self.display_message_from_main_thread = True
				self.display_message_time = display_time
				self.start_display_time = time.time()
			
			if self.display_message_from_main_thread == True and self.start_display_time != None:
				if time.time() - self.start_display_time > self.display_message_time:
					self.display_message_from_main_thread = False
					self.start_display_time = None
			else:
				self.status_bar.push(1, text)
		
	def set_title(self, title="pySopCast"):
		self.window.set_title(title)
		
	def set_play_button_stock_id(self, stock_id):
		self.play_button.set_label(stock_id)
		
	def set_play_button_active(self, active=True):
		self.play_button.set_sensitive(active)
		
if __name__ == '__main__':
	pySop = pySopCast()
	pySop.main()
