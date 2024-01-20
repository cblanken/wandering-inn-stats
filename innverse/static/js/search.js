function minimizeHeader(btn) {
  let form = document.querySelector("#textref-search-form");
  form.style.display = "none";
  form.style.height = "0";
  btn.querySelector("span.uppercase").textContent = "Maximize Search";
  btn.querySelector("svg").classList.add("animate-flip-icon");
  localStorage.setItem("header_hidden", 'true');
}

function showHeader(btn) {
  let form = document.querySelector("#textref-search-form");
  form.style.display = "block";
  form.style.height = "100%";
  btn.querySelector("span.uppercase").textContent = "Minimize Search";
  btn.querySelector("svg").classList.remove("animate-flip-icon");
  localStorage.setItem("header_hidden", 'false');
}

let minBtn = document.querySelector("#minimize-search-btn");
if (minBtn) {
  if (localStorage.getItem("header_hidden") === 'true') {
    let btn = document.querySelector("#minimize-search-btn")
    minimizeHeader(btn);
  }

  minBtn.addEventListener("click", (e) => {
    if (localStorage.getItem("header_hidden") === 'true') {
      showHeader(e.target);
    } else {
      minimizeHeader(e.target);
    }
  });
}
