window.addEventListener("load", setupForm)
var captchaWidgetID = null;

window.onloadTurnstileCallback = () => {
	captchaWidgetID = turnstile.render("#cf-turnstile", {
		sitekey: "0x4AAAAAAAU4_tLhgcruoYjU",
		callback: (token) => {

		}
	});
}

function setupForm() {
	let submitBtn = document.getElementById("submit");
	let form = document.getElementsByTagName("form")[0];
	form.addEventListener("submit", (event) => {
		event.preventDefault();
		sendRecommendationRequest();
	})

	let file = document.getElementById("file");
	if (!file) {
		return;
	}

	if (file.value) {
		submitBtn.disabled = false;
	}

	file.addEventListener("change", function () {
		if (this.value) {
			submitBtn.disabled = false;
		}
	})
}

function deleteForm() {
	let oldForm = document.querySelector("#recommendations-form");
	oldForm.remove();
}

function restoreForm() {
	let form = document.querySelector("#recommendations-form");
	document.querySelector("#time-reminder").style.display = "none";
	let submitBtn = form.querySelector("#submit");
	submitBtn.innerText = "Get Recommendations";
	submitBtn.setAttribute("aria-busy", "false");

	for (const elem of form.elements) {
		elem.disabled = false;
	}
}

function createErrorModal(heading, content) {
	let modal = document.querySelector("#error-modal");
	let modalHeading = modal.querySelector("#modal-heading");
	modalHeading.innerText = heading;
	let modalContent = modal.querySelector("#modal-content");
	modalContent.innerText = content;
	modal.setAttribute("open", "");

	let closeBtn = modal.querySelector(".close");
	closeBtn.addEventListener("click", () => {
		document.documentElement.classList.add("modal-is-closing");
		setTimeout(() => {
			document.documentElement.classList.remove("modal-is-closing", "modal-is-open");
			document.documentElement.style.removeProperty("--scrollbar-width");
			modal.removeAttribute("open");
		}, 400);
	});
}

function createRecCard(rec) {
	let card = document.createElement("div");
	card.className = "rec-card";

	let title = document.createElement("h3");
	title.className = "rec-card-title";
	title.textContent = rec.title;

	let titleEn = document.createElement("p");
	titleEn.className = "rec-card-title-en";
	titleEn.textContent = rec.title_en || rec.title;

	let link = document.createElement("a");
	link.className = "rec-card-link";
	link.href = "https://myanimelist.net/anime/" + rec.mal_id;
	link.target = "_blank";
	link.rel = "noopener noreferrer";
	link.textContent = "View on MAL";

	card.appendChild(title);
	card.appendChild(titleEn);
	card.appendChild(link);
	return card;
}

async function sendRecommendationRequest() {
	if (!captchaWidgetID) {
		createErrorModal("Captcha not loaded!", "Unable to load the captcha. Please try reloading the webpage.");
		return;
	}
	if (turnstile.isExpired(captchaWidgetID)) {
		turnstile.reset(captchaWidgetID);
	}
	if (!turnstile.getResponse()) {
		createErrorModal("You failed to verify the captcha!", "We failed to verify that you're a human. Please try again.");
		return;
	}

	let submitBtn = document.getElementById("submit");
	submitBtn.setAttribute("aria-busy", "true");
	submitBtn.innerText = "Please wait...";

	let formElements = document.getElementById("recommendations-form").elements;
	for (let i = 0; i < formElements.length; i++) {
		formElements[i].disabled = true;
	}

	let pTag = document.getElementById("time-reminder");
	pTag.style.display = "block";

	let disableNSFW = document.getElementById("nsfw");
	let formdata = new FormData();

	let file = document.getElementById("file");
	if (file) {
		formdata.append("file", file.files[0]);
	}

	formdata.append("cf-turnstile-response", turnstile.getResponse());

	turnstile.remove();

	let query = "";
	if (!disableNSFW.checked) {
		query = "?disable_nsfw=false";
	}

	fetch("/recommendations" + query, {
		method: "POST",
		body: formdata
	})
		.then(response => {
			response.json().then(
				jsonResp => {
					if (!jsonResp.success) {
						createErrorModal("Unable to get recommendations!", "The server didn't respond with a successful response: " + (jsonResp.message || "unknown error"));
						restoreForm();
						return;
					}
					deleteForm();
					let container = document.querySelector("#results-container");
					container.style.display = "flex";

					let grid = document.querySelector("#recs-grid");
					grid.innerHTML = "";

					jsonResp.results.forEach(rec => {
						const card = createRecCard(rec);
						grid.appendChild(card);
					});
				}
			).catch(err => {
				console.log("cannot convert response to json");
				console.log(response);
				console.log(err);
				createErrorModal("Unable to get recommendations!", "The server returned a non-json response. Please try again later.");
				restoreForm();
			})
		})
		.catch(err => {
			console.log("couldn't send a post request for recommendations to the server!");
			console.log(err);
			createErrorModal("Unable to interact with the server!", "We are unable to connect to our server. Please check your internet connection and try again.");
			restoreForm();
		})
}
