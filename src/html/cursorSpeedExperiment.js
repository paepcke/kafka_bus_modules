//busScript      = document.createElement('schoolBus');
//busScript.type = 'text/javascript';
//busScript.src  = 'schoolbus.js';
//document.getElementsByTagName('head')[0].appendChild(busScript);


var bus = new SchoolBus();

function SchoolbusSpeedExperiment() {

    this.fillMouseFields = function(mouseMoveEvt) {
	showMouseXY(mouseMoveEvt.pageX, mouseMoveEvt.pageY);
	showDoubleMouseXY(mouseMoveEvt.pageX, mouseMoveEvt.pageY);
    }

    var showMouseXY = function(cursorX, cursorY) {
	document.getElementById('mouseX').value = cursorX;
	document.getElementById('mouseY').value = cursorY;
    }

    var showDoubleMouseXY = function(cursorX, cursorY) {
	//document.getElementById('doubleMouseX').value = cursorX;
	//document.getElementById('doubleMouseY').value = cursorY;
	bus.publish('{"cursorX" : "' + cursorX  + '" , "cursorY" : "' + cursorY + '"}', // Msg
		    'coord_doubling',
		    {"sync" : "true"}
		   );
    }

    this.receiveDoubleCursor = function(topic, content)  {
	contentObj = JSON.parse(content);
	document.getElementById('doubleMouseX').value = contentObj.cursorXx2;
	document.getElementById('doubleMouseY').value = contentObj.cursorYx2;
    }

    // var startLocalCursorTracking = function() {
    // }

}


busExperiment = new SchoolbusSpeedExperiment();
bus.subscribeToTopic('coord_doubling', busExperiment.receiveDoubleCursor);

document.addEventListener('mousemove', busExperiment.fillMouseFields);
