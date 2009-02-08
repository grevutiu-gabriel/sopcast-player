#! /usr/bin/env python

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
import gettext
import gtk
import gtk.glade
import locale
import math
import sys
import threading
import time
import os

sys.path.append("%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "lib"))
#sys.path.append("/usr/share/sopcast-player/lib")
import DatabaseOperations
import dynamic_ports
import FileDownload
import fork
import ImportChannelGuide
import listen
import pySocket
import pySopCastConfigurationManager
import signal
import vlc
import VLCWidget

#cur_locale = locale.setlocale(locale.LC_ALL, "")
cur_locale = locale.setlocale(locale.LC_ALL, ("zh_CN", "utf8"))

gtk.glade.bindtextdomain("sopcast-player", "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "locale"))
gtk.glade.textdomain("sopcast-player")

gettext.bindtextdomain("sopcast-player", "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "locale"))
gettext.textdomain("sopcast-player")

lang = gettext.translation("sopcast-player", "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "locale"), [cur_locale], fallback=True)
lang.install('sopcast-player')

#mma: sop://broker.sopcast.com:3912/65416

def is_chinese():
	return not cur_locale[:len("zh".lower())] != "zh".lower()

class UpdateUIThread(threading.Thread):
	def __init__ (self, parent, channel_timeout=3):
		threading.Thread.__init__(self)
		self.daemon = True
		self.parent = parent
		self.sleep_time = .1
		self.terminate = False
		self.run_thread = False
		self.play_stream = False
		self.wait_before_retry_time = channel_timeout / self.sleep_time
		self.wait_before_restart = 3 / self.sleep_time
		self.time_waiting = 0
		self.paused = True
		self.terminated = False
		self.retry = False
		self.volume = None
		self.external_player = fork.ForkExternalPlayer()
		
	def run(self):
		err_point = 0
		i = 0
		loading = False
		retry = False
		was_playing = False
		while self.terminate == False:
			if self.run_thread == True:
				self.paused = False
				if self.parent.fork_sop.is_running() == True and self.run_thread == True:
					stats = self.parent.sop_stats.update_stats()
					
					if stats == None and self.run_thread == True:
						if was_playing == True and self.run_thread == True:
							if self.parent.external_player_command != None:
								if self.parent.external_player_command != "":
									self.external_player.kill()
									print "stoping external media player"
							else:
								self.parent.stop_vlc()						
								
							was_playing = False
							
						if retry == True and self.run_thread == True:
							self.time_waiting += 1
							
							if self.time_waiting > self.wait_before_restart and self.run_thread == True:
								self.parent.fork_sop.kill_sop()
							else:
								gtk.gdk.threads_enter()
								self.parent.update_statusbar("%s" % _("Retrying channel"))
								gtk.gdk.threads_leave()
						else:
							if loading == True and self.run_thread == True:
								self.time_waiting += 1
								if self.time_waiting > self.wait_before_retry_time and self.run_thread == True:
									retry = True
									self.time_waiting = 0
							loading = True
							
							gtk.gdk.threads_enter()
							self.parent.update_statusbar("%s" % _("Connecting"))
							gtk.gdk.threads_leave()
					
							if self.play_stream == True and self.run_thread == True:
								self.play_stream = False
					else:
						self.time_waiting = 0
						loading = False
						retry = False
						started = True
						
						if stats != None:
							if int(stats[0]) < 10 and self.run_thread == True:
								if i == 5 and self.run_thread == True:
									if int(stats[0]) > 0 and self.run_thread == True:
										gtk.gdk.threads_enter()
										self.parent.update_statusbar("%s: %s%%" % (_("Buffering"), stats[0]))
										gtk.gdk.threads_leave()
									else:
										gtk.gdk.threads_enter()
										self.parent.update_statusbar("%s" % _("Connecting"))
										gtk.gdk.threads_leave()
									i = 0
							else:
								if i == 5 and self.run_thread == True:
									gtk.gdk.threads_enter()
									self.parent.update_statusbar("%s: %s%%" % (_("Buffer"), stats[0]))
									gtk.gdk.threads_leave()
								
									i = 0
								
								if self.play_stream == False and self.run_thread == True:
									gtk.gdk.threads_enter()
									self.parent.update_statusbar("%s: %s%%" % (_("Buffer"), stats[0]))
									gtk.gdk.threads_leave()
									
									if self.parent.external_player_command != None:
										if self.parent.external_player_command != "":
											self.external_player.fork_player(self.parent.external_player_command, self.parent.outbound_media_url)
											print "Executing " + self.parent.external_player_command
									else:
										gtk.gdk.threads_enter()
										started = self.parent.start_vlc()
										gtk.gdk.threads_leave()								
								
									if started == True and self.run_thread == True:
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
			else:
				self.paused = True
									
			time.sleep(self.sleep_time)
		self.external_player.kill()
		self.terminated = True
		
	def print_point_on_exit(self, point):
		if self.terminate == True:
			print point
	
	def set_channel_timeout(self, channel_timeout):
		if channel_timeout != sys.maxint:
			self.wait_before_retry_time = channel_timeout / self.sleep_time
		else:
			self.wait_before_retry_time = sys.maxint
		
	def startup(self):
		self.run_thread = True
		
	def shutdown(self):
		self.run_thread = False
		self.play_stream = False
			
	def stop(self):
		self.shutdown()
		self.terminate = True
		
		while self.terminated == False:
			time.sleep(self.sleep_time)
		
		return True

class UpdateChannelGuideThread(threading.Thread):
	def __init__ (self, parent):
		threading.Thread.__init__(self)
		self.parent = parent
		self.downloader = FileDownload.FileDownload()
		self.guide_import = ImportChannelGuide.ImportChannelGuide()
		self.daemon = True
		self.running = True
		self.updated = False
		self.last_updated = None
		
	def run(self):
		self.running = True
		chinese = False
		handler_blocked = False
		
		downloader = FileDownload.FileDownload()
		guide_import = ImportChannelGuide.ImportChannelGuide()
		
		gtk.gdk.threads_enter()
		self.parent.update_channel_guide_progress.set_text(_("Contacting Server"))
		gtk.gdk.threads_leave()
		
		try:
			db_operations = DatabaseOperations.DatabaseOperations()
			downloader.download_file(self.parent.channel_guide_url, os.path.expanduser('~/.pySopCast/channel_guide.xml'), self.report_progress)
			
			gtk.gdk.threads_enter()
			self.parent.update_channel_guide_progress.set_text(_("Updating Database"))
			gtk.gdk.threads_leave()
			
			guide_import.update_database(os.path.expanduser('~/.pySopCast/channel_guide.xml'))
			
			gtk.gdk.threads_enter()
			self.parent.treeview_selection.handler_block(self.parent.treeview_selection_changed_handler)
			gtk.gdk.threads_leave()
			
			handler_blocked = True
			
			gtk.gdk.threads_enter()
			self.parent.channel_treeview.set_model()
			gtk.gdk.threads_leave()
			
			gtk.gdk.threads_enter()
			self.parent.channel_treeview.get_selection().unselect_all()
			gtk.gdk.threads_leave()
			
			gtk.gdk.threads_enter()
			self.parent.channel_treeview_model.clear()
			gtk.gdk.threads_leave()
			
			if self.parent.channel_guide_language == _("English"):
				channel_groups = db_operations.retrieve_channel_groups()
			else:
				channel_groups = db_operations.retrieve_channel_groups_cn()
		
			for channel_group in channel_groups:
				gtk.gdk.threads_enter()
				channel_group_iter = self.parent.channel_treeview_model.append(None, self.parent.prepare_row_for_channel_treeview_model(channel_group))
				gtk.gdk.threads_leave()
				
				if self.parent.channel_guide_language == _("English"):
					channels = db_operations.retrieve_channels_by_channel_group_id(channel_group[0])
				else:
					channels = db_operations.retrieve_channels_by_channel_group_id_cn(channel_group[0])
		
				for channel in channels:
					gtk.gdk.threads_enter()
					self.parent.channel_treeview_model.append(channel_group_iter, self.parent.prepare_row_for_channel_treeview_model(channel))
					gtk.gdk.threads_leave()
			
			gtk.gdk.threads_enter()
			self.parent.channel_treeview.set_model(self.parent.channel_treeview_model)
			gtk.gdk.threads_leave()
			
			gtk.gdk.threads_enter()
			self.parent.update_channel_guide_progress.set_text(_("Completed"))
			gtk.gdk.threads_leave()
			
			config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
			self.last_updated = time.strftime(locale.nl_langinfo(locale.D_T_FMT))
			config_manager.set("ChannelGuide", "last_updated", self.last_updated)
			config_manager.write()
			self.updated = True
		except Exception, e:
			gtk.gdk.threads_enter()
			if self.parent.update_channel_guide_progress != None:
				self.parent.update_channel_guide_progress.set_text(_("Server Down"))
			gtk.gdk.threads_leave()
			print e
		
		if handler_blocked == True:
			gtk.gdk.threads_enter()
			self.parent.treeview_selection.handler_unblock(self.parent.treeview_selection_changed_handler)
			gtk.gdk.threads_leave()
		
		time.sleep(5)
		gtk.gdk.threads_enter()
		if self.parent.update_channel_guide_progress != None:
			self.parent.update_channel_guide_progress.hide()
			self.parent.channel_guide_label.show()
		gtk.gdk.threads_leave()
		
		self.running = False
		
	def report_progress(self, numblocks, blocksize, filesize):
		try:
			percent = min((numblocks*blocksize*100)/filesize, 100)
		except:
			percent = 100
		
		gtk.gdk.threads_enter()
		self.parent.update_channel_guide_progress.set_text("%s: %d%%" % (_("Downloading"), percent))
		gtk.gdk.threads_leave()
		
		gtk.gdk.threads_enter()
		self.parent.update_channel_guide_progress.set_fraction(float(percent / 100.0))
		gtk.gdk.threads_leave()		


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
	def __init__(self, channel_url=None, inbound_port=None, outbound_port=None, *p):
		gtk.gdk.threads_init()
		self.vlc = VLCWidget.VLCWidget(*p)
		self.player = self.vlc.player
		self.ui_worker = None
		self.fork_sop = fork.ForkSOP()
		self.last_update = 0
		self.status_bar_text = None
		self.status_bar_text_changed = False
		self.db_operations = DatabaseOperations.DatabaseOperations()
		self.channel_url = channel_url
		self.static_ports = False
		self.server = self.get_server()
		self.inbound_port = inbound_port
		self.outbound_port = outbound_port
		self.sop_stats = None
		self.display_message_from_main_thread = False
		self.start_display_time = None
		self.display_message_time = 5
		self.treeview_selection = None
		self.channel_guide_worker = None
		self.channel_guide_url = None
		self.window_title = "SopCast Player"
		self.hide_controls_size = None
		self.show_controls = True
		self.external_player_command = None
		self.outbound_media_url = None
		self.channel_guide_language = None
		
	def main(self, sop_address=None, sop_address_name=None):
		#gladefile = "%s/%s" % ("/usr/share/sopcast-player/ui", "pySopCast.glade")
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "ui/pySopCast.glade")
		self.glade_window = gtk.glade.XML(gladefile, "window", "sopcast-player")
		self.window = self.glade_window.get_widget("window")
		glade_context_menu = gtk.glade.XML(gladefile, "context_menu", "sopcast-player")
		self.context_menu = glade_context_menu.get_widget("context_menu")
		
		window_signals = { "on_mainWindow_destroy" : self.on_exit,
			"on_play_button_clicked" : self.on_play_button_clicked,
			"on_menu_quit_activate" : self.on_menu_quit_activate,
			"on_menu_fullscreen_activate" : self.on_fullscreen_activate,
			"on_menu_add_bookmark_activate" : self.on_add_bookmark,
			"on_stop_clicked" : self.on_stop_clicked,
			"on_volume_adjust_bounds" : self.on_volume_adjust_bounds,
			"on_menu_about_activate" : self.on_menu_about_activate,
			"on_open_sop_address_activate" : self.on_open_sop_address_activate,
			"on_refresh_channel_guide_clicked" : self.on_refresh_channel_guide_clicked,
			"on_menu_screenshot_activate" : self.on_menu_screenshot_activate,
			"on_menu_preferences_activate" : self.on_menu_preferences_activate,
			"on_menu_stay_on_top_toggled" : self.on_menu_stay_on_top_toggled,
			"on_menu_show_controls_toggled" : self.on_menu_show_controls_toggled,
			"on_window_key_press_event" : self.on_window_key_press_event,
			"on_channel_treeview_button_press_event" : self.on_channel_treeview_button_press_event }
		
		self.glade_window.signal_autoconnect(window_signals)
		
		context_menu_signals = { "on_context_menu_play_activate" : self.on_context_menu_play_activate }
		
		glade_context_menu.signal_autoconnect(context_menu_signals)

		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		self.player_volume = config_manager.getint("player", "volume")
		self.volume.set_value(self.player_volume)
		self.window.set_default_size(config_manager.getint("player", "width"), config_manager.getint("player", "height"))
		self.display_pane.set_position(config_manager.getint("player", "div_position"))
		show_channel_guide_pane = config_manager.getboolean("player", "show_channel_guide")
		channel_timeout = config_manager.getint("player", "channel_timeout")
		self.window.set_keep_above(config_manager.getboolean("player", "stay_on_top"))
		self.menu_stay_on_top.set_active(config_manager.getboolean("player", "stay_on_top"))
		
		if config_manager.getboolean("player", "external_player") == True:
			self.set_media_player_visible(False)
			self.external_player_command = config_manager.get("player", "external_player_command")
			show_channel_guide_pane = True
		
		last_updated = config_manager.get("ChannelGuide", "last_updated")
		self.channel_guide_url = config_manager.get("ChannelGuide", "url")
		self.channel_guide_hpane.set_position(config_manager.getint("ChannelGuide", "div_position"))
		
		
		self.channel_guide_language = config_manager.get("ChannelGuide", "channel_guide_language")

		
		textrenderer = gtk.CellRendererText()
		
		column = gtk.TreeViewColumn("Name", textrenderer, text=1)
		self.channel_treeview.append_column(column)
		
		self.channel_treeview_model = gtk.TreeStore(int, str, str, str, str, str, int, int, int, str)
		self.treeview_selection = self.channel_treeview.get_selection()
		self.treeview_selection_changed_handler = self.treeview_selection.connect("changed", self.on_selection_changed)
		self.channel_treeview.connect("row_activated", self.on_channel_treeview_row_activated)		
		
		if show_channel_guide_pane == False:
			self.channel_guide_pane.hide()

		self.eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
		
		self.ui_worker = UpdateUIThread(self, channel_timeout)
		self.ui_worker.start()		
		
		self.populate_bookmarks()
		
		chinese = self.channel_guide_language == _("Chinese")
		self.populate_channel_treeview(chinese)
		
		self.show_channel_guide.set_active(show_channel_guide_pane)
		self.show_channel_guide.connect("toggled", self.on_show_channel_guide_toggled)
		
		if sop_address != None:
			if sop_address[:len("sop://".lower())] == "sop://".lower():
				self.play_channel(sop_address, sop_address_name)
		
		if self.channel_url != None:
			self.play_channel()
		
		self.window.show()
		
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
	
	def media_player_size(self, screen, width_ratio, player_ratio):
		width = int(screen.get_width() * width_ratio)
		height = int(width * player_ratio)
		return (width, height)
	
	def get_server(self):
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		return config_manager.get("player", "server")
	
	def get_ports(self):
		inbound_port = None
		outbound_port = None
		exit = False
		
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		if config_manager.getboolean("player", "static_ports") == True:
			inbound_port = config_manager.getint("player", "inbound_port")
			outbound_port = config_manager.getint("player", "outbound_port")
			self.static_ports = True
			s = pySocket.pySocket()
			if not s.is_available(self.server, inbound_port) or not s.is_available(self.server, outbound_port):

				dialog = gtk.Dialog(_("Static Ports Unavailable"),
					self.window,
					gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
					(gtk.STOCK_NO, gtk.RESPONSE_REJECT,
					gtk.STOCK_YES, gtk.RESPONSE_ACCEPT))
				
				#dialog.set_has_separator(False)
			
				hbox = gtk.HBox()
		
			
				label = gtk.Label(_("Static ports unavailable, do you wish to continue using dynamic ports?"))
				hbox.pack_start(label)
				hbox.set_size_request(-1, 50)
				hbox.show_all()
				dialog.set_default_response(gtk.RESPONSE_ACCEPT)
				dialog.vbox.pack_start(hbox)
		
				if dialog.run() == gtk.RESPONSE_REJECT:
					exit = True
					
			
				dialog.destroy()



				dyn = dynamic_ports.DynamicPorts()
				inbound_port, outbound_port = dyn.get_ports()
				self.static_ports = False
		else:
			dyn = dynamic_ports.DynamicPorts()
			inbound_port, outbound_port = dyn.get_ports()
		
		if exit == True:
			inbound_port = None
			outbound_port = None
			
		return inbound_port, outbound_port
		
	def populate_bookmarks(self):
		self.clear_bookmarks()
		for bookmark in self.db_operations.retrieve_bookmarks():
			menu_item = gtk.MenuItem(bookmark[1])
			menu_item.connect("activate", self.on_menu_bookmark_channel_activate, bookmark)
			self.menu_bookmarks.get_submenu().append(menu_item)
			self.menu_bookmarks.get_submenu().show_all()
	
	def populate_channel_treeview(self, chinese=False):
		self.channel_treeview.set_model()
		self.channel_treeview_model.clear()
		if chinese == False:
			channel_groups = self.db_operations.retrieve_channel_groups()
		else:
			channel_groups = self.db_operations.retrieve_channel_groups_cn()
		
		for channel_group in channel_groups:
			channel_group_iter = self.channel_treeview_model.append(None, self.prepare_row_for_channel_treeview_model(channel_group))
			
			if chinese == False:
				channels = self.db_operations.retrieve_channels_by_channel_group_id(channel_group[0])
			else:
				channels = self.db_operations.retrieve_channels_by_channel_group_id_cn(channel_group[0])
		
			for channel in channels:
				self.channel_treeview_model.append(channel_group_iter, self.prepare_row_for_channel_treeview_model(channel))
		
		self.channel_treeview.set_model(self.channel_treeview_model)

	def set_media_player_visible(self, visible):
		if visible == True:
			self.menu_view.show()
			self.media_box.show()
			self.channel_properties_pane.hide()
		else:
			self.menu_view.hide()
			self.media_box.hide()
			self.channel_properties_pane.show()
			
			if self.show_channel_guide.get_active() == False:
				self.show_channel_guide.set_active(True)
	
	def prepare_row_for_channel_treeview_model(self, row):
		if len(row) == 10:
			return row
		else:
			return [row[0], row[1], row[2], None, None, None, 0, 0, 0, None]
			
	def clear_bookmarks(self):
		menu_items = self.menu_bookmarks.get_submenu().get_children()
		
		if len(menu_items) > 2:
			i = 2
			while i < len(menu_items):
				self.menu_bookmarks.get_submenu().remove(menu_items[i])
				i += 1
	
	def on_menu_quit_activate(self, src, data=None):
		self.window.destroy()
		
	def on_menu_bookmark_channel_activate(self, src, channel_info):
		self.play_channel(channel_info[2])
		
	def on_add_bookmark(self, src, data=None):
		add_bookmark_dialog = AddBookmark(self)			
		add_bookmark_dialog.main()
		
	def on_stop_clicked(self, src, data=None):
		self.stop_vlc()
		
		self.ui_worker.shutdown()
		if self.fork_sop.is_running() == True:
			self.fork_sop.kill_sop()
		
		self.update_statusbar("")
		self.window.set_title(self.window_title)
		
	def on_volume_adjust_bounds(self, src, data=None):
		self.player_volume = int(src.get_value())
		self.vlc.set_volume(self.player_volume)
	
	def on_menu_about_activate(self, src, data=None):
		#gladefile = "%s/%s" % ("/usr/share/sopcast-player/ui", "About.glade")
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "ui/About.glade")
		about_file = gtk.glade.XML(gladefile, "about")
		about = about_file.get_widget("about")
		about.set_transient_for(self.window)
		about.run()
		about.destroy()
	
	def on_open_sop_address_activate(self, src, data=None):
		dialog = gtk.Dialog(_("Open Sop Address"),
			self.window,
			gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
			(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
			gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
			
		hbox = gtk.HBox()
		
			
		label = gtk.Label("%s %s" % (_("Enter Sop Address"), ": "))
		entry = gtk.Entry()
		hbox.pack_start(label)
		hbox.pack_start(entry)
		hbox.set_size_request(-1, 50)
		hbox.show_all()
		dialog.set_default_response(gtk.RESPONSE_ACCEPT)
		dialog.vbox.pack_start(hbox)
		
		if dialog.run() == gtk.RESPONSE_ACCEPT:
			if len(entry.get_text()) > 0:
				self.play_channel(entry.get_text())
			
		dialog.destroy()
	
	def on_show_channel_guide_toggled(self, src, data=None):
		window_width = self.window.get_size()[0]
		window_height = self.window.get_size()[1]
		handle_width = self.display_pane.style_get_property("handle-size")
		
		if src.get_active() == True:
			config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
			config_manager.read()
			self.window.resize(window_width + config_manager.getint("player", "channel_guide_width"), window_height)
			self.channel_guide_pane.show()
			
		else:
			pane2_width = self.display_pane.get_child2().get_allocation()[2]
			config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
			config_manager.read()
			config_manager.set("player", "channel_guide_width", pane2_width + handle_width)
			config_manager.write()
			
			self.channel_guide_pane.hide()
			self.window.resize(self.display_pane.get_child1().get_allocation()[2], window_height)
	
	def on_channel_treeview_row_activated(self, treeview, path, view_column, data=None):
		if self.channel_treeview_model.iter_has_child(self.selected_iter) == True:
			if self.channel_treeview.row_expanded(self.channel_treeview_model.get_path(self.selected_iter)) == False:
				self.channel_treeview.expand_row(self.channel_treeview_model.get_path(self.selected_iter), False)
			else:
				self.channel_treeview.collapse_row(self.channel_treeview_model.get_path(self.selected_iter))
		else:
			self.play_channel(self.selection[9], self.selection[1])
			
	def set_label_group(self, label_group, labels=None):
		i = 0
		if labels != None:
			while i < len(label_group):
				label_group[i].set_label(labels[i])
				i += 1
		else:
			while i < len(label_group):
				label_group[i].set_label("")
				i += 1

	def on_selection_changed(self, src, data=None):
		model, s_iter = src.get_selected()

		if s_iter:
			row = model.get_path(s_iter)
			self.selected_iter = s_iter
			self.selection = self.channel_treeview_model[row]
	
			if self.channel_treeview_model.iter_has_child(self.selected_iter) == False:
				label_group = [self.label_name, self.label_channel_group, self.label_classification, self.label_stream_type, self.label_bitrate, self.label_qc, self.label_qs, self.label_description]
				labels = ["%s: %s" % (_("Name"), self.html_escape(self.selection[1])), "%s: %s" % (_("Channel Group"), self.html_escape(self.channel_treeview_model[self.channel_treeview_model.get_path(self.channel_treeview_model.iter_parent(s_iter))][1])), "%s: %s" % (_("Classification"), self.html_escape(self.selection[4])), "%s: %s" % (_("Stream Format"), self.html_escape(self.selection[5].upper())), "Bitrate: %d kb/s" % self.selection[6], "%s: %d" % (_("QC"), self.selection[7]), "%s: %d" % (_("QS"), self.selection[8]), "%s: %s" % (_("Description"), self.html_escape(self.selection[2]))]
				self.set_label_group(label_group, labels)
		
			else:
				label_group = [self.label_name, self.label_channel_group, self.label_classification, self.label_stream_type, self.label_bitrate, self.label_qc, self.label_qs, self.label_description]
				labels = ["%s: %s" % (_("Name"), self.html_escape(self.selection[1])), "%s: %d" % (_("Channels"), self.get_iter_child_count(self.selected_iter)), "%s: %s" % (_("Description"), self.html_escape(self.selection[2])), "" ,"" ,"" ,"" ,""]
				self.set_label_group(label_group, labels)
		else:
			self.selected_iter = None
			self.selection = None
			label_group = [self.label_name, self.label_channel_group, self.label_classification, self.label_stream_type, self.label_bitrate, self.label_qc, self.label_qs, self.label_description]
			self.set_label_group(label_group)
	
	def on_refresh_channel_guide_clicked(self, src, data=None):
		self.update_channel_guide_progress.set_fraction(0)
		self.channel_guide_label.hide()
		self.update_channel_guide_progress.show()
	
		if self.channel_guide_worker != None:
			if self.channel_guide_worker.running == False:
				self.channel_guide_worker = None
			
				self.channel_guide_worker = UpdateChannelGuideThread(self)
				self.channel_guide_worker.start()
		else:
			self.channel_guide_worker = UpdateChannelGuideThread(self)
			self.channel_guide_worker.start()
	
	def on_menu_screenshot_activate(self, src, data=None):
		screenshot = self.vlc.screenshot()
		print screenshot
	
	def on_menu_preferences_activate(self, src, data=None):
		channel_timeout_display = { 0: _("<i>3 Seconds</i>"),
			    1: _("<i>30 Seconds</i>"),
			    2: _("<i>5 Minutes</i>"),
			    3: _("<i>Never</i>") }
			
		channel_timeout_value = { 0: 3,
				 1: 30,
				 2: 300,
				 3: sys.maxint }
		
		channel_timeout_inverse = { 3: 0,
					    30: 1,
					    300: 2,
					    sys.maxint: 3 }		 
				 
		#gladefile = "%s/%s" % ("/usr/share/sopcast-player/ui", "Options.glade")
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "ui/Options.glade")
		tree = gtk.glade.XML(gladefile, "window")
		
		dialog = tree.get_widget("window")
		dialog.set_transient_for(self.window)
		
				
		# Default retrieval
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		static_ports_default = config_manager.getboolean("player", "static_ports")
		inbound_port_default = config_manager.getint("player", "inbound_port")
		outbound_port_default = config_manager.getint("player", "outbound_port")
		
		external_player_default = config_manager.getboolean("player", "external_player")
		external_player_command_default = config_manager.get("player", "external_player_command")
		
		channel_timeout_default = config_manager.getint("player", "channel_timeout")
		
		channel_guide_url_default = config_manager.get("ChannelGuide", "url")
		language_combobox_default = config_manager.get("ChannelGuide", "channel_guide_language")
		

		# Widget variables
		static_ports = tree.get_widget("static_ports")
		inbound_port = tree.get_widget("inbound_port")
		outbound_port = tree.get_widget("outbound_port")
		static_ports_children = ( inbound_port, outbound_port )
		
		external_player = tree.get_widget("external_player")
		external_player_command = tree.get_widget("external_player_command")
		
		channel_timeout_label = tree.get_widget("channel_timeout_label")
		channel_timeout = tree.get_widget("channel_timeout")
		
		channel_guide_url = tree.get_widget("channel_guide_url")
		
		language_combobox = tree.get_widget("language_combobox")
		
		
		# Signal functions and helpers
		def set_widgets_sensitive(widgets, sensitive):
			for widget in widgets:
				widget.set_sensitive(sensitive)
		
		def on_static_ports_toggled(src, data=None):
			set_widgets_sensitive(static_ports_children, src.get_active())
			config_manager.set("player", "static_ports", src.get_active())
			config_manager.write()
			self.static_ports = src.get_active()
			
			if self.static_ports == False:
				self.inbound_port = None
				self.outbound_port = None
			else:
				self.inbound_port = int(inbound_port.get_value())
				self.outbound_port = int(outbound_port.get_value())
		
		def on_inbound_port_value_changed(src, data=None):
			if src.get_value() == outbound_port.get_value():
				src.set_value(src.get_value() + 1)
			else:
				config_manager.set("player", "inbound_port", int(src.get_value()))
				config_manager.write()
				self.inbound_port = int(src.get_value())
			
		def on_outbound_port_value_changed(src, data=None):
			if src.get_value() == inbound_port.get_value():
				src.set_value(src.get_value() + 1)
			else:
				config_manager.set("player", "outbound_port", int(src.get_value()))
				config_manager.write()
				self.outbound_port = int(src.get_value())
		
		def on_external_player_toggled(src, data=None):
			external_player_command.set_sensitive(src.get_active())
			config_manager.set("player", "external_player", src.get_active())
			config_manager.write()
			
			if src.get_active() == True:
				self.external_player_command = external_player_command.get_text()
				self.set_media_player_visible(False)
			else:
				self.external_player_command = None
				self.set_media_player_visible(True)
			#TODO: Mashup the player window to only show channel guide and set ui_worker to launch external command
		
		def on_external_player_command_focus_out_event(src, event, data=None):
			if external_player_command.get_text() != external_player_command_default:
				config_manager.set("player", "external_player_command", src.get_text())
				config_manager.write()
				
				self.external_player_command = external_player_command.get_text()
				#TODO: Mashup the player window to only show channel guide and set ui_worker to launch external command
				
		def on_channel_timeout_adjust_bounds(src, value, data=None):					 
			if int(math.floor(value)) > (len(channel_timeout_display) - 1):
				channel_timeout_label.set_markup(channel_timeout_display[len(channel_timeout_display) - 1])
			elif int(math.floor(value)) < 0:
				channel_timeout_label.set_markup(channel_timeout_display[0])
			else:
				channel_timeout_label.set_markup(channel_timeout_display[int(math.floor(value))])
		
		def on_channel_timeout_focus_out_event(src, event, data=None):
			if channel_timeout.get_value() != channel_timeout_default:
				config_manager.set("player", "channel_timeout", channel_timeout_value[int(channel_timeout.get_value())])
				config_manager.write()
				self.ui_worker.set_channel_timeout(channel_timeout_value[int(channel_timeout.get_value())])
		
		def on_channel_guide_url_focus_out_event(src, event, data=None):
			if src.get_text() != channel_guide_url_default:
				config_manager.set("ChannelGuide", "url", src.get_text())
				config_manager.write()
				self.channel_guide_url = src.get_text()
		
		def on_language_combobox_changed(src, data=None):
			chinese = False
			config_manager.set("ChannelGuide", "channel_guide_language", src.get_active_text())
			config_manager.write()
			
			if src.get_active_text() == _("Chinese"):
				chinese = True
			
			print chinese
			
			self.populate_channel_treeview(chinese)
			self.channel_guide_language = src.get_active_text()
		
		
		# Setup widget defaults
		static_ports.set_active(static_ports_default)
		set_widgets_sensitive(static_ports_children, static_ports_default)
		inbound_port.set_value(inbound_port_default)
		outbound_port.set_value(outbound_port_default)
		
		external_player.set_active(external_player_default)
		external_player_command.set_text(external_player_command_default)
		external_player_command.set_sensitive(external_player_default)
		
		channel_timeout.set_value(channel_timeout_inverse[channel_timeout_default])
		channel_timeout_label.set_markup(channel_timeout_display[channel_timeout_inverse[channel_timeout_default]])
		
		channel_guide_url.set_text(channel_guide_url_default)
		
		if is_chinese() == False:
			language_combobox.insert_text(0, _("English"))
			language_combobox.insert_text(1, _("Chinese"))
		else:
			language_combobox.insert_text(0, _("Chinese"))				
			language_combobox.insert_text(1, _("English"))
		
		if is_chinese() == False:
			if language_combobox_default == _("English"):
				language_combobox.set_active(0)
			else:
				language_combobox.set_active(1)
		else:
			if language_combobox_default == _("Chinese"):
				language_combobox.set_active(0)
			else:
				language_combobox.set_active(1)

		# Signal connect
		dic = { "on_static_ports_toggled" : on_static_ports_toggled,
			"on_inbound_port_value_changed" : on_inbound_port_value_changed,
			"on_outbound_port_value_changed" : on_outbound_port_value_changed,
			"on_external_player_toggled" : on_external_player_toggled,
			"on_external_player_command_focus_out_event" : on_external_player_command_focus_out_event,
			"on_channel_timeout_adjust_bounds" : on_channel_timeout_adjust_bounds,
			"on_channel_timeout_focus_out_event" : on_channel_timeout_focus_out_event,
			"on_channel_guide_url_focus_out_event" : on_channel_guide_url_focus_out_event,
			"on_language_combobox_changed" : on_language_combobox_changed}
		tree.signal_autoconnect(dic)
		
		dialog.run()
		
		
		# Post-response action area
		dialog.destroy()
	
	def on_menu_stay_on_top_toggled(self, src, data=None):
		self.window.set_keep_above(src.get_active())
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		config_manager.set("player", "stay_on_top", src.get_active())
		config_manager.write()
	
	def on_menu_show_controls_toggled(self, src, data=None):
		return True
		
	def show_menu_controls(self, show):
		self.show_controls = show
		window_height = self.window.get_size()[1]
		window_width = self.window.get_size()[0]
				
		if show == True:
			self.window.resize(window_width, window_height + self.hide_controls_size)
			self.menu_show_controls.set_active(show)
			self.main_menu.show()
			self.media_controls.show()
			self.status_bar.show()
		else:
			if self.hide_controls_size == None:
				self.hide_controls_size = self.main_menu.get_allocation()[3] + self.media_controls.get_allocation()[3] + self.status_bar.get_allocation()[3]
			
			if self.show_channel_guide.get_active() == True:
				self.show_channel_guide.set_active(False)
				self.channel_guide_pane.hide()
				window_width = self.display_pane.get_child1().get_allocation()[2]
			
			self.main_menu.hide()
			self.media_controls.hide()
			self.status_bar.hide()
			
			self.window.resize(window_width, window_height - self.hide_controls_size)
			
	def on_window_key_press_event(self, src, event, data=None):
		if event.state & gtk.gdk.CONTROL_MASK:
			if gtk.gdk.keyval_name(event.keyval) in ["h", "H"]:
				self.show_menu_controls(not self.show_controls)
			elif gtk.gdk.keyval_name(event.keyval) in ["t", "T"]:
				self.menu_stay_on_top.set_active(not self.menu_stay_on_top.get_active())
			elif gtk.gdk.keyval_name(event.keyval) in ["q", "Q"]:
				self.menu_quit.activate()
			elif gtk.gdk.keyval_name(event.keyval) in ["o", "O"]:
				self.open_sop_address.activate()
			elif gtk.gdk.keyval_name(event.keyval) in ["d", "D"]:
				self.menu_add_bookmark.activate()
			elif gtk.gdk.keyval_name(event.keyval) in ["f", "F"]:
				self.menu_fullscreen.activate()
		else:
			if gtk.gdk.keyval_name(event.keyval) in ["h", "H"]:
				self.show_menu_controls(not self.show_controls)
			elif gtk.gdk.keyval_name(event.keyval) in ["t", "T"]:
				self.menu_stay_on_top.set_active(not self.menu_stay_on_top.get_active())
			elif gtk.gdk.keyval_name(event.keyval) in ["f", "F"]:
				self.menu_fullscreen.activate()
	
	def on_channel_treeview_button_press_event(self, src, event, data=None):
		if event.button == 3:
			x = int(event.x)
			y = int(event.y)
			time = event.time
			pthinfo = self.channel_treeview.get_path_at_pos(x, y)
			if pthinfo is not None:
				path, col, cellx, celly = pthinfo
				self.channel_treeview.grab_focus()
				self.channel_treeview.set_cursor( path, col, 0 )
				if self.channel_treeview_model.iter_has_child(self.channel_treeview_model.get_iter(path)) == False:
					self.context_menu.popup( None, None, None, event.button, time)
		return False
	
	def on_context_menu_play_activate(self, src, data=None):
		path, column = self.channel_treeview.get_cursor()
		
		self.play_channel(self.channel_treeview_model[path][9], self.channel_treeview_model[path][1])
		print self.channel_treeview_model[path][2]

	def get_iter_child_count(self, parent_iter):
		i = 0
		
		child = self.channel_treeview_model.iter_children(parent_iter)
		
		while child != None:
			child = self.channel_treeview_model.iter_next(child)
			i += 1
		
		return i
		
	def update_status_bar_text(self, txt):
		if self.status_bar != None:
			self.status_bar_text = txt
			self.status_bar_text_changed = True
	
	def set_volume(self, volume):
		self.vlc.set_volume(volume)
		
	def start_vlc(self):
		if self.vlc.get_parent() == None:
			self.eb.add(self.vlc)
			self.eb.show_all()
			return False
		
		if self.vlc.get_parent() == self.eb:
			self.vlc.play_media()
			self.vlc.set_volume(self.player_volume)
			return True
		else:
			return False
			
	def stop_vlc(self):
		self.vlc.stop_media()
		if self.vlc.get_parent() == self.eb:
			self.eb.remove(self.vlc)
			if self.window != None:
				self.eb.show_all()
		
	def play_channel(self, channel_url=None, title=None):
		if self.fork_sop.is_running() == True:
			self.fork_sop.kill_sop()
		
		s = pySocket.pySocket()
		if (self.inbound_port == None or self.outbound_port == None) or (not s.is_available(self.server, self.inbound_port) or not s.is_available(self.server, self.outbound_port)):
			self.inbound_port, self.outbound_port = self.get_ports()
			
		if self.inbound_port == None or self.outbound_port == None:
			self.window.destroy()
		else:
			self.sop_stats = listen.SOPStats(self.server, self.outbound_port)
		
			print "%s: %s" % ("Inbound Port", self.inbound_port)
			print "%s: %s" % ("Outbound Port", self.outbound_port)
			
			if channel_url != None:
				self.channel_url = channel_url
				if title == None:
					self.window.set_title("%s - %s" % (channel_url, self.window_title))
			
			if title != None:
				self.window.set_title("%s - %s" % (title, self.window_title))
			else:
				records = self.db_operations.retrieve_bookmark_by_address(self.channel_url)
				if len(records) > 0:
					self.window.set_title("%s - %s" % (records[0][0], self.window_title))
				else:
					records = self.db_operations.retrieve_channel_guide_record_by_address(self.channel_url)
					if len(records) > 0:
						self.window.set_title("%s - %s" % (records[0][0], self.window_title))
			
			self.fork_sop.fork_sop(self.channel_url, str(self.inbound_port), str(self.outbound_port))
		
			self.menu_add_bookmark.set_sensitive(True)
			self.menu_fullscreen.set_sensitive(True)
		
			self.outbound_media_url = "http://%s:%d/tv.asf" % (self.server, self.outbound_port)
			self.vlc.set_media_url(self.outbound_media_url)
			self.ui_worker.startup()

	def on_play_button_clicked(self, src, data=None):
		if self.channel_url != None:
			self.play_channel(self.channel_url)
		
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
			self.vlc.display_text("         %s" % "Press Esc to exit fullscreen")
			
	def on_exit(self, widget, data=None):
		rect = self.window.get_allocation()
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		config_manager.set("player", "width", rect[2])
		
		if self.show_controls == True:
			config_manager.set("player", "height", rect[3])
		else:
			config_manager.set("player", "height", rect[3] + self.hide_controls_size)
		
		if self.channel_selection_pane.get_property("visible") == True and self.media_box.get_property("visible") == True:	
			config_manager.set("player", "div_position", self.display_pane.get_position())
		
		if self.channel_properties_pane.get_property("visible") == True and self.media_box.get_property("visible") == False:
			config_manager.set("ChannelGuide", "div_position", self.channel_guide_hpane.get_position())
		config_manager.set("player", "show_channel_guide", self.show_channel_guide.get_active())
		config_manager.set("player", "volume", int(self.volume.get_value()))
		config_manager.write()
		
		self.ui_worker.stop()
		
		if self.fork_sop.is_running() == True:
			self.vlc.stop_media()
			self.vlc.exit_media()
			self.fork_sop.kill_sop()
			
		gtk.main_quit()
		self = None

	def on_eb_key_press_event(self, widget, event, data=None):
		key = event.keyval
		
		if self.eb.is_focus() == True:
			if key == 70 or key == 102:
				self.vlc.fullscreen()
				self.vlc.display_text("         %s" % "Press Esc to exit fullscreen")
		
		return False
	
	def add_bookmark(self, channel_name, url=None):
		if url == None:
			url = self.channel_url
		
		self.db_operations.insert_bookmark(channel_name, url)
		self.populate_bookmarks()
		
		if url == self.channel_url:
			self.window.set_title("%s - %s" % (channel_name, self.window_title))
	
	def update_statusbar(self, text, display_time=None):
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
		
	def html_escape(self, text):
		html_escape_table = {
			"&": "&amp;",
			'"': "&quot;",
			"'": "&apos;",
			">": "&gt;",
			"<": "&lt;",
			}
		"""Produce entities within text."""
		L=[]
		for c in text:
			L.append(html_escape_table.get(c,c))
		return "".join(L)

class ChannelGuide2(object):
	def __init__(self, parent=None):
		gtk.gdk.threads_init()
		self.last_update = 0
		self.status_bar_text = None
		self.status_bar_text_changed = False
		self.db_operations = DatabaseOperations.DatabaseOperations()
		self.display_message_from_main_thread = False
		self.start_display_time = None
		self.display_message_time = 5
		self.treeview_selection = None
		self.channel_guide_worker = None
		self.channel_guide_language = None
		self.parent = parent
		
	def main(self, sop_address=None, sop_address_name=None):
		#gladefile = "%s/%s" % ("/usr/share/sopcast-player/ui", "ChannelGuide2.glade")
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "ui/ChannelGuide2.glade")
		self.glade_window = gtk.glade.XML(gladefile, "window", "sopcast-player")
		self.window = self.glade_window.get_widget("window")
		
		window_signals = { "on_mainWindow_destroy" : self.on_exit,
			"on_menu_quit_activate" : self.on_menu_quit_activate,
			"on_menu_about_activate" : self.on_menu_about_activate,
			"on_refresh_channel_guide_clicked" : self.on_refresh_channel_guide_clicked }
		
		self.glade_window.signal_autoconnect(window_signals)

		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		
		self.window.set_default_size(config_manager.getint("ChannelGuide", "width"), config_manager.getint("ChannelGuide", "height"))
		self.channel_guide_url = config_manager.get("ChannelGuide", "url")
		self.channel_guide_hpane.set_position(config_manager.getint("ChannelGuide", "div_position"))		
		self.channel_guide_language = config_manager.get("ChannelGuide", "channel_guide_language")

		textrenderer = gtk.CellRendererText()
		
		column = gtk.TreeViewColumn("Name", textrenderer, text=1)
		self.channel_treeview.append_column(column)
		
		self.channel_treeview_model = gtk.TreeStore(int, str, str, str, str, str, int, int, int, str)
		self.treeview_selection = self.channel_treeview.get_selection()
		self.treeview_selection_changed_handler = self.treeview_selection.connect("changed", self.on_selection_changed)
		self.channel_treeview.connect("row_activated", self.on_channel_treeview_row_activated)
		
		chinese = self.channel_guide_language == _("Chinese")
		self.populate_channel_treeview(chinese)
		
		self.window.show()
		
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
	
	def populate_channel_treeview(self, chinese=False):
		self.channel_treeview.set_model()
		self.channel_treeview_model.clear()
		if chinese == False:
			channel_groups = self.db_operations.retrieve_channel_groups()
		else:
			channel_groups = self.db_operations.retrieve_channel_groups_cn()
		
		for channel_group in channel_groups:
			channel_group_iter = self.channel_treeview_model.append(None, self.prepare_row_for_channel_treeview_model(channel_group))
			
			if chinese == False:
				channels = self.db_operations.retrieve_channels_by_channel_group_id(channel_group[0])
			else:
				channels = self.db_operations.retrieve_channels_by_channel_group_id_cn(channel_group[0])
		
			for channel in channels:
				self.channel_treeview_model.append(channel_group_iter, self.prepare_row_for_channel_treeview_model(channel))
		
		self.channel_treeview.set_model(self.channel_treeview_model)
	
	def prepare_row_for_channel_treeview_model(self, row):
		if len(row) == 10:
			return row
		else:
			return [row[0], row[1], row[2], None, None, None, 0, 0, 0, None]
	
	def on_menu_quit_activate(self, src, data=None):
		self.window.destroy()
	
	def on_menu_about_activate(self, src, data=None):
		#gladefile = "%s/%s" % ("/usr/share/sopcast-player/ui", "About.glade")
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "ui/About.glade")
		about_file = gtk.glade.XML(gladefile, "about")
		about = about_file.get_widget("about")
		about.set_transient_for(self.window)
		about.run()
		about.destroy()
	
	def on_channel_treeview_row_activated(self, treeview, path, view_column, data=None):
		if self.channel_treeview_model.iter_has_child(self.selected_iter) == True:
			if self.channel_treeview.row_expanded(self.channel_treeview_model.get_path(self.selected_iter)) == False:
				self.channel_treeview.expand_row(self.channel_treeview_model.get_path(self.selected_iter), False)
			else:
				self.channel_treeview.collapse_row(self.channel_treeview_model.get_path(self.selected_iter))
		else:
			if self.parent != None:
				if self.parent.eb == None:
					self.parent = pySopCast()
					self.parent.main(self.selection[9], self.selection[1])
				else:
					self.parent.play_channel(self.selection[9], self.selection[1])
			else:
				self.parent = pySopCast()
				self.parent.main(self.selection[9], self.selection[1])
			
	def set_label_group(self, label_group, labels=None):
		i = 0
		if labels != None:
			while i < len(label_group):
				label_group[i].set_label(labels[i])
				i += 1
		else:
			while i < len(label_group):
				label_group[i].set_label("")
				i += 1

	def on_selection_changed(self, src, data=None):
		model, s_iter = src.get_selected()

		if s_iter:
			row = model.get_path(s_iter)
			self.selected_iter = s_iter
			self.selection = self.channel_treeview_model[row]
	
			if self.channel_treeview_model.iter_has_child(self.selected_iter) == False:
				label_group = [self.label_name, self.label_channel_group, self.label_classification, self.label_stream_type, self.label_bitrate, self.label_qc, self.label_qs, self.label_description]
				labels = ["%s: %s" % (_("Name"), self.html_escape(self.selection[1])), "%s: %s" % (_("Channel Group"), self.html_escape(self.channel_treeview_model[self.channel_treeview_model.get_path(self.channel_treeview_model.iter_parent(s_iter))][1])), "%s: %s" % (_("Classification"), self.html_escape(self.selection[4])), "%s: %s" % (_("Stream Format"), self.html_escape(self.selection[5].upper())), "Bitrate: %d kb/s" % self.selection[6], "%s: %d" % (_("QC"), self.selection[7]), "%s: %d" % (_("QS"), self.selection[8]), "%s: %s" % (_("Description"), self.html_escape(self.selection[2]))]
				self.set_label_group(label_group, labels)
		
			else:
				label_group = [self.label_name, self.label_channel_group, self.label_classification, self.label_stream_type, self.label_bitrate, self.label_qc, self.label_qs, self.label_description]
				labels = ["%s: %s" % (_("Name"), self.html_escape(self.selection[1])), "%s: %d" % (_("Channels"), self.get_iter_child_count(self.selected_iter)), "%s: %s" % (_("Description"), self.html_escape(self.selection[2])), "" ,"" ,"" ,"" ,""]
				self.set_label_group(label_group, labels)
		else:
			self.selected_iter = None
			self.selection = None
			label_group = [self.label_name, self.label_channel_group, self.label_classification, self.label_stream_type, self.label_bitrate, self.label_qc, self.label_qs, self.label_description]
			self.set_label_group(label_group)
	
	def on_refresh_channel_guide_clicked(self, src, data=None):
		self.update_channel_guide_progress.set_fraction(0)
		self.channel_guide_label.hide()
		self.update_channel_guide_progress.show()
	
		if self.channel_guide_worker != None:
			if self.channel_guide_worker.running == False:
				self.channel_guide_worker = None
			
				self.channel_guide_worker = UpdateChannelGuideThread(self)
				self.channel_guide_worker.start()
		else:
			self.channel_guide_worker = UpdateChannelGuideThread(self)
			self.channel_guide_worker.start()
	
	def get_iter_child_count(self, parent_iter):
		i = 0
		
		child = self.channel_treeview_model.iter_children(parent_iter)
		
		while child != None:
			child = self.channel_treeview_model.iter_next(child)
			i += 1
		
		return i
		
	def update_status_bar_text(self, txt):
		if self.status_bar != None:
			self.status_bar_text = txt
			self.status_bar_text_changed = True
	
	def set_volume(self, volume):
		self.vlc.set_volume(volume)
			
	def on_exit(self, widget, data=None):
		rect = self.window.get_allocation()
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		config_manager.set("ChannelGuide", "width", rect[2])
		
		config_manager.set("ChannelGuide", "height", rect[3])
		
		config_manager.set("ChannelGuide", "div_position", self.channel_guide_hpane.get_position())
		config_manager.write()
			
		gtk.main_quit()
		self = None
	
	def update_statusbar(self, text, display_time=None):
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
		
	def html_escape(self, text):
		html_escape_table = {
			"&": "&amp;",
			'"': "&quot;",
			"'": "&apos;",
			">": "&gt;",
			"<": "&lt;",
			}
		"""Produce entities within text."""
		L=[]
		for c in text:
			L.append(html_escape_table.get(c,c))
		return "".join(L)
		
class UpdateChannelGuideUIThread(threading.Thread):
	def __init__ (self, parent):
		threading.Thread.__init__(self)
		self.parent = parent
		self.downloader = FileDownload.FileDownload()
		self.guide_import = ImportChannelGuide.ImportChannelGuide()
		self.daemon = True
		self.running = True
		
	def run(self):
		self.running = True
		chinese = False
		handler_blocked = False
		
		downloader = FileDownload.FileDownload()
		guide_import = ImportChannelGuide.ImportChannelGuide()
		
		gtk.gdk.threads_enter()
		self.parent.update_statusbar("%s" % (_("Contacting Server")), True)
		gtk.gdk.threads_leave()
		
		try:
			db_operations = DatabaseOperations.DatabaseOperations()
			downloader.download_file('http://www.sopcast.com/gchlxml', os.path.expanduser('~/.pySopCast/channel_guide.xml'), self.report_progress)
			
			gtk.gdk.threads_enter()
			self.parent.update_statusbar("%s" % (_("Updating Database")), True)
			gtk.gdk.threads_leave()
			
			guide_import.update_database(os.path.expanduser('~/.pySopCast/channel_guide.xml'))
			
			gtk.gdk.threads_enter()
			self.parent.treeview_selection.handler_block(self.parent.treeview_selection_changed_handler)
			gtk.gdk.threads_leave()
			
			handler_blocked = True
			
			gtk.gdk.threads_enter()
			self.parent.channel_treeview.set_model()
			gtk.gdk.threads_leave()
			
			gtk.gdk.threads_enter()
			self.parent.channel_treeview.get_selection().unselect_all()
			gtk.gdk.threads_leave()
			
			gtk.gdk.threads_enter()
			self.parent.channel_treeview_model.clear()
			gtk.gdk.threads_leave()
			
			if chinese == False:
				channel_groups = db_operations.retrieve_channel_groups()
			else:
				channel_groups = db_operations.retrieve_channel_groups_cn()
		
			for channel_group in channel_groups:
				gtk.gdk.threads_enter()
				channel_group_iter = self.parent.channel_treeview_model.append(None, self.parent.prepare_row_for_channel_treeview_model(channel_group))
				gtk.gdk.threads_leave()
				
				if chinese == False:
					channels = db_operations.retrieve_channels_by_channel_group_id(channel_group[0])
				else:
					channels = db_operations.retrieve_channels_by_channel_group_id_cn(channel_group[0])
		
				for channel in channels:
					gtk.gdk.threads_enter()
					self.parent.channel_treeview_model.append(channel_group_iter, self.parent.prepare_row_for_channel_treeview_model(channel))
					gtk.gdk.threads_leave()
			
			gtk.gdk.threads_enter()
			self.parent.channel_treeview.set_model(self.parent.channel_treeview_model)
			gtk.gdk.threads_leave()
			
			gtk.gdk.threads_enter()
			self.parent.update_statusbar("%s" % (_("Channel Guide Update Completed")), True)
			gtk.gdk.threads_leave()
			
			config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
			config_manager.set("ChannelGuide", "last_updated", time.strftime(locale.nl_langinfo(locale.D_T_FMT)))
			config_manager.write()
		except Exception, e:
			gtk.gdk.threads_enter()
			self.parent.update_statusbar("%s" % (_("Channel Guide Retrieval Failed Due to Network Problems")), True)
			gtk.gdk.threads_leave()
			print e
		
		if handler_blocked == True:
			gtk.gdk.threads_enter()
			self.parent.treeview_selection.handler_unblock(self.parent.treeview_selection_changed_handler)
			gtk.gdk.threads_leave()
		
		self.running = False
		
	def report_progress(self, numblocks, blocksize, filesize):
		try:
			percent = min((numblocks*blocksize*100)/filesize, 100)
		except:
			percent = 100
		
		gtk.gdk.threads_enter()
		self.parent.update_statusbar("%s: %d%%" % (_("Downloading Channel Guide"), percent), True)
		gtk.gdk.threads_leave()
	
class ChannelGuide(object):
	def __init__(self, parent=None):
		gtk.gdk.threads_init()
		self.window = None
		self.parent = parent
		self.ui_worker = None
		self.worker_running = False
		self.selected_iter = None
		self.selection = None
		self.add_bookmark_dialog = AddBookmark(self)
		self.db_operations = DatabaseOperations.DatabaseOperations()
		
	def main(self):
		#gladefile = "%s/%s" % ("/usr/share/sopcast-player/ui", "ChannelGuide.glade")
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "ui/ChannelGuide.glade")
		self.glade_window = gtk.glade.XML(gladefile, "window")
		self.window = self.glade_window.get_widget("window")
		
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		width = config_manager.getint("ChannelGuide", "default_width")
		height = config_manager.getint("ChannelGuide", "default_height")
		self.window.set_default_size(width, height)
		
		dic = { "on_window_destroy" : self.on_quit,
			"on_toolbar_play_clicked" : self.on_toolbar_play_clicked,
			"on_toolbar_bookmark_clicked" : self.on_toolbar_bookmark_clicked,
			"on_toolbar_refresh_clicked" : self.on_toolbar_refresh_clicked,
			"on_menu-quit_activate" : self.on_menu_quit_activate,
			"on_window_size_allocate" : self.on_window_size_allocate,
			"on_menu-about_activate" : self.on_menu_about_activate }
		
		self.channel_panel.queue_resize()
		self.glade_window.signal_autoconnect(dic)
		
		textrenderer = gtk.CellRendererText()
		
		column = gtk.TreeViewColumn("Name", textrenderer, text=1)
		self.channel_treeview.append_column(column)
		
		#treestore is id, en_name, description, region, class, stream_type, kbps, qs, qc, sop_address
		self.channel_treeview_model = gtk.TreeStore(int, str, str, str, str, str, int, int, int, str)
		
		self.treeview_selection = self.channel_treeview.get_selection()
		self.treeview_selection_changed_handler = self.treeview_selection.connect("changed", self.on_selection_changed)
		self.channel_treeview.connect("row_activated", self.on_channel_treeview_row_activated)
		
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		last_updated = config_manager.get("ChannelGuide", "last_updated")
		
		self.update_statusbar("%s %s" % (_("Channel Guide Last Updated"), last_updated))
				
		self.populate_channel_treeview()
		
		self.window.show()
		
		gtk.gdk.threads_enter()
		gtk.main()
		gtk.gdk.threads_leave()
		
	def populate_channel_treeview(self, chinese=False):		
		if chinese == False:
			channel_groups = self.db_operations.retrieve_channel_groups()
		else:
			channel_groups = self.db_operations.retrieve_channel_groups_cn()
		
		for channel_group in channel_groups:
			channel_group_iter = self.channel_treeview_model.append(None, self.prepare_row_for_channel_treeview_model(channel_group))
			
			if chinese == False:
				channels = self.db_operations.retrieve_channels_by_channel_group_id(channel_group[0])
			else:
				channels = self.db_operations.retrieve_channels_by_channel_group_id_cn(channel_group[0])
		
			for channel in channels:
				self.channel_treeview_model.append(channel_group_iter, self.prepare_row_for_channel_treeview_model(channel))
		
		self.channel_treeview.set_model(self.channel_treeview_model)
		
	def prepare_row_for_channel_treeview_model(self, row):
		if len(row) == 10:
			return row
		else:
			return [row[0], row[1], row[2], None, None, None, 0, 0, 0, None]
		
	def on_cancel_clicked(self, src, data=None):
		self.window.destroy()
		
	def on_selection_changed(self, src, data=None):
		model, s_iter = src.get_selected()

		if s_iter:
			row = model.get_path(s_iter)
			self.selected_iter = s_iter
			self.selection = self.channel_treeview_model[row]
	
			self.update_statusbar(self.channel_treeview_model[row][1])
	
			if self.channel_treeview_model.iter_has_child(self.selected_iter) == False:
				self.toolbar_play.set_sensitive(True)
				self.toolbar_bookmark.set_sensitive(True)
				label_group = [self.label_name, self.label_channel_group, self.label_classification, self.label_stream_type, self.label_bitrate, self.label_qc, self.label_qs, self.label_description]
				labels = ["%s: %s" % (_("Name"), self.html_escape(self.selection[1])), "%s: %s" % (_("Channel Group"), self.html_escape(self.channel_treeview_model[self.channel_treeview_model.get_path(self.channel_treeview_model.iter_parent(s_iter))][1])), "%s: %s" % (_("Classification"), self.html_escape(self.selection[4])), "%s: %s" % (_("Stream Format"), self.html_escape(self.selection[5].upper())), "Bitrate: %d kb/s" % self.selection[6], "%s: %d" % (_("QC"), self.selection[7]), "%s: %d" % (_("QS"), self.selection[8]), "%s: %s" % (_("Description"), self.html_escape(self.selection[2]))]
				self.set_label_group(label_group, labels)
		
			else:
				self.toolbar_play.set_sensitive(False)
				self.toolbar_bookmark.set_sensitive(False)
				label_group = [self.label_name, self.label_channel_group, self.label_classification, self.label_stream_type, self.label_bitrate, self.label_qc, self.label_qs, self.label_description]
				labels = ["%s: %s" % (_("Name"), self.html_escape(self.selection[1])), "%s: %d" % (_("Channels"), self.get_iter_child_count(self.selected_iter)), "%s: %s" % (_("Description"), self.html_escape(self.selection[2])), "" ,"" ,"" ,"" ,""]
				self.set_label_group(label_group, labels)
		else:
			self.selected_iter = None
			self.selection = None
			label_group = [self.label_name, self.label_channel_group, self.label_classification, self.label_stream_type, self.label_bitrate, self.label_qc, self.label_qs, self.label_description]
			self.set_label_group(label_group)
						
	def on_channel_treeview_row_activated(self, treeview, path, view_column, data=None):
		if self.channel_treeview_model.iter_has_child(self.selected_iter) == True:
			if self.channel_treeview.row_expanded(self.channel_treeview_model.get_path(self.selected_iter)) == False:
				self.channel_treeview.expand_row(self.channel_treeview_model.get_path(self.selected_iter), False)
			else:
				self.channel_treeview.collapse_row(self.channel_treeview_model.get_path(self.selected_iter))
		else:
			if self.parent != None:
				if self.parent.eb == None:
					self.parent = pySopCast()
					self.parent.main(self.selection[9], self.selection[1])
				else:
					self.parent.play_channel(self.selection[9], self.selection[1])
			
	def on_toolbar_play_clicked(self, src, data=None):
			if self.parent.eb == None:
				self.parent = pySopCast()
				self.parent.main(self.selection[9], self.selection[1])
			else:
				self.parent.play_channel(self.selection[9], self.selection[1])
			
	def on_toolbar_bookmark_clicked(self, channel_name, url=None):		
		self.add_bookmark_dialog.set_title(self.selection[1])
		self.add_bookmark_dialog.set_url(self.selection[9])
			
		self.add_bookmark_dialog.main()

	def on_toolbar_refresh_clicked(self, src, data=None):
		if self.ui_worker != None:
			if self.ui_worker.running == False:
				self.ui_worker = None
			
				self.ui_worker = UpdateChannelGuideUIThread(self)
				self.ui_worker.start()
		else:
			self.ui_worker = UpdateChannelGuideUIThread(self)
			self.ui_worker.start()
	
	def on_menu_about_activate(self, src, data=None):
		#gladefile = "%s/%s" % ("/usr/share/sopcast-player/ui", "About.glade")
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "ui/About.glade")
		about_file = gtk.glade.XML(gladefile, "about")
		about = about_file.get_widget("about")
		about.set_transient_for(self.window)
		about.run()
		about.destroy()
		
	def on_quit(self, src, data=None):
		self = None
		gtk.main_quit()
		
	def on_window_size_allocate(self, src, allocation, data=None):
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		config_manager.set("ChannelGuide", "default_width", allocation.width)
		config_manager.set("ChannelGuide", "default_height", allocation.height)
		config_manager.write()
	
	def on_menu_quit_activate(self, src, data=None):
		self.window.destroy()
		
	def add_bookmark(self, channel_name, url=None):
		self.db_operations.insert_bookmark(channel_name, url)
		
		if self.parent.window != None:
			self.parent.populate_bookmarks()

		
	def set_label_group(self, label_group, labels=None):
		i = 0
		if labels != None:
			while i < len(label_group):
				label_group[i].set_label(labels[i])
				i += 1
		else:
			while i < len(label_group):
				label_group[i].set_label("")
				i += 1
				
	def update_statusbar(self, text, from_worker=False):
		update_statusbar = False
		
		if self.statusbar != None:
			if from_worker == True:
				update_statusbar = True
			else:
				if self.ui_worker == None:
					update_statusbar = True
				else:
					if self.ui_worker.running == False:
						update_statusbar = True					
				
		if update_statusbar == True:
			self.statusbar.push(1, text)
				
	def get_iter_child_count(self, parent_iter):
		i = 0
		
		child = self.channel_treeview_model.iter_children(parent_iter)
		
		while child != None:
			child = self.channel_treeview_model.iter_next(child)
			i += 1
		
		return i
				
	def html_escape(self, text):
		html_escape_table = {
			"&": "&amp;",
			'"': "&quot;",
			"'": "&apos;",
			">": "&gt;",
			"<": "&lt;",
			}
		"""Produce entities within text."""
		L=[]
		for c in text:
			L.append(html_escape_table.get(c,c))
		return "".join(L)
		
	def __getattribute__(self, key):
		value = None
		try:
			value = object.__getattribute__(self, key)
		except AttributeError:
			glade_window = object.__getattribute__(self, 'glade_window')
			value = glade_window.get_widget(key)	

		return value		

		
