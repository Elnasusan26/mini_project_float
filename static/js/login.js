document.addEventListener("DOMContentLoaded", () => {
  const roleButtons = document.querySelectorAll(".role-btn");
  let selectedRole = "admin";

  roleButtons.forEach(button => {
    button.addEventListener("click", () => {
      
      roleButtons.forEach(btn => btn.classList.remove("active"));

      button.classList.add("active");

      selectedRole = button.dataset.role;
      console.log("Selected role:", selectedRole);
    });
  });

  const togglePassword = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("password");
  const eyeOpen = document.getElementById("eyeOpen");
  const eyeClosed = document.getElementById("eyeClosed");

  if (togglePassword && passwordInput && eyeOpen && eyeClosed) {
 
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
