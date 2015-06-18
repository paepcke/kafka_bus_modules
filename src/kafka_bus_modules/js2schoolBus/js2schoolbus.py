'''
Created on Jun 5, 2015

@author: paepcke
'''
import datetime
import json
import logging
import os
import socket
from subprocess import CalledProcessError
import subprocess

from kafka_bus_python.kafka_bus import BusAdapter
import tornado
from tornado.httpserver import HTTPServer
from tornado.websocket import WebSocketHandler


class Js2SchoolBus(WebSocketHandler):

    PORT            = 6070

    LOG_LEVEL_NONE  = 0
    LOG_LEVEL_ERR   = 1
    LOG_LEVEL_INFO  = 2
    LOG_LEVEL_DEBUG = 3
    
    firstInstance = True

    def __init__(self, application, request, testing=False ):
        '''
        Invoked when browser accesses this server via ws://...
        Register this handler instance in the handler list.

        :param application: Application object that defines the collection of handlers.
        :type application: tornado.web.Application
        :param request: a request object holding details of the incoming request
        :type request:HTTPRequest.HTTPRequest
        :param kwargs: dict of additional parameters for operating this service.
        :type kwargs: dict
        '''
        if not testing:
            super(Js2SchoolBus, self).__init__(application, request)
            self.defaultDb = 'Edx'
        else:
            self.defaultDb = 'unittest'
        self.testing = testing
        self.request = request;

        #self.loglevel = Js2SchoolBus.LOG_LEVEL_DEBUG
        self.loglevel = Js2SchoolBus.LOG_LEVEL_INFO
        #self.loglevel = Js2SchoolBus.LOG_LEVEL_NONE

        # Get and remember the fully qualified domain name
        # of this server, *as seen from the outside*, i.e.
        # from the WAN, outside any router that this server
        # might be behind:
        self.FQDN = self.getFQDN()

        self.bus = BusAdapter(loggingLevel=logging.WARN)
        #self.bus = BusAdapter(loggingLevel=logging.DEBUG)

        # Interval between logging the sending of
        # the heartbeat:
        self.latestHeartbeatLogTime = None
        
        if Js2SchoolBus.firstInstance:
            self.bus.logInfo('Starting schoolbus module Js2SchoolBus')
            Js2SchoolBus.firstInstance = False

    def allow_draft76(self):
        '''
        Allow WebSocket connections via the old Draft-76 protocol. It has some
        security issues, and was replaced. However, Safari (i.e. e.g. iPad)
        don't implement the new protocols yet. Overriding this method, and
        returning True will allow those connections.
        '''
        return True

    def open(self): #@ReservedAssignment
        '''
        Called by WebSocket/tornado when a client connects. Method must
        be named 'open'
        '''
        self.logDebug("Open called")

    def on_message(self, message):
        '''
        Connected browser requests action: "<actionType>:<actionArg(s)>,
        where actionArgs is a single string or an array of items.

        :param message: message arriving from the browser
        :type message: string
        '''
        #print message
        try:
            requestDict = json.loads(message)
            if requestDict['type'] == 'keepAlive':
                # Could return live-ping here! But shouldn't
                # need to, because sending the '.' periodically
                # during long ops is enough. Sending that dot
                # will cause the browser to send its keep-alive:
                return
            else:
                self.logDebug("js2schoolbus: request received: %s" % str(message))
                syncCall = requestDict.get('sync', False)
                try: 
                    msgId = requestDict['id']
                except KeyError:
                    self.writeError('Request msg from browser did not include a message id: %s' % str(message))
                    self.bus.logError('Request msg from browser did not include a message id: %s' % str(message))
                    return
                
                if (syncCall):
                    res = self.bus.publish(requestDict['content'], requestDict['topic'], sync=True, msgId=msgId)
                    self.bus.logDebug("js2schoolbus: about to return result %s" % str(res))
                    self.write_message(json.dumps({'id'      : msgId,
                                                   'topic'   : requestDict['topic'],
                                                   'type'    : 'resp',
                                                   'time'    : datetime.datetime.now().isoformat(), 
                                                   'content' : res,
                                                   }))
                else:
                    self.bus.publish(requestDict['content'], requestDict['topic'], sync=False, msgId=msgId)
                    return

        except Exception as e:
            self.writeError("Bad JSON in request received at server: %s" % `e`)
            self.logDebug("Bad request: '%s'" % str(message))


    def writeError(self, msg):
        '''
        Writes a response to the JS running in the browser
        that indicates an error. Result action is "error",
        and "args" is the error message string:

        :param msg: error message to send to browser
        :type msg: String
        '''
        self.logDebug("Sending err to browser: %s" % msg)
        if not self.testing:
            errMsg = '{"type" : "js2schoolBusAdmin", "content", "args" : "%s"}' % msg.replace('"', "`")
            try:
                self.write_message(errMsg)
            except IOError as e:
                self.logErr('IOError while writing error to browser; msg attempted to write; "%s" (%s)' % (msg, `e`))


    def logInfo(self, msg):
        if self.loglevel >= Js2SchoolBus.LOG_LEVEL_INFO:
            print(str(datetime.datetime.now()) + ' info: ' + msg)

    def logErr(self, msg):
        if self.loglevel >= Js2SchoolBus.LOG_LEVEL_ERR:
            print(str(datetime.datetime.now()) + ' error: ' + msg)

    def logDebug(self, msg):
        if self.loglevel >= Js2SchoolBus.LOG_LEVEL_DEBUG:
            print(str(datetime.datetime.now()) + ' debug: ' + msg)
            
    def getFQDN(self):
        '''
        Obtain true fully qualified domain name of server, as
        seen from the 'outside' of any router behind which the
        server may be hiding. Strategy: use shell cmd "wget -q -O- icanhazip.com"
        to get IP address as seen from the outside. Then use
        gethostbyaddr() to do reverse DNS lookup.

        @return: this server's fully qualified IP name.
        @rtype: string
        @raise ValueError: if either the WAN IP lookup, or the subsequent
            reverse DNS lookup fail.
        '''

        try:
            ip = subprocess.check_output(['wget', '-q', '-O-', 'icanhazip.com'])
        except CalledProcessError:
            # Could not get the outside IP address. Fall back
            # on using the FQDN obtained locally:
            return socket.getfqdn()

        try:
            fqdn = socket.gethostbyaddr(ip.strip())[0]
        except socket.gaierror:
            raise("ValueError: could not find server's fully qualified domain name from IP address '%s'" % ip.string())
        except Exception as e:
            raise("ValueError: could not find server's fully qualified domain: '%s'" % `e`)
        return fqdn
            
            
    @classmethod
    def getCertAndKey(self):
        '''
        Return a 2-tuple with full paths, respectively to
        the SSL certificate, and private key.
        To find the SSL certificate location, we assume
        that it is stored in dir '.ssl' in the current
        user's home dir.
        We assume the cert file either ends in .cer, or
        in .crt, and that the key file ends in .key.
        The first matching files in the .ssl directory
        are grabbed.

        @return: two-tuple with full path to SSL certificate, and key files.
        @rtype: (str,str)
        @raise ValueError: if either of the files are not found.

        '''
        homeDir = os.path.expanduser("~")
        sslDir = '%s/.ssl/' % homeDir
        try:
            certFileName = next(fileName for fileName in os.listdir(sslDir)
	                               if fileName.endswith('.cer') or fileName.endswith('.crt'))
        except StopIteration:
            raise(ValueError("Could not find ssl certificate file in %s" % sslDir))

        try:
            privateKeyFileName = next(fileName for fileName in os.listdir(sslDir)
	                                     if fileName.endswith('.key'))
        except StopIteration:
            raise(ValueError("Could not find ssl private key file in %s" % sslDir))
        return (os.path.join(sslDir, certFileName),
                os.path.join(sslDir, privateKeyFileName))
            
if __name__ == '__main__':

    application = tornado.web.Application([(r"/js2schoolBus", Js2SchoolBus),])
    #application.listen(Js2SchoolBus.PORT)

    (certFile,keyFile) = Js2SchoolBus.getCertAndKey()
    sslArgsDict = {'certfile' : certFile,
                   'keyfile'  : keyFile}

    http_server = tornado.httpserver.HTTPServer(application,ssl_options=sslArgsDict)

    application.listen(Js2SchoolBus.PORT, ssl_options=sslArgsDict)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except Exception as e:
        print("Error inside Tornado ioloop; continuing: %s" % `e`)
