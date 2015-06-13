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
	bus.publish('{"cursorX" : "' + cursorX  + '" , "cursorY" : "' + cursorY + '"}', 'coord_doubling');
    }

    // var startLocalCursorTracking = function() {
	
    // }

}

busExperiment = new SchoolbusSpeedExperiment();

document.addEventListener('mousemove', busExperiment.fillMouseFields);
