
var ws;

ws = new WebSocket("ws://127.0.0.1:9001/");

ws.onmessage = function(evt) {
    var data;
    data = evt.data;

    var date = new Date();
    var time = date.getHours() + ":";
    time += ((date.getMinutes() < 10) ? "0" : "") + date.getMinutes() + ":";
    time += ((date.getSeconds() < 10) ? "0" : "") + date.getSeconds();
    time = "< " + time + ">: "

    if (data == "start") {
        //start popup,
        console.log(time + " TOOOOOO")
    }

    if (data == "finish") {
        //start popup,
        console.log(time + " DONE")
    }

};

