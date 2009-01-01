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

import os
import signal
import sys
import time

class ForkSOP:
	def __init__(self, sop_address=None, inbound_port=None, outbound_port=None):
		self.child_pid = None
		self.sop_address = sop_address
		self.inbound_port = inbound_port
		self.outbound_port = outbound_port
		
	def fork_sop(self, sop_address=None, inbound_port=None, outbound_port=None):
		self.sop_address = sop_address
		self.inbound_port = inbound_port
		self.outbound_port = outbound_port
		
		if self.sop_address == None or self.inbound_port == None or self.outbound_port == None:
			perror("invalid call to fork_sop")
		else:
			pid = os.fork();
			if pid == -1: #fork error
				perror("fork")
				self.child_pid = None
			elif pid == 0: #execute in child
				os.execlp("sp-sc", "sp-sc", self.sop_address, self.inbound_port, self.outbound_port)
			else: #child's pid, main process execution
				self.child_pid = pid
			
	def kill_sop(self):
		if self.is_running() == True:
			try:
				os.kill(self.child_pid, signal.SIGKILL)
				killedpid, stat = os.wait()
			except OSError:
				sys.stderr.write("Process %s does not exist\n" % self.child_pid)
	
	def is_running(self):
		if self.child_pid != None:
			try:
				os.kill(self.child_pid, 0)
				return True
			except OSError:
				return False
		else:
			return False

