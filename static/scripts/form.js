window.addEventListener("load", submitButtonStateChanger)
var captchaWidgetID = null; // global variable to store the captcha widget

window.onloadTurnstileCallback = () => {
	captchaWidgetID = turnstile.render("#cf-turnstile", {
		sitekey: "0x4AAAAAAAU4_tLhgcruoYjU",
		callback: (token) => {

		}
	});
}

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

	// let captcha = document.querySelector("#cf-turnstile");
	// turnstile.render(captcha, {
	// 	sitekey: "0x4AAAAAAAU4_tLhgcruoYjU",
	// 	callback: (token) => {
	// 		console.log(token);
	// 	}
	// });

}

function deleteForm() {
	let oldForm = document.querySelector("#visualization-form");
	oldForm.remove();
}

function restoreForm() {
	let form = document.querySelector("#visualization-form");
	document.querySelector("#time-reminder").style.display = "none";
	let submitBtn = form.querySelector("#submit");
	submitBtn.innerText = "Visualize";
	submitBtn.setAttribute("aria-busy", "false");

	for (const elem of form.elements) {
		elem.disabled = false;
	}
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

function _createMatplotlibAccordion(result) {
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

function _createPlotlyAccordion(result) {
	const title = result.title;
	let snakeTitle = snakeCase(title);
	const figure = JSON.parse(result.figure);

	let details = document.createElement("details");

	let graphContainer = document.createElement("section");
	graphContainer.classList.add("center-container");
	let summary = document.createElement("summary");
	summary.role = "button";
	summary.innerText = title;

	let renderContainer = document.createElement("div");
	renderContainer.setAttribute("id", snakeTitle);
	// console.log(figure)
	Plotly.newPlot(renderContainer, figure.data, figure.layout, {
		toImageButtonOptions: {
			format: 'png', // one of png, svg, jpeg, webp
			filename: snakeTitle,
			scale: 1 // Multiply title/legend/axis/canvas sizes by this factor
		},
		displayModeBar: true,
		responsive: true
	});

	details.appendChild(summary);
	graphContainer.appendChild(renderContainer);
	details.appendChild(graphContainer);

	return details;
}

function createChartAccordion(result) {
	if (result.interactive) {
		// plotly has been used
		return _createPlotlyAccordion(result.result)
	} else {
		// matplotlib has been used
		return _createMatplotlibAccordion(result.result)
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
		// visibleModal = null;
		document.documentElement.classList.add("modal-is-closing");
		setTimeout(() => {
			document.documentElement.classList.remove("modal-is-closing", "modal-is-open");
			document.documentElement.style.removeProperty("--scrollbar-width");
			modal.removeAttribute("open");
		}, 400); // 400ms is animation duration
	});
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

function createSummarySection(summary) {
	const section = document.createElement("div");
	section.classList.add("summary-section");

	// Insight Banner
	const insightBanner = document.createElement("div");
	insightBanner.classList.add("insight-banner");
	const insightTitle = document.createElement("div");
	insightTitle.classList.add("insight-title");
	insightTitle.innerText = "Monthly Insight";
	const insightBody = document.createElement("p");
	insightBody.classList.add("insight-body");

	if (summary.finished_this_month > 0) {
		insightBody.innerText = `You've finished ${summary.finished_this_month} anime this month! You seem to be into ${summary.favorite_genre} lately.`;
	} else {
		insightBody.innerText = "You haven't finished any anime yet this month. Time to clear that backlog!";
	}

	insightBanner.appendChild(insightTitle);
	insightBanner.appendChild(insightBody);
	section.appendChild(insightBanner);

	// KPI Grid
	const grid = document.createElement("div");
	grid.classList.add("summary-grid");

	const kpis = [
		{ label: "Total Anime", value: summary.total_anime },
		{ label: "Completed", value: summary.completed },
		{ label: "Episodes", value: summary.total_episodes },
		{ label: "Mean Score", value: summary.mean_score },
		{ label: "Days Watched", value: summary.days_watched },
		{ label: "Hours Watched", value: summary.hours_watched }
	];

	kpis.forEach(kpi => {
		const card = document.createElement("div");
		card.classList.add("summary-card");
		const val = document.createElement("div");
		val.classList.add("summary-value");
		val.innerText = kpi.value;
		const lab = document.createElement("div");
		lab.classList.add("summary-label");
		lab.innerText = kpi.label;
		card.appendChild(val);
		card.appendChild(lab);
		grid.appendChild(card);
	});

	section.appendChild(grid);
	return section;
}

async function downloadAll(results) {
	// * currently supports matplotlib rendered charts only
	results = results.filter((r) => !r.interactive);
	results = results.map((r) => r.result);

	if (!results) {
		return;
	}

	const downloadAllBtn = document.createElement("button");
	downloadAllBtn.style.textAlign = "center";
	downloadAllBtn.style.width = "fit-content";
	downloadAllBtn.style.color = "white";
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
		const fileStream = streamSaver.createWriteStream("animeviz_insights.zip", {
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
					createErrorModal("Unable to make a zip file!", "We couldn't make a zip file of all the images. Please try again later.");
					downloadAllBtn.setAttribute("aria-busy", "false");
				})
		}
	});
	return downloadAllBtn;
}

async function sendVisualizationRequest() {
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

	// add busy circle and change submit button text
	let submitBtn = document.getElementById("submit");
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
	let interactiveCharts = document.getElementById("interactive");
	const data = {
		"disable_nsfw": disableNSFW.checked,
		"interactive_charts": interactiveCharts.checked
	}
	let formdata = new FormData();
	for (const key in data) {
		formdata.append(key, data[key]);
	}

	let file = document.getElementById("file");
	if (file) {
		formdata.append("file", file.files[0]);
	}

	formdata.append("cf-turnstile-response", turnstile.getResponse());

	turnstile.remove();

	fetch("/visualize", {
		method: "POST",
		body: formdata
	})
		.then(response => {
			response.json().then(
				jsonResp => {

					if (!jsonResp.success) {
						// alert("the visualization wasn't successfull");
						createErrorModal("Unable to visualize your data!", `The server didn't respond with a successfull response: ${jsonResp.message}`);
						restoreForm();
						return;
					}
					deleteForm();
					let container = document.querySelector(".form-container");

					if (jsonResp.summary) {
						const summarySection = createSummarySection(jsonResp.summary);
						container.appendChild(summarySection);
					}

					jsonResp.results.forEach(result => {
						const accordion = createChartAccordion(result);
						container.appendChild(accordion);
					});

					downloadAll(jsonResp.results)
						.then((downloadAllBtn) => {
							container.appendChild(downloadAllBtn);
						})
						.catch((err) => {
							// alert("unable to make a zip file");
							createErrorModal("Unable to make a zip file!", "We're unable to make a zip file of all the images. Please try again later.");
							console.log(err);
						});
				}
			).catch(err => {
				console.log("cannot convert response to json");
				console.log(response);
				console.log(err);
				createErrorModal("Unable to visualize!", "The server returned a non-json response. Please try again later.");
				restoreForm();
				// alert("the server returned a non-json response");
			})
		})
		.catch(err => {
			console.log("couldn't send a post request for visualization to the server!");
			console.log(err);
			createErrorModal("Unable to interact with the server!", "We are unable to connect to our server. Please check your internet connection and try again.");
			restoreForm();
			// alert("request failed, try again later");
		})
}
