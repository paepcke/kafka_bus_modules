'''
Created on May 27, 2015

@author: paepcke
'''
import datetime
import json
import unittest

from kafka_bus_python.kafka_bus import BusAdapter


class TestLearnerHomeworkHistory(unittest.TestCase):

    def setUp(self):
        self.bus = BusAdapter(kafkaHost='localhost')

    def tearDown(self):
        self.bus.close()        

    def testReceiveRequest(self):
        msg = json.dumps({'req_key' : 'abcd',
                          'request' : {'lti_id': '0925c14e89bda0c0c3ad41e36335674b',
                                       'course_id' : ''},
                          'time'    : datetime.datetime.utcnow().isoformat()
                          }) 
        self.bus.publish(msg, 'learner_homework_history')


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testReceiveRequest']
    unittest.main()