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

  // Add the timer script to the parent page, not to the Fair Work iframe
  function addTimerScript() {

    var newScript = document.createElement("script");
    newScript.onload = function() {
      // Register the timer for estimated time spent
      TimeMe.initialize({
          currentPageName: getUrlParameter("assignmentId"), // current page
          idleTimeoutInSeconds: 30 // seconds
      });
      window.setInterval(checkEstimatedTime, 1000);
    }
    document.head.appendChild(newScript);
    newScript.src = "https://cdnjs.cloudflare.com/ajax/libs/TimeMe.js/2.0.0/timeme.min.js";
  }

  function checkEstimatedTime() {
    var timeInSeconds = TimeMe.getTimeOnCurrentPageInSeconds();
    document.getElementById('fairworkframe').contentWindow.postMessage({
      'status': 'estimatedTime',
      'value': timeInSeconds
    }, '{{ FAIRWORK_DOMAIN }}');
  }

  // Equivalent of $(document).ready
  document.addEventListener("DOMContentLoaded", function(event) {

    var assignment_id = getUrlParameter("assignmentId");
    if (assignment_id == null) {
      assignment_id = 'ASSIGNMENT_ID_NOT_AVAILABLE'
    }
    var worker_id = getUrlParameter("workerId");
    var hit_id = getUrlParameter("hitId");
    var submit_to = getUrlParameter("turkSubmitTo");
    var aws_account = "{{ AWS_ACCOUNT }}";

    var data = {
      'assignmentId': assignment_id,
      'workerId': worker_id,
      'hitId': hit_id,
      'aws_account': aws_account,
      'turkSubmitTo': submit_to
    };

    // Filter out the undefined parts of the data
    data = Object.keys(data)
    .filter(key => data[key] != null)
    .reduce((obj, key) => {
      obj[key] = data[key];
      return obj;
    }, {});

    // Add iframe
    var params = Object.keys(data).map(function(k) {
      return encodeURIComponent(k) + '=' + encodeURIComponent(data[k])
    }).join('&'); // https://stackoverflow.com/a/14525299/2613185
    var url = "{{ IFRAME_URL }}" + "?" + params;

    var iframe = document.createElement('iframe');
    iframe.setAttribute('id', 'fairworkframe');
    iframe.setAttribute('src', url);
    iframe.setAttribute('style', 'margin: 0; padding: 0; border: none; width: 100%; height: 500px;');
    document.body.appendChild(iframe);
    iframe.onload = addTimerScript;

  });

})();
