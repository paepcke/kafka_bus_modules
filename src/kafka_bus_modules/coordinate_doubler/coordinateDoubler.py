'''
Created on Jun 12, 2015

@author: paepcke
'''
import functools
import json
import logging

from kafka_bus_python.kafka_bus import BusAdapter


class CoordinateDoubler(object):
    '''
    classdocs
    '''
    
    module_topic   = 'coord_doubling'

    def __init__(self, topic=None):
        '''
        Instantiated for each request coming in on the bus:
        '''
        if topic is None:
            topic = CoordinateDoubler.module_topic
            
        # The following statement is needed only 
        # if your callback is a method (rather than a top 
        # level function). That's because Python methods
        # take 'self' as a first argument, while the Bus 
        # expects a function that just takes topicName, msgText, and msgOffset.
        # The following statement creates a function wrapper around 
        # our callback method that has the leading 'self' parameter built 
        # in. The process is called function currying:
        
        self.requestDeliveryMethod = functools.partial(self.requestCoordinateDoubling)        
        
        # Create a BusAdapter instance:
        
        self.bus = BusAdapter(loggingLevel=logging.INFO)

        # Tell the bus that you are interested in the topic 'example_use',
        # and want callbacks to self.exampleDeliveryMethod whenever
        # a message arrives:
        
        self.bus.subscribeToTopic(topic, self.requestDeliveryMethod)
        
        self.bus.logInfo('Starting bus module CoordinateDoubler')
        
        # Now we do nothing. In a production system you 
        # would do something useful here:
        
        while True:
            # do anything you like
            self.bus.waitForMessage(CoordinateDoubler.module_topic)


    def requestCoordinateDoubling(self, topicName, msgText, msgOffset):
        '''
        This method is called whenever a message in topic
        CoordinateDoubler.module_topic is published by anyone on the bus.
        The msgText should have the JSON format:
        
        
            {'id'      : 'abcd',
             'type'    : 'req',
             'content' : {'cursorX' : '123', 'cursorX' : '456'},
             'time'    : '2015-05-27T18:12:22.706204',
            }
            
        Note that the publish() method on the publisher side will have
        taken care of the id, type, and time fields.           
        
        The request key is caller-generated. The response message
        will have that same key in its resp_key field. Used by
        caller to identify its response.

        Response will be of the form:
            {'id'          : 'abcd',
             'type'        : 'resp',
             'status'      : 'OK'
             'content'     : '{"cursorXx2" : "246", "cursorYx2" : "912"}'
            }
            
        Or, in case of error:
            {'id'          : 'abcd',
             'type'        : 'resp',
             'status'      : 'ERROR'
             'content'     : '<error msg'>
            }
            
        Again, when constructing our response below, we only need to
        pass the 'content', msgId, and msgType values to publish(); 
        the time is added by publish().
        
        :param topicName: name of topic to which the arriving msg belongs: always learner_homework_history
        :type topicName: string
        :param msgText: text part of the message. JSON as specified above.
        :type msgText: string
        :param msgOffset: position of message in the topic's message history
        :type msgOffset: int
        '''
        try:
            # Import the message's content field into a dict:
            msgDict = json.loads(msgText)
            self.bus.logDebug("CoordDoupler: req %s" % str(msgDict))
        except ValueError:
            self.bus.logError('Received msg with invalid cursor coordinate JSON info: %s' % str(msgText))
            return

        # Must have the msg ID to use in our response:
        try:
            reqId = msgDict['id']
        except KeyError:
            self.bus.returnError('NULL', "Error: message id not provided in an incoming request.")
            self.bus.logError("Message ID not provided in %s" % str(msgDict))
            return

        # Must have a learner type == 'req'
        try:
            reqKey = msgDict['type']
            if reqKey != 'req':
                # Not a request, do nothing:
                return
        except KeyError:
            self.bus.returnError(reqId, "Error: message type not provided in %s" % str(msgDict))
            self.bus.logError('Received msg without a type field: %s' % str(msgText))
            return
        
        # The content field should be legal JSON; make a
        # dict from it:
        try:
            contentDict = json.loads(msgDict['content'])
        except KeyError:
            self.bus.returnError(reqKey, "Error: no content field provided in %s" % str(msgDict))
            self.bus.logError('Received msg without a content field: %s' % str(msgText))
            return
        except ValueError:
            self.bus.returnError(reqKey, "Error: content field did not contain proper JSON %s" % str(msgDict))
            self.bus.logError('Error: content field did not contain proper JSON : %s' % str(msgText))
            return

        try:
            (cursorX, cursorY) = (int(contentDict['cursorX']), int(contentDict['cursorY']))
        except ValueError:
            self.bus.returnError(reqId, "Error: cursorX and cursorY JSON not (properly) provided in %s" % str(msgDict))
            self.bus.logError('Received msg bad cursorX/cursorY information: %s' % str(msgText))

        # Note that we pass the message type 'resp' 
        # to publish(), and that we specify that the
        # msg ID is to be the same as the incoming request.
        
        self.bus.publish('{"cursorXx2" : "%s", "cursorYx2" : "%s"}' % (2*cursorX, 2*cursorY),
                         CoordinateDoubler.module_topic,
                         msgType='resp',
                         msgId=reqId)



if __name__ == '__main__':
    try:
        coordinateDoubler = CoordinateDoubler()
    finally:
        try:
            coordinateDoubler.close()
        except:
            pass
    