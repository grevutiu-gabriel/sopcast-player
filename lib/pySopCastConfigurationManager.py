# pySopCast implementation of ConfigurationManager
# Copyright (C) 2009 Jason Scheunemann <jason.scheunemann@yahoo.com>.

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import ConfigurationManager
import os

class ChannelGuideLanguages:
	ENGLISH = 0
	CHINESE = 1

class pySopCastConfigurationManager(ConfigurationManager.ConfigurationManager):
	def __init__(self):
		ConfigurationManager.ConfigurationManager.__init__(self, os.path.expanduser('~/.pySopCast/pySopCast.cfg'))
					     
		self.add_section("player", { "show_toolbar" : True,
					     "static_ports" : False,
					     "width" : 600,
					     "height" : 400,
					     "div_position" : -1,
					     "show_channel_guide" : True,
					     "inbound_port" : 8901,
					     "outbound_port" : 8902,
					     "volume" : 100,
					     "server" : "127.0.0.1",
					     "channel_guide_width" : 80,
					     "external_player" : False,
					     "external_player_command" : "mplayer -ontop -geometry 100%%:100%%",
					     "channel_timeout" : 3,
					     "stay_on_top" : False })
						  
		self.add_section("ChannelGuide", { "default_width" : 650,
						    "default_height" : 550,
						    "auto_refresh" : False,
						    "default_language" : True,
						    "last_updated" : "Never",
						    "language" : ChannelGuideLanguages.ENGLISH,
						    "url" : "http://www.sopcast.com/gchlxml",
						    "div_position" : -1 })
		
