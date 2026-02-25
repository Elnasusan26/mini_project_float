document.addEventListener("DOMContentLoaded", () => {

  /* =========================
     ROLE SELECTION LOGIC
     ========================= */
  const roleButtons = document.querySelectorAll(".role-btn");
  let selectedRole = "admin"; // default role

  roleButtons.forEach(button => {
    button.addEventListener("click", () => {
      // remove active class from all buttons
      roleButtons.forEach(btn => btn.classList.remove("active"));

      // add active class to clicked button
      button.classList.add("active");

      // update selected role
      selectedRole = button.dataset.role;
      console.log("Selected role:", selectedRole);
    });
  });

  /* =========================
     PASSWORD TOGGLE LOGIC
     ========================= */
  const togglePassword = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("password");
  const eyeOpen = document.getElementById("eyeOpen");
  const eyeClosed = document.getElementById("eyeClosed");

  // safety check
  if (togglePassword && passwordInput && eyeOpen && eyeClosed) {

    // initial state
    eyeOpen.style.display = "block";
    eyeClosed.style.display = "none";

    togglePassword.addEventListener("click", () => {
      if (passwordInput.type === "password") {
        passwordInput.type = "text";
        eyeOpen.style.display = "none";
        eyeClosed.style.display = "block";
      } else {
        passwordInput.type = "password";
        eyeOpen.style.display = "block";
        eyeClosed.style.display = "none";
      }
    });
  }

});
