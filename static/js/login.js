document.addEventListener("DOMContentLoaded", () => {

  const togglePassword = document.getElementById("togglePassword");
  const passwordInput  = document.getElementById("password");
  const eyeOpen        = document.getElementById("eyeOpen");
  const eyeClosed      = document.getElementById("eyeClosed");

  if (togglePassword && passwordInput && eyeOpen && eyeClosed) {

    eyeOpen.style.display  = "block";
    eyeClosed.style.display = "none";

    togglePassword.addEventListener("click", () => {
      if (passwordInput.type === "password") {
        passwordInput.type      = "text";
        eyeOpen.style.display   = "none";
        eyeClosed.style.display = "block";
      } else {
        passwordInput.type      = "password";
        eyeOpen.style.display   = "block";
        eyeClosed.style.display = "none";
      }
    });
  }

});document.addEventListener("DOMContentLoaded", () => {

  const togglePassword = document.getElementById("togglePassword");
  const passwordInput  = document.getElementById("password");
  const eyeOpen        = document.getElementById("eyeOpen");
  const eyeClosed      = document.getElementById("eyeClosed");

  if (togglePassword && passwordInput && eyeOpen && eyeClosed) {

    eyeOpen.style.display  = "block";
    eyeClosed.style.display = "none";

    togglePassword.addEventListener("click", () => {
      if (passwordInput.type === "password") {
        passwordInput.type      = "text";
        eyeOpen.style.display   = "none";
        eyeClosed.style.display = "block";
      } else {
        passwordInput.type      = "password";
        eyeOpen.style.display   = "block";
        eyeClosed.style.display = "none";
      }
    });
  }

});