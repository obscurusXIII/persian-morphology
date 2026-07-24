const form = document.querySelector("#analyze-form");
const input = document.querySelector("#word");
const result = document.querySelector("#result");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  result.textContent = "…";
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: input.value }),
    });
    const payload = await response.json();
    result.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    result.textContent = String(error);
  }
});