class AddBookmark(object):
	def __init__(self, parent, title=None, url=None):
		self.window = None
		self.parent = parent
		self.title = title
		self.url = url
		
	def main(self):
		#gladefile = "%s/%s" % ("/usr/share/sopcast-player/ui", "AddBookmark.glade")
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "ui/AddBookmark.glade")
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
		
class OpenSopAddress(object):
	def __init__(self, parent):
		self.window = None
		self.parent = parent
		
	def main(self):
		#gladefile = "%s/%s" % ("/usr/share/sopcast-player/ui", "OpenSopAddress.glade")
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "ui/OpenSopAddress.glade")
		self.glade_window = gtk.glade.XML(gladefile, "window")
		self.window = self.glade_window.get_widget("window")
		self.window.set_modal(True)
		self.window.set_transient_for(self.parent.window)
		self.window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
		
		dic = { "on_window_destroy" : gtk.main_quit,
			"on_cancel_clicked" : self.on_cancel_clicked,
			"on_done_clicked" : self.on_done_clicked }
			
		self.glade_window.signal_autoconnect(dic)
		
		gtk.main()
		
	def on_cancel_clicked(self, src, data=None):
		self.window.destroy()
		
	def on_done_clicked(self, src, data=None):
		if self.sop_address.get_text()[:len("sop://".lower())] != "sop://".lower():
			self.sop_address.get_text()
		else:		
			self.window.destroy()
		
	def __getattribute__(self, key):
		value = None
		try:
			value = object.__getattribute__(self, key)
		except AttributeError:
			glade_window = object.__getattribute__(self, 'glade_window')
			value = glade_window.get_widget(key)	

		return value
		
if __name__ == '__main__':
	def print_usage_and_exit():
		print "Usage: sopcast-player [SOP_ADDRESS] [IN-BOUND_PORT OUT-BOUND_PORT]"
		sys.exit(1)
		
	if len(sys.argv) > 1:
		if len(sys.argv) == 2 and sys.argv[1][:len("sop://".lower())] == "sop://".lower():
				pySop = pySopCast(sys.argv[1])
				pySop.main()
				
		elif len(sys.argv) == 4 and sys.argv[1][:len("sop://".lower())] == "sop://".lower():
			try:
				pySop = pySopCast(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
				pySop.main()
			except ValueError:
				print_usage_and_exit()
		else:
			print_usage_and_exit()
	else:
		#pySop = pySopCast()
		pySop = ChannelGuide2()
		pySop.main()
	
	
