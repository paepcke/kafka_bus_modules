/*
  Loaded by exportClass.html. Function startProgressStream()
  is called when the Export Class button is pressed. The function
  causes:
  dbadmin:datastage:Code/json_to_relation/json_to_relation/cgi_bin/exportClass.py
  to run on datastage. That remote execution is started via
  an EventSource, so that server-send messages from datastage
  can be displayed on the browser below the export class form.
*/

function SchoolBus() {

    this.SCHOOL_BUS_PORT = 6070;
    this.JS_2_SCHOOL_BUS_ADMIN_TOPIC = 'js2schoolBusAdmin';

    this.keepAliveTimer = null;
    this.keepAliveInterval = 15000; /* 15 sec*/
    this.WS_CONNECT_TIMEOUT  = 5000;  /*  5 sec*/
    this.screenContent = "";
    this.source = null;
    this.ws = null;
    this.timer = null;
    this.encryptionPwd = null;
    this.callbackRegister = {};

    /*----------------------------  Constructor ---------------------*/

    originHost = window.location.host;
    
    // When testing by loading files that use this script,
    // the above will be empty; deal with this special case:
    if (originHost.length == 0) {
    	originHost = "localhost";
    }

    webSocketUrl = "wss://" + originHost + ":" + this.SCHOOL_BUS_PORT + "/js2schoolBus";

    this.ws = new WebSocket(webSocketUrl);
    this.ws.parent = this;

    /*----  Websocket Event Handlers  ----*/

    this.ws.onopen = function() {
    	keepAliveTimer = window.setInterval(function() {SchoolBus.prototype.sendKeepAlive()}, this.keepAliveInterval);
    };

    this.ws.onclose = function() {
    	clearInterval(keepAliveTimer);
    	alert("The browser or server closed the connection, or network trouble; please reload the page to resume.");
    }

    this.ws.onerror = function(evt) {
    	clearInterval(keepAliveTimer);
    	//alert("The browser has detected an error while communicating withe the data server: " + evt.data);
    }

    this.ws.onmessage = function(evt) {
	
    	/**
    	   Internalize the JSON
    	   e.g. {"id"      : "a453a...", 
    	   "type"    : "resp", 
    	   "status"  : "OK",
    	   "time"    : "2015-06-20T15:30...",
    	   "content" : {"x" : "10", "y" : "20"}

    	   @param {string} JSON with event info
    	*/   

    	try {
    	    var oneLineData = evt.data.replace(/(\r\n|\n|\r)/gm," ");
    	    var argsObj    	= JSON.parse(oneLineData);
    	    var msgId      	= argsObj.id;
    	    var msgType    	= argsObj.type;
    	    var msgStatus  	= argsObj.status;
    	    var msgTime    	= argsObj.time;
    	    var msgContent 	= argsObj.content;
	    var msgTopic    = argsObj.topic;
    	} catch(err) {
    	    alert('Error report from server (' + oneLineData + '): ' + err );
    	    return
    	}
    	this.parent.handleResponse(msgTopic, msgId, msgType, msgStatus, msgTime, msgContent);
    }
}

