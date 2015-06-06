'''
Created on May 27, 2015

@author: paepcke
'''
import datetime
import functools
import json
import unittest

from kafka_bus_python.kafka_bus import BusAdapter


class TestLearnerHomeworkHistory(unittest.TestCase):

    LEARNER_ACTIVITY_TOPIC = 'learner_homework_history' 

    def setUp(self):
        self.bus = BusAdapter(kafkaHost='localhost')
        self.resultDelivery = functools.partial(self.resultDeliveryMethod)

    def tearDown(self):
        self.bus.close()  
        
    def resultDeliveryMethod(self, topicName, rawResult, msgOffset):
        self.topicName = topicName
        self.rawResult = rawResult
        self.msgOffset = msgOffset
              

    def testReceiveRequest(self):
        msg = json.dumps({'req_key' : 'abcd',
                          'content' : {'lti_id': '0925c14e89bda0c0c3ad41e36335674b',
                                       'course_id' : ''},
                          'time'    : datetime.datetime.utcnow().isoformat()
                          })
        self.bus.subscribeToTopic(self.LEARNER_ACTIVITY_TOPIC, 
                                  deliveryCallback=self.resultDelivery)
        
        self.bus.publish(msg, self.LEARNER_ACTIVITY_TOPIC)
        self.assertTrue(self.bus.waitForMessage(self.LEARNER_ACTIVITY_TOPIC, 3.0), 
                        'No reply from learner_homework_history') # wait for at most 3sec
        self.assertEqual(self.topicName, TestLearnerHomeworkHistory.LEARNER_ACTIVITY_TOPIC)
        self.rawResult.startswith('{"status": "OK", "content": [{"percent_grade":')

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testReceiveRequest']
    unittest.main()