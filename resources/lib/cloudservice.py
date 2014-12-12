'''
    Copyright (C) 2013-2014 ddurdle

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

import os
import re
import urllib, urllib2
#from resources.lib import authorization



import xbmc, xbmcaddon, xbmcgui, xbmcplugin


#
#
#
class cloudservice(object):

    def __init__(self): pass


    ##
    # perform login
    ##
    def login(self): pass

    ##
    # if we don't have an authorization token set for the plugin, set it with the recent login.
    #   auth_token will permit "quicker" login in future executions by reusing the existing login session (less HTTPS calls = quicker video transitions between clips)
    ##
    def updateAuthorization(self,addon):
        if self.authorization.isUpdated and addon.getSetting(self.instanceName+'_save_auth_token') == 'true':
            self.authorization.saveTokens(self.instanceName,addon)

    ##
    # return the appropriate "headers" for requests that include 1) user agent, 2) any authorization cookies/tokens
    #   returns: list containing the header
    ##
    def getHeadersList(self):
        return { 'User-Agent' : self.user_agent }

    ##
    # return the appropriate "headers" for requests that include 1) user agent, 2) any authorization cookies/tokens
    #   returns: URL-encoded header string
    ##
    def getHeadersEncoded(self):
        return urllib.urlencode(self.getHeadersList())

    # helper methods
    def log(msg, err=False):
        if err:
            xbmc.log(self.addon.getAddonInfo('name') + ': ' + msg, xbmc.LOGERROR)
        else:
            xbmc.log(self.addon.getAddonInfo('name') + ': ' + msg, xbmc.LOGDEBUG)


    def traverse(self, path, cacheType, folderID, savePublic, level):
        import os
        import xbmcvfs

        xbmcvfs.mkdir(path)

        folders = self.getFolderList(folderID)
        files = self.getMediaList(folderID,cacheType)

        if files:
            for media in files:
                filename = xbmc.translatePath(os.path.join(path, media.title+'.strm'))
                strmFile = open(filename, "w")

                strmFile.write(self.PLUGIN_URL+'?mode=streamURL&url=' + self.FILE_URL+ media.id +'\n')
                strmFile.close()

        if folders and level == 1:
            count = 1
            progress = xbmcgui.DialogProgress()
            progress.create(self.addon.getLocalizedString(30000),self.addon.getLocalizedString(30036),'\n','\n')

            for folder in folders:
                max = len(folders)
                progress.update(count/max*100,self.addon.getLocalizedString(30036),folder.title,'\n')
                self.traverse( path+'/'+folder.title + '/',cacheType,folder.id,savePublic,0)
                count = count + 1

        if folders and level == 0:
            for folder in folders:
                self.traverse( path+'/'+folder.title + '/',cacheType,folder.id,savePublic,0)


