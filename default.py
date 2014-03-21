'''
    owncloud XBMC Plugin
    Copyright (C) 2013 dmdsoftware

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from resources.lib import owncloud
import sys
import urllib
import cgi
import re

import xbmc, xbmcgui, xbmcplugin, xbmcaddon

# global variables
PLUGIN_NAME = 'plugin.video.owncloud'
PLUGIN_URL = 'plugin://'+PLUGIN_NAME+'/'
ADDON = xbmcaddon.Addon(id=PLUGIN_NAME)


#helper methods
def log(msg, err=False):
    if err:
        xbmc.log(ADDON.getAddonInfo('name') + ': ' + msg, xbmc.LOGERROR)
    else:
        xbmc.log(ADDON.getAddonInfo('name') + ': ' + msg, xbmc.LOGDEBUG)

def parse_query(query):
    queries = cgi.parse_qs(query)
    q = {}
    for key, value in queries.items():
        q[key] = value[0]
    q['mode'] = q.get('mode', 'main')
    return q

def addVideo(url, infolabels, label, img='', fanart='', total_items=0,
                   cm=[], cm_replace=False):
    infolabels = decode_dict(infolabels)
    log('adding video: %s - %s' % (infolabels['title'], url))
    listitem = xbmcgui.ListItem(label, iconImage=img,
                                thumbnailImage=img)
    listitem.setInfo('video', infolabels)
    listitem.setProperty('IsPlayable', 'true')
    listitem.setProperty('fanart_image', fanart)
    if cm:
        listitem.addContextMenuItems(cm, cm_replace)
    xbmcplugin.addDirectoryItem(plugin_handle, url, listitem,
                                isFolder=False, totalItems=total_items)

def addMusic(url, infolabels, label, img='', fanart='', total_items=0,
                   cm=[], cm_replace=False):
    infolabels = decode_dict(infolabels)
    log('adding video: %s - %s' % (infolabels['title'], url))
    listitem = xbmcgui.ListItem(label, iconImage=img,
                                thumbnailImage=img)
    listitem.setInfo('music', infolabels)
    listitem.setProperty('IsPlayable', 'true')
    listitem.setProperty('fanart_image', fanart)
    if cm:
        listitem.addContextMenuItems(cm, cm_replace)
    xbmcplugin.addDirectoryItem(plugin_handle, url, listitem,
                                isFolder=False, totalItems=total_items)

def addDirectory(url, title, img='', fanart='', total_items=0):
    log('adding dir: %s - %s' % (title, url))
    listitem = xbmcgui.ListItem(decode(title), iconImage=img, thumbnailImage=img)
    if not fanart:
        fanart = ADDON.getAddonInfo('path') + '/fanart.jpg'
    listitem.setProperty('fanart_image', fanart)
    xbmcplugin.addDirectoryItem(plugin_handle, url, listitem,
                                isFolder=True, totalItems=total_items)

#http://stackoverflow.com/questions/1208916/decoding-html-entities-with-python/1208931#1208931
def _callback(matches):
    id = matches.group(1)
    try:
        return unichr(int(id))
    except:
        return id

def decode(data):
    return re.sub("&#(\d+)(;|(?=\s))", _callback, data).strip()

def decode_dict(data):
    for k, v in data.items():
        if type(v) is str or type(v) is unicode:
            data[k] = decode(v)
    return data



#global variables
plugin_url = sys.argv[0]
plugin_handle = int(sys.argv[1])
plugin_queries = parse_query(sys.argv[2][1:])


try:

    remote_debugger = ADDON.getSetting('remote_debugger')
    remote_debugger_host = ADDON.getSetting('remote_debugger_host')

    # append pydev remote debugger
    if remote_debugger == 'true':
        # Make pydev debugger works for auto reload.
        # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
        import pysrc.pydevd as pydevd
        # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
        pydevd.settrace(remote_debugger_host, stdoutToServer=True, stderrToServer=True)
except ImportError:
    log(ADDON.getLocalizedString(30016), True)
    sys.exit(1)
except :
    pass


# retrieve settings
username = ADDON.getSetting('username')
password = ADDON.getSetting('password')
domain = ADDON.getSetting('domain')
protocol = int(ADDON.getSetting('protocol'))
user_agent = ADDON.getSetting('user_agent')
auth = ADDON.getSetting('auth')
session = ADDON.getSetting('session')


if protocol == 1:
    protocol = 'https://'
else:
    protocol = 'http://'


# you need to have at least a username&password set
if ((username == '' or password == '')):
    xbmcgui.Dialog().ok(ADDON.getLocalizedString(30000), ADDON.getLocalizedString(30015))
    log(ADDON.getLocalizedString(30015), True)
    xbmcplugin.endOfDirectory(plugin_handle)


owncloud = owncloud.owncloud(username, password, protocol, domain, auth, session, user_agent)


log('plugin url: ' + plugin_url)
log('plugin queries: ' + str(plugin_queries))
log('plugin handle: ' + str(plugin_handle))

mode = plugin_queries['mode']

#dump a list of videos available to play
if mode == 'main' or mode == 'folder':
    log(mode)

    cacheType = int(ADDON.getSetting('playback_type'))

    folderID=0
    if (mode == 'folder'):
        folderName = plugin_queries['directory']
        videos = owncloud.getVideosList(folderName, cacheType=cacheType)
    else:
        videos = owncloud.getVideosList(cacheType=cacheType)

    for title in sorted(videos.iterkeys()):
        if videos[title]['mediaType'] == owncloud.MEDIA_TYPE_FOLDER:
            addDirectory(videos[title]['url'],title)
        elif videos[title]['mediaType'] == owncloud.MEDIA_TYPE_VIDEO:
            addVideo(videos[title]['url'],{ 'title' : title , 'plot' : title }, title)
        elif videos[title]['mediaType'] == owncloud.MEDIA_TYPE_MUSIC:
            addMusic(videos[title]['url'],{ 'title' : title , 'plot' : title }, title)

#play a video given its exact-title
elif mode == 'video':
    filename = plugin_queries['filename']
    cacheType = ADDON.getSetting('playback_type')

    if cacheType == '0':
      videoURL = owncloud.getVideoLink(title)
    else:
      videoURL = owncloud.getVideoLink(title,True,cacheType)

    item = xbmcgui.ListItem(path=videoURL)
    log('play url: ' + videoURL)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)



#force stream - play a video given its exact-title
elif mode == 'audio':
    try:
      filename = plugin_queries['filename']
    except:
      title = 0


    # immediately play resulting (is a video)
    videoURL = owncloud.getVideoLink(filename, 2)
    item = xbmcgui.ListItem(path=videoURL)
    log('play url: ' + videoURL)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)


if auth != owncloud.auth:
    ADDON.setSetting('auth', owncloud.auth)

if session != owncloud.session:
    ADDON.setSetting('session', owncloud.session)


xbmcplugin.endOfDirectory(plugin_handle)

