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
import locale

class ChannelGuideLanguages:
	ENGLISH = 0
	CHINESE = 1

class ChannelGuideLayout:
	UNITY = 0
	DUAL_WINDOW = 1

cur_locale = locale.setlocale(locale.LC_ALL, "")

def is_chinese():
	return not cur_locale[:len("zh".lower())] != "zh".lower()

class pySopCastConfigurationManager(ConfigurationManager.ConfigurationManager):
	def __init__(self):
		ConfigurationManager.ConfigurationManager.__init__(self, os.path.expanduser('~/.pySopCast/pySopCast.cfg'))
		
		if is_chinese() == True:
			language = _("Chinese")
			channel_guide = "http://channel.sopcast.com/gchlxml"
		else:
			language = _("English")
			channel_guide = "http://www.sopcast.com/gchlxml"
					     
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
						  
		self.add_section("ChannelGuide", {  "width" : 600,
						    "height" : 400,
						    "default_width" : 650,
						    "default_height" : 550,
						    "auto_refresh" : False,
						    "channel_guide_language" : language,
						    "last_updated" : "Never",
						    "url" : channel_guide,
						    "div_position" : -1,
						    "layout" : ChannelGuideLayout.UNITY })
		
