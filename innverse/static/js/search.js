let header = document.querySelector("#textref-search-form");

function replace_header_fold_icon(feather_name) {
  let header_fold_btn = document.querySelector("#header-fold-btn")
  let icon = document.createElement("i")
  icon.classList.add("inline");
  icon.setAttribute("data-feather", feather_name)
  header_fold_btn.replaceChild(icon, header_fold_btn.firstElementChild);
  feather.replace()
}

function fold_header(btn) {
  header.style.display = "none";
  header.style.height = "0";
  btn.querySelector("span.uppercase").textContent = "Maximize Search";
  replace_header_fold_icon("chevron-down");
  localStorage.setItem("header_folded", true);
}

function unfold_header(btn) {
  header.style.display = "block";
  header.style.height = "100%";
  btn.querySelector("span.uppercase").textContent = "Minimize Search";
  replace_header_fold_icon("chevron-up");
  localStorage.setItem("header_folded", false);
}

// Fold per setting in localStorage
let header_fold_btn = document.querySelector("#header-fold-btn")
let is_header_folded = localStorage.getItem("header_folded");
if (is_header_folded === "true") {
  fold_header(header_fold_btn)
}

// Add fold click event
header_fold_btn.addEventListener("click", (e) => {
  if (localStorage.getItem("header_folded") === "true") {
    unfold_header(e.target)
  } else {
    fold_header(e.target)
  }
  window.dispatchEvent(new Event('resize'));
})
