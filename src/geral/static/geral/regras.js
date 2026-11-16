// The rules dialog of a game: shown once by itself (remembered per game), then by the "?" button.
(() => {
  const dialog = document.getElementById("regras");
  if (!dialog) return;
  const key = `regras:${dialog.dataset.game}`;
  const open = () => dialog.showModal();
  document.querySelectorAll(".rules-open").forEach((button) => button.addEventListener("click", open));
  dialog.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => dialog.close()));
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close(); // a tap on the dimmed page around it
  });
  let seen = false;
  try {
    seen = localStorage.getItem(key) === "1";
    localStorage.setItem(key, "1");
  } catch {
    /* private mode: show the rules every time rather than never */
  }
  if (!seen) open();
})();
