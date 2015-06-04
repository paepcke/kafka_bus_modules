'''
Created on May 26, 2015

@author: paepcke
'''
import argparse
import cStringIO
import functools
import getpass
import json
import os
import sys

from kafka_bus_python.kafka_bus import BusAdapter
from pymysql_utils.pymysql_utils import MySQLDB


class CoursesGivenQuarter(object):
    '''
    Bus module that queries datastage for course information,
    given academic year, and quarter.
    '''
    
    MYSQL_PORT_LOCAL = 5555
    
    module_topic   = 'course_listing'

    def __init__(self, topic=None, user='dataman', passwd=''):
        '''
        Instantiated for each incoming bus message
        '''
        if topic is None:
            topic = CoursesGivenQuarter.module_topic
            
        self.mysqldb = MySQLDB(host='127.0.0.1', 
                               port=CoursesGivenQuarter.MYSQL_PORT_LOCAL, 
                               user=user, 
                               passwd=passwd, 
                               db='Edx')
        
        # The following statement is needed only 
        # if your callback is a method (rather than a top 
        # level function). That's because Python methods
        # take 'self' as a first argument, while the Bus 
        # expects a function that just takes topicName, msgText, and msgOffset.
        # The following statement creates a function wrapper around 
        # our callback method that has the leading 'self' parameter built 
        # in. The process is called function currying:
        
        self.requestDeliveryMethod = functools.partial(self.requestCoursesForQuarter)        
        
        # Create a BusAdapter instance:
        
        self.bus = BusAdapter()

        # Tell the bus that you are interested in the topic 'example_use',
        # and want callbacks to self.exampleDeliveryMethod whenever
        # a message arrives:
        
        self.bus.subscribeToTopic(topic, self.requestDeliveryMethod)
        
        # Now we do nothing. In a production system you 
        # would do something useful here:
        
        while True:
            # do anything you like
            self.bus.waitForMessage(CoursesGivenQuarter.module_topic)

    def requestCoursesForQuarter(self, topicName, msgText, msgOffset):
        '''
        This method is called whenever a message in topic
        'course_listing' is published by anyone on the bus.
        The msgText should have the JSON format:
        
            {'req_key' : 'abcd'
             'content' : {'academic_year' : '2014',
                          'quarter'       : 'spring'},
             'time'    : '2015-05-27T18:12:22.706204',
                          }           
        
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
            # Import the message into a dict:
            msgDict = json.loads(msgText)
        except ValueError:
            self.bus.logError('Received msg with invalid wrapping JSON: %s (%s)' % str(msgText))
            return

        # Must have a learner message id:
        try:
            reqId = msgDict['id']
        except KeyError:
            self.returnError('NULL', "Error: message type not provided in an incoming request.")
            self.bus.logError("Message type not provided in %s" % str(msgDict))
            return

        # Must have a learner type == 'req'
        try:
            reqKey = msgDict['type']
            if reqKey != 'req':
                return
        except KeyError:
            self.returnError(reqId, "Error: message type not provided in %s" % str(msgDict))
            self.bus.logError('Received msg without a type field: %s' % str(msgText))
            return
        
        # The content field should be legal JSON; make a
        # dict from it:
        try:
            contentDict = msgDict['content']
        except KeyError:
            self.returnError(reqKey, "Error: no content field provided in %s" % str(msgDict))
            self.bus.logError('Received msg without a content field: %s' % str(msgText))
            return
        
        # Must have an academic year:
        try:
            academicYear = contentDict['academic_year']
        except KeyError:
            self.returnError(reqKey, "Error: academic year not provided in %s" % str(msgDict))
            self.bus.logError('Received msg without academic year in content field: %s' % str(msgText))            
            return
            
        # Must have a quarter:
        try:
            quarter = contentDict['quarter']
        except KeyError:
            self.returnError(reqKey, "Error: quarter not provided in %s" % str(msgDict))
            self.bus.logError('Received msg without quarter in content field: %s' % str(msgText))            
            return
        
        # Get an array of dicts, each dict being one MySQL record:
        #    course_display_name,
        #    course_catalog_name,
        #    is_internal
        
        resultArr = self.executeCourseInfoQuery(academicYear, quarter)
        
        # Turn result into an HTML table:
        htmlRes = self.buildHtmlTableFromQueryResult(resultArr)

        # Note that we pass the message type 'resp' 
        # to publish(), and that we specify that the
        # msg ID is to be the same as the incoming request.

        self.bus.publish(htmlRes, 
                         CoursesGivenQuarter.module_topic,
                         msgType='resp',
                         msgId=reqId)
        
    def executeCourseInfoQuery(self, academicYear, quarter):
        
        homeworkQuery = "SELECT course_display_name," +\
    			        "course_catalog_name," +\
    			        "is_internal " +\
    			   "FROM CourseInfo " +\
    			  "WHERE academic_year = '%s' " % academicYear +\
                    " AND quarter = '%s' " % quarter +\
                    ";"

        try:
            resIt = self.mysqldb.query(homeworkQuery)
        except Exception as e:
            self.returnError("Error: Call to database returned an error: '%s'" % `e`)
            self.bus.logError("Call to MySQL returned an error: '%s'" % `e`)
            return
            
        resultArr = []
        for res in resIt:
            resultArr.append(res)
            
        return resultArr
    
    def returnError(self, req_id, errMsg):
        self.bus.publish(errMsg, 
                         CoursesGivenQuarter.module_topic,
                         msgId=req_id, 
                         msgType='resp')

    def buildHtmlTableFromQueryResult(self, resTupleArr):
        htmlStr   = '<table border=1><tr><td><b>Course</b></td><td><b>Description</b></td><td><b>Internal-Only</b></td></tr>'
        strResArr = []
        for (courseDisplayName, courseCatalogName, isInternal) in resTupleArr:
            strResArr.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" %
                             (courseDisplayName, courseCatalogName, isInternal))
        htmlStr = htmlStr + ' '.join(strResArr) + '</table>'
        return htmlStr
            
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
        courseLister = CoursesGivenQuarter(user=user, passwd=pwd)
    finally:
        try:
            courseLister.close()
        except:
            pass
