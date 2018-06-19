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

  // Equivalent of $(document).ready
  document.addEventListener("DOMContentLoaded", function(event) {

    var assignment_id = getUrlParameter("assignmentId");
    if (assignment_id == 'ASSIGNMENT_ID_NOT_AVAILABLE') {
      // preview mode
      return;
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

    var iframe = document.createElement('iframe');
    iframe.setAttribute('id', 'fairworkframe');
    iframe.setAttribute('src', 'https://fairwork.herokuapp.com/iframe?' + params);
    iframe.setAttribute('style', 'margin: 0; padding: 0; border: none; width: 100%; height: 300px;');
    document.body.appendChild(iframe);

  });

})();
