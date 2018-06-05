(function() {

  // From Stack Overflow: https://stackoverflow.com/a/21903119/2613185
  function getUrlParameter(sParam) {
    var sPageURL = decodeURIComponent(window.location.search.substring(1)),
        sURLVariables = sPageURL.split('&'),
        sParameterName,
        i;

    for (i = 0; i < sURLVariables.length; i++) {
        sParameterName = sURLVariables[i].split('=');

        if (sParameterName[0] === sParam) {
            return sParameterName[1] === undefined ? true : sParameterName[1];
        }
    }
  }

  // Taken from underscore.js (MIT License)
  // Similar to ES6's rest param (http://ariya.ofilabs.com/2013/03/es6-and-rest-parameter.html)
  // This accumulates the arguments passed into an array, after a given index.
  var restArgs = function(func, startIndex) {
    startIndex = startIndex == null ? func.length - 1 : +startIndex;
    return function() {
      var length = Math.max(arguments.length - startIndex, 0),
          rest = Array(length),
          index = 0;
      for (; index < length; index++) {
        rest[index] = arguments[index + startIndex];
      }
      switch (startIndex) {
        case 0: return func.call(this, rest);
        case 1: return func.call(this, arguments[0], rest);
        case 2: return func.call(this, arguments[0], arguments[1], rest);
      }
      var args = Array(startIndex + 1);
      for (index = 0; index < startIndex; index++) {
        args[index] = arguments[index];
      }
      args[startIndex] = rest;
      return func.apply(this, args);
    };
  };



  // Equivalent of $(document).ready
  document.addEventListener("DOMContentLoaded", function(event) {

    // Register the HIT
    var assignment_id = getUrlParameter("assignmentId");
    if (assignment_id == 'ASSIGNMENT_ID_NOT_AVAILABLE') {
      // preview mode
      return;
    }
    var worker_id = getUrlParameter("workerId");
    var hit_id = getUrlParameter("hitId");
    var aws_account = "{{ AWS_ACCOUNT }}";
    var is_sandbox = getUrlParameter("turkSubmitTo").includes("sandbox");
    var host = is_sandbox ? "mechanicalturk.sandbox.amazonaws.com" : "mechanicalturk.amazonaws.com";


    var data = {
      'assignment_id': assignment_id,
      'worker_id': worker_id,
      'hit_id': hit_id,
      'host': host,
      'aws_account': aws_account
    };

    var params = Object.keys(data).map(function(k) {
      return encodeURIComponent(k) + '=' + encodeURIComponent(data[k])
    }).join('&'); // https://stackoverflow.com/a/14525299/2613185

    var iframe = document.createElement('iframe');
    iframe.setAttribute('id', 'fairworkframe');
    iframe.setAttribute('src', 'https://fairwork.herokuapp.com/iframe?' + params);
    document.body.appendChild(iframe);

  });

})();
