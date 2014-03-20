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

import os
import re
import urllib, urllib2
import cookielib


import xbmc, xbmcaddon, xbmcgui, xbmcplugin

# global variables
PLUGIN_NAME = 'plugin.video.owncloud'
PLUGIN_URL = 'plugin://'+PLUGIN_NAME+'/'
ADDON = xbmcaddon.Addon(id=PLUGIN_NAME)


# helper methods
def log(msg, err=False):
    if err:
        xbmc.log(ADDON.getAddonInfo('name') + ': ' + msg, xbmc.LOGERROR)
    else:
        xbmc.log(ADDON.getAddonInfo('name') + ': ' + msg, xbmc.LOGDEBUG)


#
#
#
class owncloud:


    PROTOCOL = 'https://'
    ##
    # initialize (setting 1) username, 2) password, 3) authorization token, 4) user agent string
    ##
    def __init__(self, user, password, domain, user_agent):
        self.user = user
        self.password = password
        self.user_agent = user_agent
        self.domain = domain
        self.cookiejar = cookielib.CookieJar()

#        self.login();
        return


    ##
    # perform login
    ##
    def login(self):

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        # default User-Agent ('Python-urllib/2.6') will *not* work
        opener.addheaders = [('User-Agent', self.user_agent)]

        url = self.PROTOCOL + self.domain +'/'

        try:
            response = opener.open(url)

        except urllib2.URLError, e:
            log(str(e), True)
            return
        response_data = response.read()
        response.close()

        url = self.PROTOCOL + self.domain + '/'

        values = {
                  'password' : self.password,
                  'user' : self.user,
                  'remember_login' : 1,
                  'timezone-offset' : -4,
        }

        log('logging in')

        # try login
        try:
            response = opener.open(url,urllib.urlencode(values))

        except urllib2.URLError, e:
            if e.code == 403:
                #login denied
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(30000), ADDON.getLocalizedString(30017))
            log(str(e), True)
            return
        response_data = response.read()
        response.close()


        loginResult = 0
        #validate successful login
        for r in re.finditer('(data-user)\=\"([^\"]+)\"',
                             response_data, re.DOTALL):
            loginType,loginResult = r.groups()

        if (loginResult == 0 or loginResult != self.user):
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(30000), ADDON.getLocalizedString(30017))
            log('login failed', True)
            return

        return


    ##
    # return the appropriate "headers" for owncloud requests that include 1) user agent, 2) authorization cookie
    #   returns: list containing the header
    ##
    def getHeadersList(self):
        if (self.cookie != '' or self.cookie != 0):
            return { 'User-Agent' : self.user_agent, 'Cookie' : 'auth='+self.cookie+'; exp=1' }
        else:
            return { 'User-Agent' : self.user_agent }

    ##
    # return the appropriate "headers" for owncloud requests that include 1) user agent, 2) authorization cookie
    #   returns: URL-encoded header string
    ##
    def getHeadersEncoded(self):
        return urllib.urlencode(self.getHeadersList())

    ##
    # retrieve a list of videos, using playback type stream
    #   parameters: prompt for video quality (optional), cache type (optional)
    #   returns: list of videos
    ##
    def getVideosList(self, folderID=0, cacheType=0):

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        # default User-Agent ('Python-urllib/2.6') will *not* work
        opener.addheaders = [('User-Agent', self.user_agent)]

        url = self.PROTOCOL + self.domain +'/index.php/apps/files'

        videos = {}
        if True:
            # if action fails, validate login
            try:
              response = opener.open(url)
            except urllib2.URLError, e:
              if e.code == 403 or e.code == 401:
                self.login()
              else:
                log(str(e), True)
                return
            response_data = response.read()
            response.close()

            loginResult = 0
            #validate successful login
            for r in re.finditer('(data-user)\=\"([^\"]+)\"',
                             response_data, re.DOTALL):
                loginType,loginResult = r.groups()

            if (loginResult == 0 or loginResult != self.user):
                self.login()
                try:
                    response = opener.open(url)
                    response_data = response.read()
                    response.close()
                except urllib2.URLError, e:
                    log(str(e), True)
                    return



            # parsing page for videos
            # video-entry
            for r in re.finditer('"gal_thumb":"([^\"]+)"\,.*?type\=\'video\'.*?"file_filename":"([^\"]+)","al_title":"([^\"]+)".*?alias\=([^\"]+)"' ,response_data, re.DOTALL):
                img,filename,title,fileID = r.groups()
                img = re.sub('\\\\', '', img)
                img = 'http://static.owncloud.com/'+img


                log('found video %s %s' % (title, filename))

                # streaming
                videos[title] = {'url': 'plugin://plugin.video.owncloud?mode=streamVideo&filename=' + fileID, 'thumbnail' : img}

            for r in re.finditer('"gal_thumb":"([^\"]+)"\,.*?type\=\'audio\'.*?"file_filename":"([^\"]+)","al_title":"([^\"]+)".*?alias\=([^\"]+)"' ,response_data, re.DOTALL):
                img,filename,title,fileID = r.groups()
                img = re.sub('\\\\', '', img)
                img = 'http://static.owncloud.com/'+img

                log('found audio %s %s' % (title, filename))

                # streaming
                videos[title] = {'url': 'plugin://plugin.video.owncloud?mode=streamVideo&filename=' + fileID, 'thumbnail' : img}

            response.close()

        return videos


    ##
    # retrieve a list of folders
    #   parameters: folder is the current folderID
    #   returns: list of videos
    ##
    def getFolderList(self, folderID=0):

        # retrieve all documents
        params = urllib.urlencode({'getFolders': folderID, 'format': 'large', 'term': '', 'group':0, 'user_token': self.auth, '_': 1394486104901})

        url = 'http://www.owncloud.com/action/?'+ params

        folders = {}
        if True:
            log('url = %s header = %s' % (url, self.getHeadersList()))
            req = urllib2.Request(url, None, self.getHeadersList())

            # if action fails, validate login
            try:
              response = urllib2.urlopen(req)
            except urllib2.URLError, e:
              if e.code == 403 or e.code == 401:
                self.login()
                req = urllib2.Request(url, None, self.getHeadersList())
                try:
                  response = urllib2.urlopen(req)
                except urllib2.URLError, e:
                  log(str(e), True)
                  return
              else:
                log(str(e), True)
                return

            response_data = response.read()

            # parsing page for videos
            # video-entry
            for r in re.finditer('"f_id":"([^\"]+)".*?"f_fullname":"([^\"]+)"' ,response_data, re.DOTALL):
                folderID, folderName = r.groups()

                log('found folder %s %s' % (folderID, folderName))

                # streaming
                folders[folderName] = 'plugin://plugin.video.owncloud?mode=folder&folderID=' + folderID

            response.close()

        return folders



    ##
    # retrieve a video link
    #   parameters: title of video, whether to prompt for quality/format (optional), cache type (optional)
    #   returns: list of URLs for the video or single URL of video (if not prompting for quality)
    ##
    def getVideoLink(self,filename,cacheType=0):


        # search by video title
        params = urllib.urlencode({'file_id': filename, 'group_id': 0, 'page': 1, 'total':7, 'index':0, 'all':'false','user_token': self.auth, '_': 1394486104901})
        url = 'http://www.owncloud.com/view_media/?'+params


        log('url = %s header = %s' % (url, self.getHeadersList()))
        req = urllib2.Request(url, None, self.getHeadersList())


        # if action fails, validate login
        try:
            response = urllib2.urlopen(req)
        except urllib2.URLError, e:
            if e.code == 403 or e.code == 401:
              self.login()
              req = urllib2.Request(url, None, self.getHeadersList())
              try:
                response = urllib2.urlopen(req)
              except urllib2.URLError, e:
                log(str(e), True)
                return
            else:
              log(str(e), True)
              return

        response_data = response.read()

        playbackURL = 0
        # fetch video title, download URL and docid for stream link
        for r in re.finditer('\{\"id"\:\"([^\"]+)\"\,\"title\"\:\"([^\"]+)\"\,.*?\"down\"\:\"([^\"]+)\"[^\}]+\}' ,response_data, re.DOTALL):
             fileID,fileTitle,fileURL = r.groups()
             if fileID == filename:
                 log('found video %s %s %s' % (fileID, fileURL, fileTitle))
                 fileURL = re.sub('\\\\', '', fileURL)
                 playbackURL = fileURL


        response.close()

        return playbackURL


    ##
    # retrieve a video link
    #   parameters: title of video, whether to prompt for quality/format (optional), cache type (optional)
    #   returns: list of URLs for the video or single URL of video (if not prompting for quality)
    ##
    def getPublicLink(self,url,cacheType=0):


        log('url = %s header = %s' % (url, self.getHeadersList()))
        req = urllib2.Request(url, None, self.getHeadersList())


        # if action fails, validate login
        try:
            response = urllib2.urlopen(req)
        except urllib2.URLError, e:
            if e.code == 403 or e.code == 401:
              self.login()
              req = urllib2.Request(url, None, self.getHeadersList())
              try:
                response = urllib2.urlopen(req)
              except urllib2.URLError, e:
                log(str(e), True)
                return
            else:
              log(str(e), True)
              return

        response_data = response.read()

        confirmID = 0
        # fetch video title, download URL and docid for stream link
        for r in re.finditer('name\=\"(confirm)\" value\=\"([^\"]+)"\/\>' ,response_data, re.DOTALL):
             confirmType,confirmID = r.groups()

        response.close()

        if confirmID == 0:
            return

        values = {
                  'confirm' : confirmID,
        }

        req = urllib2.Request(url, urllib.urlencode(values), self.getHeadersList())


        # if action fails, validate login
        try:
            response = urllib2.urlopen(req)
        except urllib2.URLError, e:
            if e.code == 403 or e.code == 401:
              self.login()
              req = urllib2.Request(url,  urllib.urlencode(values), self.getHeadersList())
              try:
                response = urllib2.urlopen(req)
              except urllib2.URLError, e:
                log(str(e), True)
                return
            else:
              log(str(e), True)
              return

        response_data = response.read()

        streamURL = 0
        # fetch video title, download URL and docid for stream link
        for r in re.finditer('(file)\: \'([^\']+)' ,response_data, re.DOTALL):
             streamType,streamURL = r.groups()


        response.close()


        return streamURL




