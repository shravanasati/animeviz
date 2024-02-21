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
	graphContainer.classList.add("center-container");
	let summary = document.createElement("summary");
	summary.role = "button";
	summary.innerText = title;
	let img = document.createElement("img");
	img.src = "data:image/png;base64," + b64image;
	img.classList.add("graph-image");

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

function blobFromBase64String(base64String) {
	const byteCharacters = atob(base64String);
	const byteNumbers = new Array(byteCharacters.length);
	for (let i = 0; i < byteCharacters.length; i++) {
		byteNumbers[i] = byteCharacters.charCodeAt(i);
	}
	const byteArray = new Uint8Array(byteNumbers);
	const blob = new Blob([byteArray], { type: "image/png" });
	return blob;
}

async function downloadAll(results) {
	const downloadAllBtn = document.createElement("button");
	downloadAllBtn.style.textAlign = "center";
	downloadAllBtn.style.width = "fit-content";
	downloadAllBtn.style.padding = "10px 20px";
	downloadAllBtn.innerText = "Download All";
	downloadAllBtn.classList.add("outline");

	downloadAllBtn.addEventListener("click", async () => {
		downloadAllBtn.innerText = "Please wait...";
		downloadAllBtn.setAttribute("aria-busy", "true");
		const zip = new JSZip();
	
		for (const result of results) {
			const title = result.title;
			const img = result.image;
			const blob = blobFromBase64String(img);
			zip.file(`${snakeCase(title)}.png`, blob, { base64: true });
		}
		const content = await zip.generateAsync({ type: "blob" });
		const fileStream = streamSaver.createWriteStream("animevisualised_insights.zip", {
			size: content.size // Makes the percentage visiable in the download
		});
		const readableStream = content.stream();
		if (window.WritableStream && readableStream.pipeTo) {
			return readableStream.pipeTo(fileStream)
				.then(() => {
					console.log('done writing')
					downloadAllBtn.innerText = "Download All";
					downloadAllBtn.setAttribute("aria-busy", "false");
				})
				.catch((error) => { 
					console.log(`unable to write zip file: ${error}`)
					downloadAllBtn.innerText = "Download All";
					downloadAllBtn.setAttribute("aria-busy", "false");
				})
		}
	});
	return downloadAllBtn;
}

async function sendVisualizationRequest() {
	// add busy circle and change submit button text
	let submitBtn = document.getElementById("submit");
	console.log(submitBtn);
	submitBtn.setAttribute("aria-busy", "true");
	submitBtn.innerText = "Please wait...";

	// disable form
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
						alert("the visualization wasn't successfull");
						// todo handle error
						return;
					}
					deleteForm();
					let container = document.querySelector(".form-container");
					jsonResp.results.forEach(result => {
						const accordion = createGraphAccordion(result);
						container.appendChild(accordion);
					});

					downloadAll(jsonResp.results)
						.then((downloadAllBtn) => {
							container.appendChild(downloadAllBtn);
						})
						.catch((err) => {
							alert("unable to make a zip file");
							console.log(err);
						});
				}
			).catch(err => {
				console.log("cannot convert response to json");
				console.log(err);
				alert("the server returned a non-json response");
			})
		})
		.catch(err => {
			console.log("couldn't send a post request for visualization to the server!");
			console.log(err);
			// todo handle error
			alert("request failed, try again later");
		})
}
