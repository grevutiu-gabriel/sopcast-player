import fork
import sys
import threading
import time
import os
import gtk

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
									print("stoping external media player")
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
											print("Executing " + self.parent.external_player_command)
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
			print(point)
	
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
