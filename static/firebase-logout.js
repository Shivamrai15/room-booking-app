"use strict";

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.10.0/firebase-app.js";
import { getAuth, signOut } from "https://www.gstatic.com/firebasejs/10.10.0/firebase-auth.js";

const firebaseConfig = {
    apiKey: "AIzaSyB7tSFkoCaWAFUuEQMwNvjsMNiZC_pjdF0",
    authDomain: "lunar-implement-416715.firebaseapp.com",
    projectId: "lunar-implement-416715",
    storageBucket: "lunar-implement-416715.appspot.com",
    messagingSenderId: "588266450285",
    appId: "1:588266450285:web:13abd0e20511827916be64"
};

window.addEventListener("load", function(){
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    updateUI(document.cookie);
    // signout from firebase
    document.getElementById("sign-out").addEventListener(("click"), function() {
        signOut(auth)
        .then((output) => {
            document.cookie = "token=;path=/;SameSite=Strict";
            window.location = "/";
        })
    });
});


function updateUI (cookie) {
    var token = parseCookieToken(cookie);

    try {
        if (token.length > 0 ) {
            document.getElementById("sign-out").hidden = false;
            document.getElementById("login-href").hidden = true;
            document.getElementById("room-href").hidden = false;
            document.getElementById("book-href").hidden = false;
        } else {
            document.getElementById("sign-out").hidden = true;
            document.getElementById("login-href").hidden = false;
            document.getElementById("room-href").hidden = true;
            document.getElementById("book-href").hidden = true;
        }
    } catch (error) {
        console.log(error);
    }
}

function parseCookieToken(cookie) {
    var strings = cookie.split(";");

    for ( let i=0; i< strings.length; i++ ) {
        var temp = strings[i].split("=");
        if ( temp[0] == "token" ) {
            return temp[1];
        }
    }

    return "";
}