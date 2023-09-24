$(document).ready(function () {
    // Initialize Assets
    const assetsContainer = document.getElementById('assetsList');
    const addAssetButton = document.getElementById('addAsset');
    const newAsset = document.getElementById('newAsset');

    addAssetButton.addEventListener('click', function () {
        addChip(newAsset.value, assetsContainer);
        newAsset.value = '';
    });

    newAsset.addEventListener('keydown', function (event) {
        if (event.keyCode === 13 || event.key === 'Enter') {
            addChip(newAsset.value, assetsContainer);
            newAsset.value = '';
        }
    });


    // Initialize Significant Items
    const perkContainer = document.getElementById('perksList');
    const addPerkButton = document.getElementById('addPerk');
    const newPerk = document.getElementById('newPerk');

    addPerkButton.addEventListener('click', function () {
        addChip(newPerk.value, perkContainer);
        newPerk.value = '';
    });

    newPerk.addEventListener('keydown', function (event) {
        if (event.keyCode === 13 || event.key === 'Enter') {
            addChip(newPerk.value, perkContainer);
            newPerk.value = '';
        }
    });

    function addChip(value, container) {
        if (value === '') return;

        const chip = document.createElement('span');
        chip.className = 'mdl-chip mdl-chip--deletable';
        chip.innerHTML = `
        <span class="mdl-chip__text">${value}</span>
        <button type="button" class="mdl-chip__action"><i class="material-icons">cancel</i></button>
    `;

        chip.querySelector('.mdl-chip__action').addEventListener('click', function () {
            chip.remove();
        });

        container.appendChild(chip);
    }



    // Initialize variables
    let navbar = document.querySelector(".mdl-layout__header--transparent");

    function getDistanceFromElement(e, element) {
        const rect = element.getBoundingClientRect();
        const left = rect.left;
        const right = rect.right;
        const top = rect.top;
        const bottom = rect.bottom;
        const mouseX = e.clientX;
        const mouseY = e.clientY;

        const dx = Math.max(left - mouseX, 0, mouseX - right);
        const dy = Math.max(top - mouseY, 0, mouseY - bottom);

        return Math.sqrt(dx * dx + dy * dy);
    }

    // Event listener for mouse movement
    document.addEventListener("mousemove", function (e) {
        const distance = getDistanceFromElement(e, navbar);
        const proximityRadius = 100;
        let opacity;

        if (distance < proximityRadius) {
            opacity = 1 - (distance / proximityRadius);
        } else {
            opacity = 0;
        }

        navbar.style.opacity = opacity;
    });

    let accumulatedData = "";

    // Retrieve story content

    $("#storyInput").val(sessionStorage.getItem("savedStory"));
    $("#relationsInput").val(sessionStorage.getItem("savedRelations"));
    // Retrieve and set name, age, occupation
    $("#name").val(sessionStorage.getItem("name"));
    $("#age").val(sessionStorage.getItem("age"));
    $("#occupation").val(sessionStorage.getItem("occupation"));

    // Retrieve and populate perksList and assetsList
    $("#perksList").html(sessionStorage.getItem("perksList"));
    $("#assetsList").html(sessionStorage.getItem("assetsList"));



    // Save Button Functionality
    $("#save").on("click", function (event) {
        event.preventDefault();

        // Save story content

        sessionStorage.setItem("savedRelations", $("#relationsInput").val());
        sessionStorage.setItem("savedStory", $("#storyInput").val());

        // Save name, age, occupation
        sessionStorage.setItem("name", $("#name").val());
        sessionStorage.setItem("age", $("#age").val());
        sessionStorage.setItem("occupation", $("#occupation").val());

        // Save innerHTML of perksList and assetsList
        sessionStorage.setItem("perksList", $("#perksList").html());
        sessionStorage.setItem("assetsList", $("#assetsList").html());
    });

    try {
        let elements = document.querySelectorAll('.mdl-chip__action');
        elements.forEach(function (element) {
            element.addEventListener('click', function () {
                this.parentNode.remove();
            });
        });
    }
    catch (err) {
        console.log(err);
    }


    // Function to toggle button visibility based on input value
    function toggleButtonVisibility(inputElement) {
        let button = $(inputElement).siblings(".generateIcon");
        if ($(inputElement).val() === "") {
            button.show();
        } else {
            button.hide();
        }
    }

    // Run the toggle function for each input field when the page loads
    $(".mdl-textfield__input").each(function () {
        toggleButtonVisibility(this);
    });

    // Attach an input event listener to input fields inside the #fact-sheet div
    $(".mdl-textfield__input").on("input", function () {
        toggleButtonVisibility(this);
    });

    $("#input_toState").on("click", function (event) {
        event.preventDefault();
        console.log(accumulatedData);
        accumulatedData = "";
        console.log(accumulatedData);
        $.ajax({
            url: '/wizard',
            type: 'post',
            data: $('#storyForm').serialize() + "&output=json&function=input_toState",
        });
    });

    $("#input_toStateAnalysis").on("click", function (event) {
        event.preventDefault();
        accumulatedData = "";
        $("#textOutput").text("");
        $.ajax({
            url: '/wizard',
            type: 'post',
            data: $('#storyForm').serialize() + "&output=text&function=input_toStateAnalysis",  // Indicate the output type
        });
    });

    $("#json_toStory").on("click", function (event) {
        event.preventDefault();
        accumulatedData = "";
        $("#modal-container").css('display', 'block');
        $("#story_output_container").empty();
        $.ajax({
            url: '/wizard',
            type: 'post',
            data: $('#storyForm').serialize() + "&output=json&function=json_toStory",  // Indicate the output type
        });
    });

    socket.on('message_debug', function (data) {
        // Append new data to existing content in the #textOutput div
        accumulatedData += data.data;

        $("#textOutput").text(accumulatedData);
        socket.emit('updated_output', { updated_analysis_text: accumulatedData });
    });

    socket.on('message_story', function (data) {
        accumulatedData += data.data;

        try {

            // Parse the JSON string
            const parsedData = JSON.parse("{" + accumulatedData + "}");

            // Format newContent into HTML as per MDL guidelines
            const formattedContent = `
    <h5>${parsedData.title}</h5>
    <p>${parsedData.narrative}</p>
    <p><strong>Closure Conditions:</strong> ${parsedData.closure_conditions}</p>
    `;

            // Update the modal content
            $("#story_output_container").html(formattedContent);

            // Emit the updated story
            socket.emit('updated_output', { updated_story_json: parsedData });

        } catch (e) {
            // Fix incomplete JSON if needed
            const fixedData = fixIncompleteJSON(accumulatedData);
        }

        // Close functionalities
        $("#dialog_close").on("click", function (event) {
            event.preventDefault();
            $("#modal-container").css('display', 'none');
        });
    });


    socket.on('message_state', function (data) {
        // Append the incoming data to accumulatedData
        accumulatedData += data.data;

        try {
            let game_state = JSON.parse(accumulatedData);
            let newState = populateOverview(game_state);
            accumulatedData = "";

            // New code to extract state and emit it
            socket.emit('updated_output', { updated_state_text: newState });

        } catch (err) {
            console.error("Error 1 parsing JSON:", err);
            let fixedData = fixIncompleteJSON(accumulatedData);

            if (fixedData !== accumulatedData) {
                try {
                    let game_state = JSON.parse(fixedData);
                    let newState = populateOverview(game_state);
                    socket.emit('updated_output', { updated_state_text: newState });

                } catch (innerErr) {
                    console.error("Error 2 parsing JSON:", err);
                }
            }
        }
    });

    function fixIncompleteJSON(data) {
        let stack = [];
        const bracketMap = {
            "{": "}",
            "[": "]"
        };

        for (let char of data) {
            if (char === "{" || char === "[") {
                stack.push(char);
            } else if (char === "}" || char === "]") {
                stack.pop();
            }
        }

        // Create the complementary closing brackets for each unmatched opening bracket
        while (stack.length) {
            let lastBracket = stack.pop();
            data += bracketMap[lastBracket];
        }

        return data;
    }

    var itemsAdded = {
        player_holdings: [],
        player_relations: [],
        player_state: [],
        world_state: []
    };


    function populateOverview(game_state) {
        let newState = "";

        for (let section in game_state) {
            let sectionId = `${section}_section`;
            let sectionTitle = toTitleCase(section);

            if ($(`#${sectionId}`).length === 0) {
                $("#debugContent").append(`<div id="${sectionId}"><h2>${sectionTitle}</h2></div>`);
            }

            newState += sectionTitle + ':\n';

            if (section === "meta") {
                for (let key in game_state[section]) {
                    let formattedKey = toTitleCase(key);
                    let value = game_state[section][key];

                    if (!itemsAdded[section] || !itemsAdded[section].includes(value)) {
                        $(`#${sectionId}`).append(`<div class='tile'><span>${formattedKey}:</span><span>${value}</span></div>`);
                        itemsAdded[section] = itemsAdded[section] || [];
                        itemsAdded[section].push(value);
                    }
                    newState += `${formattedKey}: ${value}\n`;
                }
            } else {
                game_state[section].forEach(item => {
                    let formattedDescription = item.description ? item.description.replace(/\.$/, '') : '';  // Remove trailing punctuation
                    if (!itemsAdded[section] || !itemsAdded[section].includes(item.value)) {
                        $(`#${sectionId}`).append(`<div class='tile'><span>${item.key} (${formattedDescription}):</span><span>${item.value}</span></div>`);
                        itemsAdded[section] = itemsAdded[section] || [];
                        itemsAdded[section].push(item.value);
                    }
                    newState += `${item.key} (${formattedDescription}) ${item.value}\n`;
                });
            }
            newState += '\n';
        }

        return newState;
    }


    function toTitleCase(str) {
        return str.replace(/_/g, ' ') // replace underscores with spaces
            .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
    }

    function extractStateInfo() {
        let newState = "";

        $('#debugContent > div').each(function (index, sectionElement) {
            let sectionTitle = $(sectionElement).find('h2').text();
            newState += sectionTitle + ':\n';

            $(sectionElement).find('.tile').each(function (tileIndex, tileElement) {
                let spans = $(tileElement).find('span');
                let keyAndDescription = spans.eq(0).text(); // Key and description are in one span
                let value = spans.eq(1).text().replace(/^: /, "");  // Remove the ": " prefix before the value

                let match = keyAndDescription.match(/(.*?) \(=(.*?)\)/);  // Extract key and description
                if (match) {
                    let key = match[1];
                    let description = match[2];
                    newState += `${key} (${description}) ${value}\n`;
                } else {
                    // In case the key and description pattern doesn't match, just use the whole text.
                    newState += `${keyAndDescription} ${value}\n`;
                }
            });

            newState += '\n';
        });

        return newState;
    }


    dragElements(".modal-draggable");

    $(".textarea-wizard").each(function () {
        this.setAttribute("style", "height:" + (this.scrollHeight) + "px;overflow-y:hidden;");
    }).on("input", function () {
        this.style.height = 0;
        this.style.height = (this.scrollHeight) + "px";
    });

});

document.addEventListener("DOMContentLoaded", function () {
    // Reference to the debug modal and FAB button
    const debugModal = document.getElementById("debugModal");
    const debugFAB = document.getElementById("debugFAB");
    const debugModal_close = document.getElementById("closeDebugModal");

    // Open the debug modal
    debugFAB.addEventListener("click", function () {
        debugModal.style.display = "block";
    });

    // Close the debug modal
    debugModal_close.addEventListener("click", function () {
        debugModal.style.display = "none";
    });
});


function dragElements(className) {
    $(className).each(function () {
        var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
        var elmnt = this;
        var header = $(this).find(".header");

        if (header.length) {
            header.mousedown(dragMouseDown);
        } else {
            $(this).mousedown(dragMouseDown);
        }

        function dragMouseDown(e) {
            e.preventDefault();
            pos3 = e.clientX;
            pos4 = e.clientY;
            $(document).mouseup(closeDragElement);
            $(document).mousemove(elementDrag);
        }

        function elementDrag(e) {
            e.preventDefault();
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;
            elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
            elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
        }

        function closeDragElement() {
            $(document).off("mouseup", closeDragElement);
            $(document).off("mousemove", elementDrag);
        }

        // Initialize with a jQuery class

    });
}