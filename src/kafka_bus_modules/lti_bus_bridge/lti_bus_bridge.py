'''
Created on Jun 2, 2015

@author: paepcke
'''
import json
import logging
from this import s

from kafka_bus_python.kafka_bus import BusAdapter, SyncCallTimedOut

import tornado.httpserver
import tornado.web


#from tornado.web import RequestHandler
#import tornado.web
#from  tornado.httpserver import HTTPServer
class LtiBusBridgeProducer(tornado.web.RequestHandler):
    '''
    If you run it on your own server, and you have
    a sandbox course on Lagunita, you can create 
    an LTI component as described at 
    http://edx.readthedocs.org/projects/edx-partner-course-staff/en/latest/exercises_tools/lti_component.html
    '''

    LTI_LISTEN_PORT          = 6005
    SYNCHRONOUS_CALL_TIMEOUT = 40 # seconds
    
    COMMON_LTI_CUSTOM_KEYS   = ['custom_topic_name',
                                'custom_synchronous_call']

    # Needs to be a class variable so
    # that only the first instance does
    # logging setup:
    loggingInitialized = False

    def __init__(self,
                 application,
                 request,
                 loggingLevel=logging.DEBUG,
                 logFile=None,
):
        super(LtiBusBridgeProducer, self).__init__(application, request)
        self.setupLogging(loggingLevel, logFile)
        self.bus = BusAdapter()

    def get(self):
        getParms = self.request.arguments
        self.write("<html><body>GET method was called: %s.</body></html>" %str(getParms))


    def post(self):
        '''
        Override the post() method. The
        associated form is available as a 
        dict in self.request.arguments.
        '''
        postBodyForm = self.request.arguments
        #print(str(postBody))
        #self.write('<!DOCTYPE html><html><body><script>document.getElementById("ltiFrame-i4x-DavidU-DC1-lti-2edb4bca1198435cbaae29e8865b4d54").innerHTML = "Hello iFrame!"</script></body></html>"');    

        self.publishRequestToBus(postBodyForm)

    def publishRequestToBus(self, postBodyForm):

        paramNames = postBodyForm.keys()
        paramNames.sort()

        # Pull out the LTI built-in, and custom parameters
        # that may be common with calls to all modules:
        # The [0]'s below: LTI delivers the values of its
        # key/value pairs as an array, so our get() defaults
        # are arrays as well, and the [0] will always work:
        course_display_name = postBodyForm.get('context_id', ['null'])[0]
        ltiUid              = postBodyForm.get('user_id', ['null'])[0]
        topicName           = postBodyForm.get('custom_topic_name', [None])[0]
        synchronousCall     = postBodyForm.get('custom_synchronous_call', [False])[0]
        if topicName is None:
            self.logError('Invocation from LMS with missing bus topic name.')
            self.writeToLtiDisplay('<b>Error</b>: your LTI was not set up to pass the required topic name to the LTI-->SchoolBus bridge.')
            return

        # Every module may have additional custom parameters
        # that were added when the respective LTI was registered
        # with the LMS:
        
        # Build the payload (i.e. msg content) dict, initializing with the 
        # key/value pairs that every bus module receives:
        payLoadDict = {'course_display_name' : course_display_name,
                       'lti_id' : ltiUid}
        
        # Now add the custom ones:
        for (key, value) in postBodyForm.items():
            if key.startswith('custom_') and key not in LtiBusBridgeProducer.COMMON_LTI_CUSTOM_KEYS:
                # Found a module-specific custom parm.
                # The [0] is again b/c LTI values are 
                # passed in arrays;
                # Strip the leading 'custom_':
                payLoadDict[key[len('custom_'):]] = value[0]
        
        try:
            respStr = self.bus.publish(payLoadDict,
                                       topicName=topicName,
                                       sync=synchronousCall,
                                       timeout=LtiBusBridgeProducer.SYNCHRONOUS_CALL_TIMEOUT)
        except SyncCallTimedOut:
            respStr = '<b>Error:</b>: No response within %d seconds when querying on topic %s' % (LtiBusBridgeProducer.SYNCHRONOUS_CALL_TIMEOUT, topicName)
        if synchronousCall:
            self.writeToLtiDisplay(str(respStr))

    def writeToLtiDisplay(self, htmlTxt):
        
        self.write('<html><body>')
        self.write(htmlTxt)
        self.write("</body></html>")
        
    @classmethod  
    def makeApp(self):
        '''
        Create the tornado application, making it 
        called via http://myServer.stanford.edu:<port>/dill
        '''
        application = tornado.web.Application([
            (r"/schoolBusBridge", LtiBusBridgeProducer),
            ])
        return application
    
    def setupLogging(self, loggingLevel, logFile):
        
        if LtiBusBridgeProducer.loggingInitialized:
            # Remove previous file or console handlers,
            # else we get logging output doubled:
            LtiBusBridgeProducer.logger.handlers = []
            
        # Set up logging:
        # A logger named SchoolBusLog:
        LtiBusBridgeProducer.logger = logging.getLogger('SchoolBusLog')
        LtiBusBridgeProducer.logger.setLevel(loggingLevel)
        
        # A msg formatter that shows datetime, logger name, 
        # the log level of the message, and the msg.
        # The datefmt=None causes ISO8601 to be used:
        
        formatter = logging.Formatter(fmt='%(asctime)s-%(name)s-%(levelname)s: %(message)s',datefmt=None)
        
        # Create file handler if requested:
        if logFile is not None:
            handler = logging.FileHandler(logFile)
        else:
            # Create console handler:
            handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.setLevel(loggingLevel)
#         # create formatter and add it to the handlers
#         formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#         fh.setFormatter(formatter)
#         ch.setFormatter(formatter)
        # Add the handler to the logger
        LtiBusBridgeProducer.logger.addHandler(handler)
        
        LtiBusBridgeProducer.loggingInitialized = True


    def logWarn(self, msg):
        LtiBusBridgeProducer.logger.warn(msg)

    def logInfo(self, msg):
        LtiBusBridgeProducer.logger.info(msg)
     
    def logError(self, msg):
        LtiBusBridgeProducer.logger.error(msg)

    def logDebug(self, msg):
        LtiBusBridgeProducer.logger.debug(msg)
    

if __name__ == "__main__":
    application = LtiBusBridgeProducer.makeApp()
    # We need an SSL capable HTTP server:
    # For configuration without a cert, add "cert_reqs"  : ssl.CERT_NONE
    # to the ssl_options (though I haven't tried it out.):

    http_server = tornado.httpserver.HTTPServer(application,
                                                ssl_options={"certfile": "/home/paepcke/.ssl/MonoCertSha2Expiration2018/mono_stanford_edu_cert.cer",
                                                             "keyfile" : "/home/paepcke/.ssl/MonoCertSha2Expiration2018/mono.stanford.edu.key"
    })
    # Run the app on its port:
    # Instead of application.listen, as in non-SSL
    # services, the http_server is told to listen:
    #*****application.listen(7071)
    http_server.listen(LtiBusBridgeProducer.LTI_LISTEN_PORT)
    tornado.ioloop.IOLoop.instance().start()        
        