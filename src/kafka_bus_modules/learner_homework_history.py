'''
Created on May 26, 2015

@author: paepcke
'''
import argparse
import cStringIO
import datetime
import functools
import getpass
import json
import os
import sys
import time

from kafka_bus_python.kafka_bus import BusAdapter
from pymysql_utils.pymysql_utils import MySQLDB


class LearnerHomeworkHistory(object):
    '''
    classdocs
    '''
    
    module_topic   = 'learner_homework_history'
    kafka_bus_host = 'mono.stanford.edu'

    def __init__(self, topic=None, user='dataman', passwd=''):
        '''
        Constructor
        '''
        if topic is None:
            topic = LearnerHomeworkHistory.module_topic
            
        self.mysqldb = MySQLDB(host='127.0.0.1', port=5555, user=user, passwd=passwd, db='Edx')
        
        # The following statement is needed only 
        # if your callback is a method (rather than a top 
        # level function). That's because Python methods
        # take 'self' as a first argument, while the Bus 
        # expects a function that just takes topicName, msgText, and msgOffset.
        # The following statement creates a function wrapper around 
        # our callback method that has the leading 'self' parameter built 
        # in. The process is called function currying:
        
        self.requestDeliveryMethod = functools.partial(self.requestHomeworkHistory)        
        
        # Create a BusAdapter instance, telling it that its
        # server(s) are on machine mono.stanford.edu:
        
        self.bus = BusAdapter(kafkaHost=LearnerHomeworkHistory.kafka_bus_host)

        # Tell the bus that you are interested in the topic 'example_use',
        # and want callbacks to self.exampleDeliveryMethod whenever
        # a message arrives:
        
        self.bus.subscribeToTopic(topic, self.requestDeliveryMethod)
        
        # Now we do nothing. In a production system you 
        # would do something useful here:
        
        while True:
            # do anything you like
            self.bus.waitForMessage(LearnerHomeworkHistory.module_topic)

    def requestHomeworkHistory(self, topicName, msgText, msgOffset):
        '''
        This method is called whenever a message in topic
        'learner_homework_history' is published by anyone on the bus.
        The msgText should have the JSON format:
        
            {'req_key' : 'abcd'
             'content' : {'lti_id': '0925c14e89bda0c0c3ad41e36335674b',
                          'course_id' : ''},
             'time'    : '2015-05-27T18:12:22.706204',
                          }           
        
        The request key is caller-generated. The response message
        will have that same key in its resp_key field. Used by
        caller to identify its response.
        
        The request field contains the request-specific JSON.
        
        CourseId may be empty, or missing, in which case stats for the given
        learner for all classes is returned.
        
        Hint: in Python you get the ISO formatted time stamp string via:
        datetime.datetime.utcnow().isoformat()
        
        Response will be of the form:
            {'resp_key'    : 'abcd',
             'status'      : 'OK'
             'content'     : *****
            }
            
        Or, in case of error:
            {'resp_key'    : 'abcd',
             'status'      : 'ERROR'
             'content'     : '<error msg'>
            }
        
        :param topicName: name of topic to which the arriving msg belongs: always learner_homework_history
        :type topicName: string
        :param msgText: text part of the message. JSON as specified above.
        :type msgText: string
        :param msgOffset: position of message in the topic's message history
        :type msgOffset: int
        '''
        try:
            # Import the JSON payload into a dict:
            msgDict = json.loads(msgText)
        except ValueError as e:
            self.bus.logError('Received msg with invalid JSON: %s (%s)' % (msgText, `e`))
            return

        # Must have a learner req_key:
        try:
            reqKey = msgDict['request']['req_key']
        except KeyError:
            self.returnError("Error: req_key not provided in %s" % str(msgDict), 'NULL')
            return
        
        # Must have a learner LTI ID:
        try:
            ltiId = msgDict['request']['lti_id']
        except KeyError:
            self.returnError("Error: lti not provided in %s" % str(msgDict), reqKey)
            return
            
        # May have a courseId:
        try:
            courseId = msgDict['request']['course_id']
        except KeyError:
            courseId = None
        
        # Get an array of dicts, each dict being one MySQL record:
        #    first_submit          [a <datetime obj>]
        #    last_submit           [a <datetime obj>]
        #    course_display_name
        #    resource_display_name 
        #    num_attempts
        #    percent_grade
        
        resultArr = self.executeLearnerQuery(ltiId, courseId)
        # print (str(resultArr))
        
        respJSON = self.buildResponse(resultArr, reqKey)
        self.bus.publish(respJSON, LearnerHomeworkHistory.module_topic)
        
    def executeLearnerQuery(self, ltiLearnerId, courseId=None):
        
        if courseId is None or len(courseId) == 0:
            courseId = '%' 
            
        # Get anon_screen_name in separate query. This
        # will speed the subsequent main query up tremendously:
        try:
            anonScreenName = self.mysqldb.query("SELECT idExt2Anon('%s');" % ltiLearnerId).next()
        except Exception as e:
            raise ValueError('Could not convert %s to anon_screen_name (%s)' % (ltiLearnerId, `e`))
        
        homeworkQuery = "SELECT first_submit," +\
                        "last_submit," +\
    			        "course_display_name," +\
    			        "resource_display_name," +\
    			        "module_id," +\
    			        "num_attempts," +\
    			        "percent_grade " +\
    			   "FROM ActivityGrade " +\
    			  "WHERE anon_screen_name = '%s' " % anonScreenName +\
                    "AND course_display_name LIKE '%s' " % courseId +\
    			    "AND module_type = 'problem';"
        resIt = self.mysqldb.query(homeworkQuery)
        resultArr = []
        for res in resIt:
            resultArr.append(res)
        return resultArr
    
    def buildResponse(self, arrOfDicts, reqKey):
        responseMsg = {'resp_key'   : reqKey,
                       'status'     : 'OK',
                       'content'    : arrOfDicts,
                       'time'       : datetime.datetime.utcnow().isoformat()
                       }
        return self.makeJSON(responseMsg)
                       
    def returnError(self, req_key, errMsg):
        errMsg = {'resp_key'    : req_key,
                  'status'      : 'ERROR',
                  'content'     : errMsg
                 }
        errMsgJSON = self.makeJSON(errMsg)
        self.bus.publish(errMsgJSON, LearnerHomeworkHistory.module_topic)

    def makeJSON(self, pythonStructure):
        io = cStringIO.StringIO()
        json.dump(pythonStructure, io)
        val = io.getvalue()
        io.close()
        return val
    
    def close(self):
        try:
            self.mysqldb.close()
        except:
            pass
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-u', '--user',
                        action='store',
                        help='User ID that is to log into MySQL. Default: the user who is invoking this script.')
    parser.add_argument('-p', '--password',
                        action='store_true',
                        help='request to be asked for pwd for operating MySQL;\n' +\
                             '    default: content of scriptInvokingUser$Home/.ssh/mysql if --user is unspecified,\n' +\
                             '    or, if specified user is root, then the content of scriptInvokingUser$Home/.ssh/mysql_root.')
    parser.add_argument('-w', '--givenPass',
                        dest='givenPass',
                        help='Mysql password. Default: see --password. If both -p and -w are provided, -w is used.'
                        )
    args = parser.parse_args();

    if args.user is None:
        user = getpass.getuser()
    else:
        user = args.user
        
    if args.givenPass is not None:
        pwd = args.givenPass
    else:
        if args.password:
            pwd = getpass.getpass("Enter %s's MySQL password on localhost: " % user)
        else:
            # Try to find pwd in specified user's $HOME/.ssh/mysql
            currUserHomeDir = os.getenv('HOME')
            if currUserHomeDir is None:
                pwd = None
            else:
                # Don't really want the *current* user's homedir,
                # but the one specified in the -u cli arg:
                userHomeDir = os.path.join(os.path.dirname(currUserHomeDir), user)
                try:
                    if user == 'root':
                        with open(os.path.join(currUserHomeDir, '.ssh/mysql_root')) as fd:
                            pwd = fd.readline().strip()
                    else:
                        with open(os.path.join(userHomeDir, '.ssh/mysql')) as fd:
                            pwd = fd.readline().strip()
                except IOError:
                    # No .ssh subdir of user's home, or no mysql inside .ssh:
                    pwd = None
                    
    #************
    #print('UID:'+user)
    #print('PWD:'+str(pwd))
    #sys.exit()
    #************
    try:
        learnerHomeworkServer = LearnerHomeworkHistory(user='dataman', passwd=pwd)
    finally:
        try:
            learnerHomeworkServer.close()
        except:
            pass
