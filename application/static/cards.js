document.addEventListener("DOMContentLoaded", function () {

    // Initialize variables

    const navbar = document.querySelector(".mdl-layout__header--transparent");

    // Build observer

    const target = document.querySelector('#layout');

    const config = {
        childList: true,
        subtree: true
    };

    const observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            if (mutation.type === "childList") {
                mutation.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1 && node.matches('div')) {  // Check if the added node is an element and is a 'div'

                        modal_boot();

                        // if this node has id="mission-picker" then do something
                        if (node.id === "mission-picker") {
                            mission_picker();
                        }

                        if (node.id == "button_container") {
                            console.log("its working")
                            time_boot();
                        }

                        if (node.id.startsWith("event-")) {
                            event_click_handler();
                        }
                    }
                });
            }
        });
    });

    observer.observe(target, config);

    prevValue = 10;
    spacebarPressed = true;

    modal_boot();

    function time_boot() {
    // Event handler for your timeline-bar slider
        $("#timeline-bar").on("input change", function() {
            spacebarPressed = false
            const speed = $(this).val();
            // Emit 'change_speed' event to server with the speed value
            socket.emit('change_speed', speed);
            if (speed > 1) {
                prevValue = speed;
            }

        });

        $(document).keydown(function(e) {
            // Check if the pressed key is the spacebar (keyCode 32)
            if (e.keyCode === 32) {
                // Prevent the default action (scrolling)
                e.preventDefault();

                const slider = $("#timeline-bar");

                

                // If prevValue is null, store the current value and set the slider to 0
                if (spacebarPressed === false) {
                    prevValue = slider.val();
                    slider.val(0).trigger("input");  // Set value to 0 and trigger input event
                    slider.addClass('is-lowest-value');
                    spacebarPressed = true;
                } else {
                    // If prevValue is not null, set the s lider back to prevValue
                    slider.val(prevValue).trigger("input");  // Set value to prevValue and trigger input event
                    slider.removeClass('is-lowest-value');
                    spacebarPressed = false;
                }
            }
        });
    }

    function modal_boot() {

        // Your functions can be called here for the new divs
        dragElements(".modal-draggable");

        $(".mdl-textfield__input").each(function () {
            toggleButtonVisibility(this);
        });

        $(".mdl-textfield__input").on("input", function () {
            toggleButtonVisibility(this);
        });

        $(".textarea-wizard").each(function () {
            this.setAttribute("style", "height:" + (this.scrollHeight) + "px;overflow-y:hidden;");
        }).on("input", function () {
            this.style.height = "68px";
            this.style.height = (this.scrollHeight) + "px";
        });

        componentHandler.upgradeDom();

    }

    function event_click_handler() {
        $(".action").click(function () {
            selected_option = $(this).attr('id')
            selected_option_id = parseInt(selected_option.split("-")[1])-1
            event_id = $(this).parents('[event-id]').attr('event-id');
            socket.emit('execute_option', event_id, selected_option_id); 
          })   
    }

    function mission_picker() {
        // inner text


        // add click handler and apply css when clicked
        $(".story").click(function () {
            $(".story").removeClass("selected");

            $(this).toggleClass("selected");
            $("#mission-picker>.mdl-card__actions").removeClass("actions-disabled");

            // Step 2: Hide all buttons
            $("#mission-picker>.mdl-card__actions>.mdl-tooltip").addClass("hidden");
            // Step 3: Get the loop.index associated with the clicked story
            const storyIndex = $(this).attr("id").split("-")[1];
            // Step 4: Show the respective button
            $(`#tooltip-${storyIndex}`).removeClass("hidden");
        })
        
        $("#start-story").click(function () {
            selected_mission = $("#mission-picker .selected").attr('id')
            mission_id = parseInt(selected_mission.split("-")[1])-1
            event_id = $(this).parents('[event-id]').attr('event-id');
            socket.emit('execute_option', event_id, mission_id);    
        })
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

    function dragElements(className) {
        $(className).draggable({
            handle: ".header" // Only the .header element will initiate a drag.
        });
    };


    // function getDistanceFromElement(e, element) {
    //     const rect = element.getBoundingClientRect();
    //     const left = rect.left;
    //     const right = rect.right;
    //     const top = rect.top;
    //     const bottom = rect.bottom;
    //     const mouseX = e.clientX;
    //     const mouseY = e.clientY;

    //     const dx = Math.max(left - mouseX, 0, mouseX - right);
    //     const dy = Math.max(top - mouseY, 0, mouseY - bottom);

    //     return Math.sqrt(dx * dx + dy * dy);
    // }

    // // Event listener for mouse movement
    // document.addEventListener("mousemove", function (e) {
    //     const distance = getDistanceFromElement(e, navbar);
    //     const proximityRadius = 100;
    //     let opacity;

    //     if (distance < proximityRadius) {
    //         opacity = 1 - (distance / proximityRadius);
    //     } else {
    //         opacity = 0;
    //     }

    //     navbar.style.opacity = opacity;
    // });

});