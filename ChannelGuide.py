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
import locale
import socket
import sys
import threading
import time
import os
import urllib

sys.path.append(os.path.abspath("%s/%s") % (os.path.dirname(sys.argv[0]), 'lib/'))
import DatabaseOperations
import FileDownload
import ImportChannelGuide
import AddBookmark
import pySopCastConfigurationManager
import pySopCast

loc = locale.getdefaultlocale()
locale.setlocale(locale.LC_ALL, loc)

class UpdateUIThread(threading.Thread):
	def __init__ (self, parent):
		threading.Thread.__init__(self)
		self.parent = parent
		self.downloader = FileDownload.FileDownload()
		self.guide_import = ImportChannelGuide.ImportChannelGuide()
		self.daemon = True
		self.running = True
		
	def run(self):
		gtk.gdk.threads_enter()
		self.parent.update_statusbar("%s" % (_("Contacting Server")), True)
		gtk.gdk.threads_leave()
		
		try:
			self.downloader.download_file('http://www.sopcast.com/gchlxml', os.path.expanduser('~/.pySopCast/channel_guide.xml'), self.report_progress)
			
			gtk.gdk.threads_enter()
			self.parent.update_statusbar("%s" % (_("Updating Database")), True)
			gtk.gdk.threads_leave()
			self.guide_import.update_database(os.path.expanduser('~/.pySopCast/channel_guide.xml'))
			
			self.parent.populate_channel_treeview()
			
			gtk.gdk.threads_enter()
			self.parent.update_statusbar("%s" % (_("Channel Guide Update Completed")), True)
			gtk.gdk.threads_leave()
			
			config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
			config_manager.read()
			config_manager.set("ChannelGuide", "last_updated", time.strftime(locale.nl_langinfo(locale.D_T_FMT)))
			config_manager.write()
			
			time.sleep(5)
			
			gtk.gdk.threads_enter()
			self.parent.update_statusbar("", True)
			gtk.gdk.threads_leave()
		except Exception, e:
			gtk.gdk.threads_enter()
			self.parent.update_statusbar("%s" % (_("Channel Guide Retrieval Failed Due to Network Problems")), True)
			gtk.gdk.threads_leave()
			print e
		
		self.running = False
	
	def report_progress(self, numblocks, blocksize, filesize):
		try:
			percent = min((numblocks*blocksize*100)/filesize, 100)
		except:
			percent = 100
		
		gtk.gdk.threads_enter()
		self.parent.update_statusbar("%s: %d%%" %(_("Downloading Channel Guide"), percent), True)
		gtk.gdk.threads_leave()


class ChannelGuide(object):

	def __init__(self, parent=None):
		gtk.gdk.threads_init()
		self.window = None
		self.parent = parent
		self.ui_worker = None
		self.selected_iter = None
		self.selection = None
		self.add_bookmark_dialog = AddBookmark.AddBookmark(self)
		self.db_operations = DatabaseOperations.DatabaseOperations()
		
	def main(self):
		gladefile = os.path.abspath("%s/%s") % (os.path.dirname(sys.argv[0]), 'ui/ChannelGuide.glade')
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
		self.treeview_selection.connect("changed", self.on_selection_changed)
		self.channel_treeview.connect("row_activated", self.on_channel_treeview_row_activated)
		
		config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
		config_manager.read()
		last_updated = config_manager.get("ChannelGuide", "last_updated")
		
		self.update_statusbar("%s %s" % (_("Channel Guide Last Updated"), last_updated))
				
		self.populate_channel_treeview()
		
		self.window.show_all()
		
		gtk.gdk.threads_enter()
		gtk.main()
		gtk.gdk.threads_leave()
	
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
				if self.parent.channel_url_entry == None:
					self.parent = pySopCast.pySopCast()
					self.parent.main(self.selection[9], self.selection[1])
				else:
					self.parent.play_channel(self.selection[9], self.selection[1])
			
	def on_toolbar_play_clicked(self, src, data=None):
			if self.parent.channel_url_entry == None:
				self.parent = pySopCast.pySopCast()
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
			
				self.ui_worker = UpdateUIThread(self)
				self.ui_worker.start()
		else:
			self.ui_worker = UpdateUIThread(self)
			self.ui_worker.start()
	
	def on_menu_about_activate(self, src, data=None):
		gladefile = os.path.abspath("%s/%s") % (os.path.dirname(sys.argv[0]), 'ui/About.glade')
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
		
		if self.parent.channel_url_entry != None:
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

