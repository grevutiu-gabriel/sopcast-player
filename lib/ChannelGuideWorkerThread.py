# Copyright (C) 2011 Jason Scheunemann <jason.scheunemann@yahoo.com>.
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

import fork
import sys
import threading
import time
import os
import gtk
import FileDownload
import ImportChannelGuide
import DatabaseOperations
import datetime
import pySopCastConfigurationManager

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
		
		gtk.gdk.threads_enter()
		self.parent.refresh_channel_guide.set_sensitive(False)
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
		
			t = datetime.datetime.now()

			config_manager = pySopCastConfigurationManager.pySopCastConfigurationManager()
			config_manager.set("ChannelGuide", "last_updated", time.mktime(t.timetuple()))
			config_manager.write()
		
			time.sleep(5)
			gtk.gdk.threads_enter()
			if self.parent.update_channel_guide_progress != None:
				self.parent.update_channel_guide_progress.hide()
				self.parent.channel_guide_label.show()
			gtk.gdk.threads_leave()
				
			self.updated = True
		except(Exception):
			gtk.gdk.threads_enter()
			if self.parent.update_channel_guide_progress != None:
				self.parent.update_channel_guide_progress.set_text(_("Server Down"))
			gtk.gdk.threads_leave()
			
		gtk.gdk.threads_enter()
		self.parent.refresh_channel_guide.set_sensitive(True)
		gtk.gdk.threads_leave()
		
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
		self.parent.update_channel_guide_progress.set_text("%s: %d%%" % (_("Downloading"), percent))
		gtk.gdk.threads_leave()
		
		gtk.gdk.threads_enter()
		self.parent.update_channel_guide_progress.set_fraction(float(percent / 100.0))
		gtk.gdk.threads_leave()		

