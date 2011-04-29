import os
import sys
import gtk

class AddBookmark(object):
	def __init__(self, parent, title=None, url=None):
		self.window = None
		self.parent = parent
		self.title = title
		self.url = url
		
	def main(self):
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "../ui/AddBookmark.glade")
		
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
		if self.channel_name.get_text() != "":
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
