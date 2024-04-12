"use strict";

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.10.0/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/10.10.0/firebase-auth.js";

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

    // signup of a new user to firebase
    document.getElementById("sign-up").addEventListener("click", function(){

        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;

        createUserWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {

            const user = userCredential.user;
            console.log("User has been created");

            user.getIdToken().then((token) => {
                    document.cookie = "token=" + token + ";path=/;SameSite=Strict";
                    window.location = "/";
            });
        })
        .catch((error) => {
            console.log(error.code, error.message);
        });

    });

    // login for a user to firebase
    document.getElementById("login").addEventListener("click", function() {
       
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;

        signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {

            const user = userCredential.user;
            console.log("User has been logged in");

            user.getIdToken().then((token) => {
                    document.cookie = "token=" + token + ";path=/;SameSite=Strict";
                    window.location = "/";
            });
        })
        .catch((error) => {
            console.log(error.code, error.message);
        });

    });

});

