
const loginImage = document.getElementById("login-image");

//images tab
const images = [
   "/static/public/img/log1.png",
   "/static/public/img/log2.png",
   "/static/public/img/log3.png"
];

let index = 0; // Index de l'image actuelle

// function of image changement
function changeImage() {
    loginImage.src = images[index]; // Change image
    index = (index + 1) % images.length; 
}

// Change image after 5s
setInterval(changeImage, 5000);


index = Math.floor(Math.random() * images.length);
changeImage();
