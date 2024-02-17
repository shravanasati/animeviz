window.addEventListener("load", submitButtonStateChanger)

function submitButtonStateChanger() {
	let submitBtn = document.getElementById("submit");

	let form = document.getElementsByTagName("form")[0];
	form.addEventListener("submit", (event) => {
		event.preventDefault();
		sendVisualizationRequest();
	})

	let file = document.getElementById("file");
	// this file input is present only if the user is not authenticated
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
	const form = document.querySelector("#visualization-form");
	form.remove();
}

function snakeCase(text) {
	let snake = "";
	for (const char of text) {
		if (char == " ") {
			snake += "_";
			continue;
		}
		snake += char.toLowerCase();
	}
	return snake;
}

function createGraphAccordion(result) {
	let b64image = result.image;
	let title = result.title;

	let details = document.createElement("details");

	let graphContainer = document.createElement("section");
	graphContainer.className = "center-container";
	let summary = document.createElement("summary");
	summary.role = "button";
	summary.innerText = title;
	let img = document.createElement("img");
	img.src = "data:image/jpeg;base64," + b64image;
	img.className = "graph-image";

	let downloadBtn = document.createElement("a");
	downloadBtn.role = "button";
	downloadBtn.href = img.src;
	downloadBtn.download = snakeCase(title + ".png");
	downloadBtn.textContent = "Download";
	downloadBtn.classList.add("outline");

	details.appendChild(summary);
	graphContainer.appendChild(img);
	graphContainer.appendChild(downloadBtn);
	details.appendChild(graphContainer);

	return details;
}

async function downloadAll(results) {
	console.log("download all called");
	const zip = new JSZip();

	for (const result of results) {
		const title = result.title;
		const img = result.image;
		const blob = await fetch(img).then(r => r.blob());
		zip.file(`${snakeCase(title)}.png`, blob, { base64: true });
	}
	const content = await zip.generateAsync({ type: "blob" });
	const url = URL.createObjectURL(content);
	const a = document.createElement('a');
	a.href = url;
	a.role = "button";
	a.download = 'insights.zip';
	// a.click();
}

async function sendVisualizationRequest() {
	// add busy circle and change submit button text
	let submitBtn = document.getElementById("submit");
	console.log(submitBtn);
	submitBtn.setAttribute("aria-busy", "true");
	submitBtn.innerText = "Please wait...";

	let formElements = document.getElementById("visualization-form").elements;
	for (let i = 0; i < formElements.length; i++) {
		formElements[i].disabled = true;
	}

	let pTag = document.getElementById("time-reminder");
	pTag.style.display = "block";


	// fetch form data and post it
	let disableNSFW = document.getElementById("nsfw");
	const data = {
		"disable_nsfw": disableNSFW.checked,
	}
	let formdata = new FormData();
	for (const key in data) {
		formdata.append(key, data[key]);
	}

	let file = document.getElementById("file");
	if (file) {
		formdata.append("file", file.files[0]);
	}

	fetch("/visualize", {
		method: "POST",
		body: formdata
	})
		.then(response => {
			response.json().then(
				jsonResp => {

					console.log(jsonResp);
					if (!jsonResp.success) {
						// todo handle error
						return;
					}
					deleteForm();
					let container = document.querySelector(".form-container");
					jsonResp.results.forEach(result => {
						const accordion = createGraphAccordion(result);
						container.appendChild(accordion);
					});

					let downloadAllButton = document.createElement("a");
					downloadAllButton.role = "button";
					downloadAllButton.innerText = "Download All"
					downloadAllButton.addEventListener("click", downloadAll(jsonResp.results));
					downloadAllButton.classList.add("outline");
					container.appendChild(downloadAllButton);
				}
			).catch(err => {
				console.log("cannot convert response to json");
				console.log(err);
			})
		})
		.catch(err => {
			console.log("couldn't send a post request for visualization to the server!");
			console.log(err);
			// todo handle error
			alert("request failed, try again later");
		})
}
