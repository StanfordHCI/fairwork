(function() {

  function reportTime() {
    var time = document.getElementById("fairwork-min").value;
    var assignment_id = getUrlParameter("assignmentId");
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
      'duration': time,
      'aws_account': aws_account
    };

    var http = new XMLHttpRequest();
    var url = "{{ DURATION_URL }}";
    var params = Object.keys(data).map(function(k) {
      return encodeURIComponent(k) + '=' + encodeURIComponent(data[k])
    }).join('&'); // https://stackoverflow.com/a/14525299/2613185

    http.withCredentials = true;
    http.open("POST", url, true);
    http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");

    http.onreadystatechange = function() {//Call a function when the state changes.
        if(http.readyState == 4 && http.status == 200) {
            console.log(http.responseText);
        }
    }
    http.send(params);
  }

  // https://docs.djangoproject.com/en/2.0/ref/csrf/
  function getCookie(name) {
      var cookieValue = null;
      if (document.cookie && document.cookie !== '') {
          var cookies = document.cookie.split(';');
          for (var i = 0; i < cookies.length; i++) {
              var cookie = jQuery.trim(cookies[i]);
              // Does this cookie string begin with the name we want?
              if (cookie.substring(0, name.length + 1) === (name + '=')) {
                  cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                  break;
              }
          }
      }
      return cookieValue;
  }

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
  // Returns a function, that, as long as it continues to be invoked, will not
  // be triggered. The function will be called after it stops being called for
  // N milliseconds. If `immediate` is passed, trigger the function on the
  // leading edge, instead of the trailing.
  function debounce(func, wait, immediate) {
    var timeout, result;

    var later = function(context, args) {
      timeout = null;
      if (args) result = func.apply(context, args);
    };

    var debounced = restArgs(function(args) {
      if (timeout) clearTimeout(timeout);
      if (immediate) {
        var callNow = !timeout;
        timeout = setTimeout(later, wait);
        if (callNow) result = func.apply(this, args);
      } else {
        timeout = delay(later, wait, this, args);
      }

      return result;
    });

    debounced.cancel = function() {
      clearTimeout(timeout);
      timeout = null;
    };

    return debounced;
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

  // Taken from underscore.js (MIT License)
  // Delays a function for the given number of milliseconds, and then calls
  // it with the arguments supplied.
  var delay = restArgs(function(func, wait, args) {
    return setTimeout(function() {
      return func.apply(null, args);
    }, wait);
  });


  // Equivalent of $(document).ready
  document.addEventListener("DOMContentLoaded", function(event) {
    // Add JS and CSS
    {% spaceless %}
    document.body.innerHTML += "{{ DIV_HTML | safe }}";
    var css = document.createElement("style");
    css.type = "text/css";
    css.innerHTML = "{{ CSS | safe }}";
    document.head.appendChild(css);
    {% endspaceless %}

    document.getElementById("fairwork-min").addEventListener("keyup", debounce(reportTime, 250));

    /*
    // Do any relevant exchange of keys
    var oReq = new XMLHttpRequest();
    oReq.open("GET", '{{ HOME_URL }}');
    oReq.withCredentials = true;
    oReq.onload = function(e) {

    }
    oReq.send();
    */

    // Register the HIT
    var assignment_id = getUrlParameter("assignmentId");
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

    var http = new XMLHttpRequest();
    var url = "{{ CREATE_HIT_URL }}";
    var params = Object.keys(data).map(function(k) {
      return encodeURIComponent(k) + '=' + encodeURIComponent(data[k])
    }).join('&'); // https://stackoverflow.com/a/14525299/2613185

    http.withCredentials = true;
    http.open("POST", url, true);
    http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");

    http.onreadystatechange = function() {//Call a function when the state changes.
        if(http.readyState == 4 && http.status == 200) {
            console.log(http.responseText);
        }
    }
    http.send(params);
  });

})();
