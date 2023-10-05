let prevValue;
let spacebarPressed;

$(document).ready(function () {
    // GLOBAL VARIABLES

    stories = [];

    // SOCKET.IO

    // Initialize the mission picker

    socket.on('message_story_init', function (data) {
        $("#wizard").remove();
        $("#event-container").prepend(data.new_html_content);
    });

    socket.on('update_statmenu', function (data) {
        for (let item in data) {
            $(`#stat_${item} .stat_descriptor`).text(data[item]);
        }
    });

    socket.on('update_progress', function (data) {
        console.log(data);
        $('#b1').css('width', `${data.progress}%`);
    });

    socket.on('message_story', function (data) {
        $("#loader").remove();
        $("#event-container").prepend(data.new_html_content);
        stories = data.stories;
    });

    socket.on('blank_canvas', function (data) {
        $("#mission-picker").remove();
        $("#layout").prepend(data.new_html_content);
        $(".timeline").css('opacity', '100');
    });

    socket.on('update_time', function(data) {
        const { time, date, year } = data;
        $('#time').text(time);
        $('#date').text(date);
        $('#year').text(year);
    });

    socket.on('drop_event', function (data) {
        $("#event-container").prepend(data.new_html_content);
        actions = data.actions;
    });

    socket.on('populate_starting_state', function (data) {
        $("#event-container").prepend(data.new_html_content);
    });

    // Listen for 'update_time' event from server
    socket.on('update_time', function(data) {
        const { time, date, year } = data;
        $('#time').text(time);
        $('#date').text(date);
        $('#year').text(year);
    });

    socket.on('stop_time', function () {
        slider = $("#timeline-bar")
        slider.addClass('is-lowest-value');
        slider.val(0);
        spacebarPressed = true;
    });



    // Initialize the game

    socket.emit('app_init');



    // GENERAL

    // Button functionalities
    $("#save").on("click", function (event) {
        event.preventDefault();
        // Save story content
        sessionStorage.setItem("savedRelations", $("#relationsInput").val());
        sessionStorage.setItem("savedLifestyle", $("#lifestyleInput").val());
        sessionStorage.setItem("savedStory", $("#storyInput").val());
        // Save name, age, occupation
        sessionStorage.setItem("name", $("#name").val());
        sessionStorage.setItem("age", $("#age").val());
        sessionStorage.setItem("occupation", $("#occupation").val());
        // Save innerHTML of perksList and assetsList
        sessionStorage.setItem("perksList", $("#perksList").html());
        sessionStorage.setItem("assetsList", $("#assetsList").html());
        sessionStorage.setItem("placesList", $("#placesList").html());
        sessionStorage.setItem("personality", $("#personality_h").attr('value'));
        sessionStorage.setItem("class", $("#class_h").attr('value'));
        sessionStorage.setItem("worldview", $("#worldview_h").attr('value'));
    });
    
    // Open the debug modal
    $("#debugFAB").on("click", function (event) {
        if ($("#debugModal").css('display') == 'block') {
            $("#debugModal").css('display', 'none');
        } else {
            $("#debugModal").css('display', 'block');
        }
    });

    // Close the debug modal
    $("#closeDebugModal").on("click", function (event) {
        $("#debugModal").css('display', 'none');
    });

    // WIZARD

    // Retrieve story content
    $("#storyInput").parent()[0].MaterialTextfield.change(sessionStorage.getItem("savedStory"));

    $("#relationsInput").parent()[0].MaterialTextfield.change(sessionStorage.getItem("savedRelations"));
    $("#lifestyleInput").parent()[0].MaterialTextfield.change(sessionStorage.getItem("savedLifestyle"));

    // Retrieve and set name, age, occupation
    $("#name").parent()[0].MaterialTextfield.change(sessionStorage.getItem("name"));
    $("#age").parent()[0].MaterialTextfield.change(sessionStorage.getItem("age"));
    $("#occupation").parent()[0].MaterialTextfield.change(sessionStorage.getItem("occupation"));

    // Retrieve and populate perksList and assetsList
    $("#perksList").html(sessionStorage.getItem("perksList"));
    $("#assetsList").html(sessionStorage.getItem("assetsList"));
    $("#placesList").html(sessionStorage.getItem("placesList"));

    $(`.mdl-menu__item[data-val='${sessionStorage.getItem("worldview")}']`).attr('data-selected', 'true');
    $(`.mdl-menu__item[data-val='${sessionStorage.getItem("personality")}']`).attr('data-selected', 'true');
    $(`.mdl-menu__item[data-val='${sessionStorage.getItem("class")}']`).attr('data-selected', 'true');
    
    getmdlSelect.init('.getmdl-select');
    
    if (sessionStorage.getItem("personality") != null && sessionStorage.getItem("worldview") != "" && sessionStorage.getItem("class") != "" ) {
        let values = {}; 
        $('.stat_selector').each(function () {
            values[$(this).attr('name')] = $(this).val();
          });
        socket.emit('stat_change', values);
    };

    $('#advanced_toggle').click(function() {
        $('#create-sheet, #select-sheet').toggle();
    });

    $('#select-sheet').hide();
    $('#create-sheet').hide();

          // Function to emit the object to the backend

  // Listen for changes to any input element with class 'stat_selector'
  $('#game-sheet li').click(function () {
    let values = {};
    $('.stat_selector').each(function () {
      values[$(this).attr('name')] = $(this).val();
    });
    socket.emit('stat_change', values);
  });


    $("#json_toStory").on("click", function (event) {
        event.preventDefault();
        $("#storyForm .mdl-chip__text").each(function (i, v) {
            $this = $(this)
            $("#storyForm").append(
                $("<input type='hidden' />").attr({
                    name: $this.attr('name') + i,
                    value: $this.text()
                })
            )
        })    
    
        var formData = $('#storyForm').serializeArray();
        socket.emit('wizard_to_story', formData);
        
    });

    // Initialize Assets
    initializeComponent('assetsList', 'addAsset', 'newAsset');
    
    // Initialize Perks
    initializeComponent('perksList', 'addPerk', 'newPerk');

    initializeComponent('placesList', 'addPlace', 'newPlace');

    // Initialize Chips
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
    

    function initializeComponent(containerId, buttonId, inputId) {
        const $container = $(`#${containerId}`);
        const $button = $(`#${buttonId}`);
        const $input = $(`#${inputId}`);
      
        $button.on('click', function (event) {
            event.preventDefault();
          addChip($input.val(), $container[0]); // Assume addChip can handle a DOM element
          $input.val('');
        });
      
        $input.on('keydown', function (event) {
          if (event.keyCode === 13 || event.key === 'Enter') {
            event.preventDefault();
            addChip($input.val(), $container[0]);
            $input.val('');
          }
        });
      }

    function addChip(value, container) {
        if (value === '') return;

        const chip = document.createElement('span');
        chip.className = 'mdl-chip mdl-chip--deletable';
        chip.innerHTML = `
       <span name="${container.id}-item" class="mdl-chip__text">${value}</span>
       <button type="button" class="mdl-chip__action"><i class="material-icons">cancel</i></button>
   `;

        chip.querySelector('.mdl-chip__action').addEventListener('click', function () {
            chip.remove();
        });

        container.appendChild(chip);
    }

});