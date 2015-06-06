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

    var SCHOOL_BUS_PORT = 6070;
    var keepAliveTimer = null;
    var keepAliveInterval = 15000; /* 15 sec*/
    var screenContent = "";
    var source = null;
    var ws = null;
    var timer = null;
    var encryptionPwd = null;
    var callbackRegister = {}

    /*----------------------------  Constructor ---------------------*/
    this.construct = function() {
	originHost = window.location.host;
	ws = new WebSocket("wss://" + originHost + ":" + SCHOOL_BUS_PORT + "/exportClass");

	ws.onopen = function() {
	    keepAliveTimer = window.setInterval(function() {sendKeepAlive()}, keepAliveInterval);
	};

	ws.onclose = function() {
	    clearInterval(keepAliveTimer);
	    alert("The browser or server closed the connection, or network trouble; please reload the page to resume.");
	}

	ws.onerror = function(evt) {
	    clearInterval(keepAliveTimer);
	    //alert("The browser has detected an error while communicating withe the data server: " + evt.data);
	}

	ws.onmessage = function(evt) {
	    
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
		var argsObj   = JSON.parse(oneLineData);
		var msgId     = argsObj.id;
		var msgType   = argsObj.type;
		var msgStatus = argsObj.status;
		var content   = argsObj.content;
	    } catch(err) {
		alert('Error report from server (' + oneLineData + '): ' + err );
		return
	    }
	    handleResponse(msgId, msgType, msgStatus, msgTime, msgContent);
	}
    }();

    /*----------------------------  Registering Callbacks ---------------------*/
    
    var subscribeToTopic(topicName, deliveryCallback, kafkaLiveCheckTimeout=30) {
	currRegistrants = callbackRegister[topicName];
	currRegistrants === undefined {
	    callbackRegister[topicName] = [deliveryCallback];
	} else {
	    callbackRegister.push(deliveryCallback);
	}
    }


    /*----------------------------  Handlers for Msgs from Server ---------------------*/

    var handleResponse = function(msgId, msgType, msgStatus, msgTime, msgContent) {
	switch (msgType) {
	case 'resp':
	    if (msgStatus == "ERROR") {
		handleReturnedError(msgStatus, msgContent);
	    } else {
		forwardReturnVal(content);
	    }
	    break;
	default:
	    alert('Unknown response type from server: ' + msgType);
	    break;
	}
    }

    var sendKeepAlive = function() {
	var req = buildRequest("keepAlive", "");
	ws.send(req);
    }

    var forwardReturnVal = function(topic, content) {
	registrants    = callbackRegister[topic];
	if registrants === undefined {
	    return;
	}
	numRegistrants = registrants.length;
	for (var i=0; i < numRegistrants; i++) {
	    registrants[i](topic, content);
	}
    }


}

var bus = new SchoolBus();

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