SchoolBus.prototype = {

    constructor : SchoolBus,


    /*----------------------------  Registering Callbacks ---------------------*/
    

    subscribeToTopic : function(topicName, deliveryCallback, kafkaLiveCheckTimeout) {
	if (kafkaLiveCheckTimeout === undefined) {
	    kafkaLiveCheckTimeout = 30;
	}
	currRegistrants = this.callbackRegister[topicName];
	if (currRegistrants === undefined) {
	    this.callbackRegister[topicName] = [deliveryCallback];
	} else {
	    this.callbackRegister.push(deliveryCallback);
	}
    },

    /*----------------------------  Pushlishing to Bus ---------------------*/

    publish : function (busMessage, 
			topicName,
			optionObj) {
	/**
	   Publishes one message to the SchoolBus, given the message's
	   'content' field, and the topic name. Optionally, a JSON
	   object may be passed to determine the message's type field
	   value, and whether the message will be treated on the
	   SchoolBus as synchronous.

	   @param busMessage: the content field of the outgoing
	      message. This string will often be valid JSON, but
	      does not need to be: depends on the topic subscriber's
	      expectations.
	   @type busMessage: string
	   @param topicName: the Kafka topic to publish to
	   @type topicName: string
	   @param optionObj: a JSON object containing options for
	      the sending process. Valid fields are:
	          "type" : {"req" | "resp" | "keep-alive"}
		  "sync" : {"1" | "0"}
	   
	*/

	if (optionObj === undefined) {
	    type = 'req';
	    sync = 'False';
	} else {
	    // Establish default values for all options:
	    type = "req";
	    sync = "False";

	    // And overwrite them if provided:
	    if (optionObj.hasOwnProperty('type')) {
		type = optionObj["type"];
	    }
	    if (optionObj.hasOwnProperty('sync')) {
		sync = optionObj["sync"];
	    }
	}

	msg = {'id'   	 : this.generateUUID(),
	       'type' 	 : type,
	       'time' 	 : new Date().toISOString(),
	       'topic'   : topicName,
	       'content' : busMessage,
	       'sync'    : sync
	      }
	try {
	    this.ws.send(JSON.stringify(msg));
    	} catch(err) {
    	    alert('Error while sending (' + JSON.stringify(msg) + '): ' + err );
    	    return
    	}

    },

    /*----------------------------  Handlers for Msgs from Server ---------------------*/

    handleResponse : function(msgTopic, msgId, msgType, msgStatus, msgTime, msgContent) {
	switch (msgType) {
	case 'resp':
	    if (msgStatus == "ERROR") {
		handleReturnedError(msgStatus, msgContent);
	    } else {
		this.forwardReturnVal(msgTopic, msgContent);
	    }
	    break;
	default:
	    alert('Unknown response type from server: ' + msgType);
	    break;
	}
    },

    sendKeepAlive : function() {
	// Send empty msg to topic JS_2_SCHOOL_BUS_ADMIN_TOPIC,
	// of type 'keepAlive':

	// To debug: don't actually send keep-alive. Uncomment this
	// when the rest works!!
	var req = this.publish("", this.JS_2_SCHOOL_BUS_ADMIN_TOPIC, "keepAlive");
    },

    forwardReturnVal : function(topic, content) {
	registrants    = this.callbackRegister[topic];
	if (registrants === undefined) {
	    return;
	}
	numRegistrants = registrants.length;
	for (var i=0; i < numRegistrants; i++) {
	    registrants[i](topic, content);
	}
    },

    generateUUID : function() {
	var d = new Date().getTime();
	var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
	    var r = (d + Math.random()*16)%16 | 0;
	    d = Math.floor(d/16);
	    return (c=='x' ? r : (r&0x3|0x8)).toString(16);
	});
	return uuid;
    },

    waitForWebSocketConnection : function(callback) {
	/**
	   Wait max of WS_CONNECT_TIMEOUT msecs until 
	   Websocket is connected. Not usually needed.
	 */
	startTime = new Date().getTime();
	setTimeout(
            function () {
		if (this.ws.readyState === ws.OPEN) {
                    console.log("Connection is made")
                    if(callback !== undefined){
			callback();
                    }
                    return;

		} else {
                    console.log("wait for connection...")
		    totalElapsedTime = new Date().getTime() - startTime
		    if (totalElapsedTime > this.WS_CONNECT_TIMEOUT) {
			throw new WebSocketNotReadyExc();
		    }
                    this.waitForSocketConnection(callback);
		}

            }, 5); // wait 5 milisecond for the connection...
    },

    /*----------------------------  Miscellaneous ---------------------*/


    close : function() {
	ws.close();
    }

} // end prototype additions for class SchoolBus

// In your JS code, instantiate bus acces via:
// var bus = new SchoolBus();

/*
document.getElementById('listClassesBtn').addEventListener('click', classExporter.evtResolveCourseNames);
document.getElementById('getDataBtn').addEventListener('click', classExporter.evtGetData);
document.getElementById('clrProgressBtn').addEventListener('click', classExporter.evtClrPro);
document.getElementById('cancelBtn').addEventListener('click', classExporter.evtCancelProcess);
//document.getElementById('piiPolicy').addEventListener('change', classExporter.evtPIIPolicyClicked);
document.getElementById('pwdOK').addEventListener('click', classExporter.evtCryptoPwdSubmit);
document.getElementById('edxForum').addEventListener('click', classExporter.evtAnyForumClicked);
document.getElementById('piazzaForum').addEventListener('click', classExporter.evtAnyForumClicked);
document.getElementById('edcastForum').addEventListener('click', classExporter.evtAnyForumClicked);
document.getElementById('emailList').addEventListener('click', classExporter.evtEmailListClicked);
document.getElementById('learnerPII').addEventListener('click', classExporter.evtLearnerPIIClicked);
document.getElementById('quarterRep').addEventListener('click', classExporter.evtQuarterlyRepClicked);
document.getElementById('quarterRepByActivity').addEventListener('click', classExporter.inclCourseActivityClicked);

// The following is intended to make CR in 
// course ID text field click the Get Course List
// button, but the assigned func is never talled:
document.getElementById('courseID').addEventListener('onkeydown', classExporter.evtCarriageReturnListMatchesTrigger);

// Initially, we hide the solicitation for
// a PII zip file encryption pwd:
classExporter.hideCryptoPwdSolicitation();

// Same for the quarterly specs, unless 
// quarterly report is already checked:

if (document.getElementById('quarterRep').checked) {
    classExporter.showQuarterlySpecs();
} else {
    classExporter.hideQuarterlySpecs();
}

// For now we permanently hide Edcast and Piazza:
document.getElementById('piazzaAndEdcast').style.display = "none";

*/