'''
Created on Jun 5, 2015

@author: paepcke
'''
import datetime
import json
import os
import tornado
from tornado.websocket import WebSocketHandler
from tornado.httpserver import HTTPServer;

class Js2SchoolBus(WebSocketHandler):

    PORT            = 6070

    LOG_LEVEL_NONE  = 0
    LOG_LEVEL_ERR   = 1
    LOG_LEVEL_INFO  = 2
    LOG_LEVEL_DEBUG = 3

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

        # Interval between logging the sending of
        # the heartbeat:
        self.latestHeartbeatLogTime = None

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
            if requestDict['req'] == 'keepAlive':
                # Could return live-ping here! But shouldn't
                # need to, because sending the '.' periodically
                # during long ops is enough. Sending that dot
                # will cause the browser to send its keep-alive:
                return
            else:
                self.logInfo("request received: %s" % str(message))
        except Exception as e:
            self.writeError("Bad JSON in request received at server: %s" % `e`)

        self.logDebug("About to fork thread for request '%s'" % str(requestDict))

    def logInfo(self, msg):
        if self.loglevel >= Js2SchoolBus.LOG_LEVEL_INFO:
            print(str(datetime.datetime.now()) + ' info: ' + msg)

    def logErr(self, msg):
        if self.loglevel >= Js2SchoolBus.LOG_LEVEL_ERR:
            print(str(datetime.datetime.now()) + ' error: ' + msg)

    def logDebug(self, msg):
        if self.loglevel >= Js2SchoolBus.LOG_LEVEL_DEBUG:
            print(str(datetime.datetime.now()) + ' debug: ' + msg)
            
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
