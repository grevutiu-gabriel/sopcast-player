import sys
import os
import gtk

class OpenSopAddress(object):
	def __init__(self, parent):
		self.window = None
		self.parent = parent
		
	def main(self):
		gladefile = "%s/%s" % (os.path.realpath(os.path.dirname(sys.argv[0])), "../ui/OpenSopAddress.glade")
			
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
