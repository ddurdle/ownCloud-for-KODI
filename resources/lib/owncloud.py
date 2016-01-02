'''
    owncloud XBMC Plugin
    Copyright (C) 2013-2016 ddurdle

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

from resources.lib import authorization
from cloudservice import cloudservice
from resources.lib import folder
from resources.lib import file
from resources.lib import package
from resources.lib import mediaurl


#
#
#
class owncloud(cloudservice):


    AUDIO = 1
    VIDEO = 2
    PICTURE = 3

    MEDIA_TYPE_MUSIC = 1
    MEDIA_TYPE_VIDEO = 2
    MEDIA_TYPE_PICTURE = 3

    MEDIA_TYPE_FOLDER = 0

    CACHE_TYPE_MEMORY = 0
    CACHE_TYPE_DISK = 1
    CACHE_TYPE_AJAX = 2
    OWNCLOUD_V6 = 0
    OWNCLOUD_V7 = 1
    OWNCLOUD_V82 = 2

    #
    # initialize (save addon, instance name, user agent)
    ##
    def __init__(self, PLUGIN_URL, addon, instanceName, user_agent):
        self.PLUGIN_URL = PLUGIN_URL
        self.addon = addon
        self.instanceName = instanceName

        try:
            if self.addon.getSetting(self.instanceName+'_ssl') == 'true':
                import ssl
                ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass

        try:
            username = self.addon.getSetting(self.instanceName+'_username')
        except:
            username = ''
        self.authorization = authorization.authorization(username)

        try:
            self.version = int(self.addon.getSetting(self.instanceName+'_version'))
        except:
            self.version = OWNCLOUD_V6

        try:
            protocol = int(self.addon.getSetting(self.instanceName+'_protocol'))
            if protocol == 1:
                self.protocol = 'https://'
            else:
                self.protocol = 'http://'
        except:
            self.protocol = 'http://'

        try:
            self.domain = self.addon.getSetting(self.instanceName+'_domain')
        except:
            self.domain = 'localhost'


        self.cookiejar = cookielib.CookieJar()

        try:
            auth = self.addon.getSetting(self.instanceName+'_auth_token')
            session = self.addon.getSetting(self.instanceName+'_auth_session')
        except:
            auth = ''
            session = ''

        self.authorization.setToken('auth_token',auth)
        self.authorization.setToken('auth_session',session)


        self.user_agent = user_agent

        #public playback only -- no authentication
        if self.authorization.username == '':
            return

        # if we have an authorization token set, try to use it
        if auth != '':
          xbmc.log(self.addon.getAddonInfo('name') + ': ' + 'using token', xbmc.LOGDEBUG)
          return
        else:
          xbmc.log(self.addon.getAddonInfo('name') + ': ' + 'no token - logging in', xbmc.LOGDEBUG)
          self.login();
          return


    ##
    # perform login
    ##
    def login(self):

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        # default User-Agent ('Python-urllib/2.6') will *not* work
        opener.addheaders = [('User-Agent', self.user_agent)]

        url = self.protocol + self.domain +'/'

        try:
            response = opener.open(url)

        except urllib2.URLError, e:
            xbmc.log(self.addon.getAddonInfo('name') + ': ' + str(e), xbmc.LOGERROR)
            return
        response_data = response.read()
        response.close()

        requestToken = None

#        for cookie in self.cookiejar:
#            for r in re.finditer(' ([^\=]+)\=([^\s]+)\s',
#                        str(cookie), re.DOTALL):
#                cookieType,cookieValue = r.groups()
#                if cookieType == 'oc_token':
#                    self.authorization.setToken('auth_token',cookieValue)
#                elif cookieType != 'oc_remember_login' and cookieType != 'oc_username':
#                    self.authorization.setToken('auth_session',cookieType + '=' + cookieValue)
#
#        return

        #owncloud7
        for r in re.finditer('name=\"requesttoken\" value\=\"([^\"]+)\"',
                             response_data, re.DOTALL):
            requestToken = r.group(1)

        if requestToken == None:
            for r in re.finditer('data-requesttoken\=\"([^\"]+)\"',
                                response_data, re.DOTALL):
                requestToken = r.group(1)

        if requestToken != '':
            self.authorization.setToken('auth_requesttoken',requestToken)

        url = self.protocol + self.domain + '/index.php'


        values = {
                  'password' : self.addon.getSetting(self.instanceName+'_password'),
                  'user' : self.authorization.username,
                  'remember_login' : 1,
                  'requesttoken' : requestToken,
                  'timezone-offset' : -4,
        }

        # try login
        try:
            response = opener.open(url,urllib.urlencode(values))

        except urllib2.URLError, e:
            if e.code == 403:
                #login denied
                xbmcgui.Dialog().ok(self.addon.getLocalizedString(30000), self.addon.getLocalizedString(30017))
                xbmc.log(self.addon.getAddonInfo('name') + ': ' + str(e), xbmc.LOGERROR)
            return
        response_data = response.read()
        response.close()


        loginResult = 0
        #validate successful login
        for r in re.finditer('(data-user)\=\"([^\"]+)\"',
                             response_data, re.DOTALL):
            loginType,loginResult = r.groups()

        if (loginResult == 0 or loginResult != self.authorization.username):
            xbmcgui.Dialog().ok(self.addon.getLocalizedString(30000), self.addon.getLocalizedString(30017))
            xbmc.log(self.addon.getAddonInfo('name') + ': ' + 'login failed', xbmc.LOGERROR)
            return

        if (self.version == self.OWNCLOUD_V82):
            sessionString = ''
            for cookie in self.cookiejar:
                for r in re.finditer(' ([^\=]+)\=([^\s]+)\s',
                        str(cookie), re.DOTALL):
                    cookieType,cookieValue = r.groups()
                    if cookieType == 'oc_token':
                        self.authorization.setToken('auth_token',cookieValue)
                    elif cookieType != 'oc_remember_login' and cookieType != 'oc_username'  and cookieType != 'oc_token' and cookieType != 'oc_token':
                        sessionString = str(sessionString) + str(cookieType) + '=' + str(cookieValue)+'; '
            self.authorization.setToken('auth_session',sessionString)


        else:
            for cookie in self.cookiejar:
                for r in re.finditer(' ([^\=]+)\=([^\s]+)\s',
                        str(cookie), re.DOTALL):
                    cookieType,cookieValue = r.groups()
                    if cookieType == 'oc_token':
                        self.authorization.setToken('auth_token',cookieValue)
                    elif cookieType != 'oc_remember_login' and cookieType != 'oc_username':
                        self.authorization.setToken('auth_session',cookieType + '=' + cookieValue)

        return


    ##
    # return the appropriate "headers" for owncloud requests that include 1) user agent, 2) authorization cookie
    #   returns: list containing the header
    ##
    def getHeadersList(self):
        auth = self.authorization.getToken('auth_token')
        session = self.authorization.getToken('auth_session')
        token = self.authorization.getToken('auth_requesttoken')

        if (self.version == self.OWNCLOUD_V82):
            if (auth != '' or session != ''):
                return [('User-Agent', self.user_agent), ('Cookie', session)]
            else:
                return [('User-Agent', self.user_agent )]

        else:

            if (auth != '' or session != ''):
                return [('User-Agent', self.user_agent), ('OCS-APIREQUEST', 'true'), ('requesttoken', token), ('Cookie', session+'; oc_username='+self.authorization.username+'; oc_token='+auth+'; oc_remember_login=1')]
            else:
                return [('User-Agent', self.user_agent )]



    ##
    # return the appropriate "headers" for owncloud requests that include 1) user agent, 2) authorization cookie
    #   returns: URL-encoded header string
    ##
    def getHeadersEncoded(self):
        auth = self.authorization.getToken('auth_token')
        session = self.authorization.getToken('auth_session')

        if (self.version == self.OWNCLOUD_V82):
            if (auth != '' or session != ''):
                return urllib.urlencode({ 'User-Agent' : self.user_agent, 'Cookie' : session })
            else:
                return urllib.urlencode({ 'User-Agent' : self.user_agent })

        else:

            if (auth != '' or session != ''):
                return urllib.urlencode({ 'User-Agent' : self.user_agent, 'Cookie' : session+'; oc_username='+self.authorization.username+'; oc_token='+auth+'; oc_remember_login=1' })
            else:
                return urllib.urlencode({ 'User-Agent' : self.user_agent })

    ##
    # retrieve a list of videos, using playback type stream
    #   parameters: prompt for video quality (optional), cache type (optional)
    #   returns: list of videos
    ##
    def getMediaList(self, folderName='', cacheType=CACHE_TYPE_MEMORY):

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        opener.addheaders = self.getHeadersList()

        if (self.version == self.OWNCLOUD_V6):
            url = self.protocol + self.domain +'/index.php/apps/files?' + urllib.urlencode({'dir' : folderName})
        else:
            if folderName == 'ES':
                url = self.protocol + self.domain + '/ocs/v1.php/apps/files_external/api/v1/mounts?format=json'
            elif folderName == 'SL':
                url = self.protocol + self.domain + '/ocs/v1.php/apps/files_sharing/api/v1/shares?format=json&shared_with_me=false'
            else:
                url = self.protocol + self.domain +'/index.php/apps/files/ajax/list.php?'+ urllib.urlencode({'dir' : folderName})+'&sort=name&sortdirection=asc'



        # if action fails, validate login
        try:
            response = opener.open(url)
        except urllib2.URLError, e:
            self.login()
            opener.addheaders = self.getHeadersList()

            try:
                response = opener.open(url)
            except urllib2.URLError, e:
                xbmc.log(self.addon.getAddonInfo('name') + ': ' + str(e), xbmc.LOGERROR)
                return
        response_data = response.read()
        response.close()


        mediaFiles = []
        # parsing page for files
        if (self.version == self.OWNCLOUD_V6):

            for r in re.finditer('\<tr data\-id\=.*?</tr>' ,response_data, re.DOTALL):
                entry = r.group()
                for q in re.finditer('data\-id\=\"([^\"]+)\".*?data\-file\=\"([^\"]+)\".*?data\-type\=\"([^\"]+)\".*?data\-mime\=\"([^\/]+)\/' ,entry, re.DOTALL):
                    fileID,fileName,contentType,fileType = q.groups()

                    try:
#                            fileName = unicode(fileName, "unicode-escape")
                            fileName = fileName.decode('unicode-escape')
                            fileName = fileName.encode('utf-8')
                    except:
                            pass

                    #fileName = unicode(fileName, "unicode-escape")
                    # Undo any urlencoding before displaying the files (should also make the folders accessible)
                    #fileName = urllib.unquote(fileName)

                    if fileType == 'video':
                        fileType = self.MEDIA_TYPE_VIDEO
                    elif fileType == 'audio':
                        fileType = self.MEDIA_TYPE_MUSIC
                    elif fileType == 'image':
                        fileType = self.MEDIA_TYPE_PICTURE


                    if contentType == 'dir':
                        mediaFiles.append(package.package(0,folder.folder(folderName+'/'+fileName,fileName)) )
                    else:
                        thumbnail = self.protocol + self.domain +'/index.php/core/preview.png?file='+folderName+ '/'+fileName + '&x=50&y=50'+'|' + self.getHeadersEncoded()

                        mediaFiles.append(package.package(file.file(fileName, fileName, fileName, fileType, '', thumbnail),folder.folder(folderName,folderName)) )

            return mediaFiles
        else:
            for r in re.finditer('\[\{.*?\}\]' ,response_data, re.DOTALL):
                entry = r.group()

                for s in re.finditer('\{.*?\}' ,entry, re.DOTALL):
                    item = s.group()

                    fileID = ''
                    fileName = ''
                    fileType = ''
                    contentType = ''
                    etag = ''
                    thumbnail = ''
                    if folderName == 'ES':
                        for q in re.finditer('\"type\"\:\"([^\"]+)\"' ,
                                         item, re.DOTALL):
                            contentType = q.group(1)
                            break
                        for q in re.finditer('\"name\"\:\"([^\"]+)\"' ,
                                         item, re.DOTALL):
                            fileName = q.group(1)
                            break

                    elif folderName == 'SL':
                        for q in re.finditer('\"file_source\"\:\"([^\"]+)\"' ,
                                         item, re.DOTALL):
                            fileID = q.group(1)
                            break

                        for q in re.finditer('\"file_target\"\:\"([^\"]+)\"' ,
                                         item, re.DOTALL):
                            fileName = q.group(1)
                            break
                        for q in re.finditer('\"mimetype\"\:\"([^\/]+)\/' ,
                                         item, re.DOTALL):
                            fileType = q.group(1)
                            break
                        for q in re.finditer('\"item_type\"\:\"([^\"]+)\"' ,
                                         item, re.DOTALL):
                            contentType = q.group(1)
                            break

                        if fileType == 'video\\':
                            fileType = self.MEDIA_TYPE_VIDEO
                        elif fileType == 'audio\\':
                            fileType = self.MEDIA_TYPE_MUSIC
                        elif fileType == 'image\\':
                            fileType = self.MEDIA_TYPE_PICTURE



                    else:
                        for q in re.finditer('\"id\"\:\"([^\"]+)\"' ,
                                         item, re.DOTALL):
                            fileID = q.group(1)
                            break
                        for q in re.finditer('\"name\"\:\"([^\"]+)\"' ,
                                         item, re.DOTALL):
                            fileName = q.group(1)
                            break
                        for q in re.finditer('\"mimetype\"\:\"([^\/]+)\/' ,
                                         item, re.DOTALL):
                            fileType = q.group(1)
                            break
                        for q in re.finditer('\"type\"\:\"([^\"]+)\"' ,
                                         item, re.DOTALL):
                            contentType = q.group(1)
                            break
                        for q in re.finditer('\"etag\"\:\"([^\"]+)\"' ,
                                         item, re.DOTALL):
                            etag = q.group(1)
                            break
                            thumbnail = self.protocol + self.domain +'/index.php/core/preview.png?file='+str(folderName)+ '/'+str(fileName) + '&c='+str(etag)+'&x=50&y=50&forceIcon=0'+'|' + self.getHeadersEncoded()

                        if fileType == 'video\\':
                            fileType = self.MEDIA_TYPE_VIDEO
                        elif fileType == 'audio\\':
                            fileType = self.MEDIA_TYPE_MUSIC
                        elif fileType == 'image\\':
                            fileType = self.MEDIA_TYPE_PICTURE

#                        fileName = unicode(fileName, "unicode-escape")
                    try:
#                            fileName = unicode(fileName, "unicode-escape")
                            fileName = fileName.decode('unicode-escape')
                            fileName = fileName.encode('utf-8')
                    except:
                            pass
#                        # Undo any urlencoding before displaying the files (should also make the folders accessible)
#                        fileName = urllib.unquote(fileName)
                    if contentType == 'dir':

                            mediaFiles.append(package.package(0,folder.folder(folderName+'/'+fileName,fileName)) )
                    else:

                            mediaFiles.append(package.package(file.file(fileName, fileName, fileName, fileType, '', thumbnail),folder.folder(folderName,folderName)) )

            return mediaFiles


    ##
    # retrieve a playback url
    #   returns: url
    ##
    def getPlaybackCall(self, playbackType, package):
        if playbackType == self.CACHE_TYPE_AJAX:
            params = urllib.urlencode({'files': package.file.id, 'dir': package.folder.id})
            return self.protocol + self.domain +'/index.php/apps/files/ajax/download.php?'+params + '|' + self.getHeadersEncoded()
        else:
            return self.protocol + self.domain +'/index.php/apps/files/download/'+urllib.quote(package.folder.id)+ '/'+urllib.quote(package.file.id) + '|' + self.getHeadersEncoded()

    ##
    # retrieve a media url
    #   returns: url
    ##
    def getMediaCall(self, package):
#        try:
#            fileID =  unicode(package.file.id,'utf-8')
#        except:
        fileID = package.file.id

#        try:
#            folderID =  unicode(package.folder.id,'utf-8')
#        except:
        folderID = package.folder.id



        if package.file.type == package.file.VIDEO:
#            return self.PLUGIN_URL+'?mode=video&instance='+self.instanceName+'&filename='+unicode(package.file.id,'utf-8')+'&title='+unicode(package.file.title,'utf-8')+'&directory=' + unicode(package.folder.id,'utf-8')
            return self.PLUGIN_URL+'?mode=video&instance='+self.instanceName+'&filename='+fileID+'&title='+fileID+'&directory=' + folderID
        elif package.file.type == package.file.AUDIO:
#            return self.PLUGIN_URL+'?mode=audio&instance='+self.instanceName+'&filename='+unicode(package.file.id,'utf-8')+'&title='+unicode(package.file.title,'utf-8')+'&directory=' + unicode(package.folder.id,'utf-8')
            return self.PLUGIN_URL+'?mode=audio&instance='+self.instanceName+'&filename='+fileID+'&title='+fileID+'&directory=' + folderID
        else:
#            return self.PLUGIN_URL+'?mode=audio&instance='+self.instanceName+'&filename='+unicode(package.file.id,'utf-8')+'&title='+unicode(package.file.title,'utf-8')+'&directory=' + unicode(package.folder.id,'utf-8')
            return self.PLUGIN_URL+'?mode=audio&instance='+self.instanceName+'&filename='+fileID+'&title='+fileID+'&directory=' + folderID


    ##
    # retrieve a directory url
    #   returns: url
    ##
    def getDirectoryCall(self, folder):
#                        videos[fileName] = {'url':  'plugin://plugin.video.owncloud?mode=folder&directory=' + urllib.quote_plus(folderName+'/'+fileName), 'mediaType': self.MEDIA_TYPE_FOLDER}

#        try:
#            return self.PLUGIN_URL+'?mode=folder&instance='+self.instanceName+'&directory=' + unicode(folder.id,'utf-8')
#        except:
            return self.PLUGIN_URL+'?mode=folder&instance='+self.instanceName+'&directory=' + folder.id



