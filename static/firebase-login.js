'use strict'

// import firebase
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.9.0/firebase-app.js"
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut } from "https://www.gstatic.com/firebasejs/12.9.0/firebase-auth.js"

//  web app's firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyBDTfC5S1hB9Y_Yx30XySw8V-JDYvc4IRQ",
    authDomain: "room-scheduler-31165.firebaseapp.com",
    projectId: "room-scheduler-31165",
    storageBucket: "room-scheduler-31165.firebasestorage.app",
    messagingSenderId: "955618408046",
    appId: "1:955618408046:web:3d35b72866a9426e29587f"
};

window.addEventListener("load", function() {
    const app = initializeApp(firebaseConfig)
    const auth = getAuth()
    updateUI(document.cookie)
    console.log("hello world load")

    // signup of a new user to firebase
    document.getElementById("sign-up").addEventListener('click', function() {
        const email = document.getElementById("email").value
        const password = document.getElementById("password").value

        createUserWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            const user = userCredential.user

            user.getIdToken().then((token) => {
                document.cookie = "token=" + token + ";path=/;SameSite=Strict";
                window.location = "/";
            });
        })
        .catch((error) => {
            console.log(error.code + error.message)
        });
    })

    // login of a user to firebase
    document.getElementById("login").addEventListener('click', function() {
        const email = document.getElementById("email").value
        const password = document.getElementById("password").value

        signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            const user = userCredential.user
            console.log("logged in")

            user.getIdToken().then((token) => {
                document.cookie = "token=" + token + ";path=/;SameSite=Strict";
                window.location = "/"
            });
        })
        .catch((error) => {
            console.log(error.code + error.message)
        });
    })

    // signout from firebase
    document.getElementById("sign-out").addEventListener('click', function() {
        signOut(auth)
        .then((output) => {
            document.cookie = "token=;path=/;SameSite=Strict";
            window.location = "/";
        })
    });
});

// function that will update the UI for the user
function updateUI(cookie) {
    var token = parseCookieToken(cookie);

    if(token.length > 0) {
        document.getElementById("login-box").hidden = true;
        document.getElementById("sign-out").hidden = false;
    } else {
        document.getElementById("login-box").hidden = false;
        document.getElementById("sign-out").hidden = true;
    }
}

// function that will parse the cookie token
function parseCookieToken(cookie) {
    var strings = cookie.split(';');

    for(let i = 0; i < strings.length; i++) {
        var temp = strings[i].split('=');
        if(temp[0] == "token")
            return temp[1];
    }
    return ""
}