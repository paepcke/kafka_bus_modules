//busScript      = document.createElement('schoolBus');
//busScript.type = 'text/javascript';
//busScript.src  = 'schoolbus.js';
//document.getElementsByTagName('head')[0].appendChild(busScript);


var bus = new SchoolBus();

function SchoolbusSpeedExperiment() {

    // Modify to taste:
    var NUM_TRIPS_TO_MEASURE = 100;
    var PUBLISH_SYCHRONOUSLY = true;

    // Locals
    var roundTrips = 0;

    // Use queue to record start time, so
    // that we can work with both synchronous
    // and asychronous publish:
    var sendTime = [];
    var msgTravelTime = 0;
    var cursorX = 10;
    var cursorY = 20;

    // Arr of msecs/msg results; used
    // to compute running average:
    var speedResults = [];

    var keepExperimentRunning = true;

    this.receiveDoubleCursor = function(topic, content)  {

	currTime = new Date().getTime();
	// Get the send time of the originating
	// request, and subtract from curr time:
	msgTravelTime += currTime - sendTime.shift();
	if (roundTrips >= NUM_TRIPS_TO_MEASURE) {
	    // Experiment done:
	    msecsPerAllRounds = msgTravelTime/NUM_TRIPS_TO_MEASURE;
	    speedResults.push(msecsPerAllRounds);
	    runningAvg = getRunningAvg();
	    writeToDisplay("Time for " + roundTrips + " trips: " + msecsPerAllRounds + "ms/msg. Total time: " + msgTravelTime + "ms (running avg: " + runningAvg + ")<br>");

	    msgTravelTime = 0;
	    roundTrips = 0;
	    if (keepExperimentRunning) {
		resetForNewExperiment();
	    }
	    return;
	}
	// Publish next:
	sendTime.push(new Date().getTime());
	bus.publish('{"cursorX" : "' + cursorX  + '" , "cursorY" : "' + cursorY + '"}', // Msg
		    'coord_doubling',
		    {"sync" : PUBLISH_SYCHRONOUSLY}
		   );
	cursorX += 1;
	cursorY += 1;
	roundTrips += 1;
    }

    var getRunningAvg = function() {
	sum = 0;
	for (i=0;i<speedResults.length;i++) {
	    sum += speedResults[i];
	}
	return sum / speedResults.length;
    }

    var resetForNewExperiment = function() {

	msgTravelTime = 0;
	sendTime      = [];
	cursorX       = 10;
	cursorY       = 20;
	roundTrips    = 0;

	sendTime.push(new Date().getTime());
	bus.publish('{"cursorX" : "' + cursorX  + '" , "cursorY" : "' + cursorY + '"}', // Msg
		    'coord_doubling',
		    {"sync" : "true"}
		   );
    }

    var writeToDisplay = function(msg) {
	document.getElementById('log').innerHTML += msg;
    }
    
    this.clearDisplay = function(msg) {
	document.getElementById('log').innerHTML = "";
    }

    this.startExperiment = function() {
        writeToDisplay("<br>Starting experiment...<br>")
	keepExperimentRunning = true;
	resetForNewExperiment();
    }

    this.stopExperiment = function() {
	keepExperimentRunning = false;
	writeToDisplay("Stopping experiment...<br>");
    }

}


busExperiment = new SchoolbusSpeedExperiment();
bus.subscribeToTopic('coord_doubling', busExperiment.receiveDoubleCursor);

document.getElementById('startButton').addEventListener('click', busExperiment.startExperiment);
document.getElementById('stopButton').addEventListener('click', busExperiment.stopExperiment);
document.getElementById('clearDisplay').addEventListener('click', busExperiment.clearDisplay);
