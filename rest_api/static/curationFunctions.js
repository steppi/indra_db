// CURATION FUNCTIONS

// Variables
let latestSubmission = {
    'ddSelect': '',
    'ev_hash': '',
    'source_hash': '',
    'submit_status': 0
};

function slideToggle(id) {
    const el = document.querySelector(`#${id}`);
    if(!el.dataset.open_height) {
        el.dataset.open_height = el.offsetHeight;
    }
    if (el.dataset.open === "true") {
        el.dataset.open = "false";
        el.style.height = '0px';
    }
    else {
        el.dataset.open = "true";
        el.style.height = el.dataset.open_height + 'px';
    }
}


// Turn on all the toggle buttons and connect them to a funciton.
document.addEventListener('DOMContentLoaded', () => {

    // Turn on all the toggle buttons.
   document.querySelectorAll('.curation_toggle')
       .forEach(function(toggle) {
           toggle.onclick = function() {
               const clickedRow = document.querySelector(`#${this.dataset.parent_id}`);
               const cur_id = addCurationRow(clickedRow);
               this.onclick = function () {
                   slideToggle(cur_id);
               };
           };
           toggle.innerHTML = "&#9998;";
           toggle.style.display = 'inline-block';
       })
});


function submitButtonClick(clickEvent) {
    // Get mouseclick target, then parent's parent
    let pn = clickEvent.target.parentNode.parentNode;
    let pmid_row = pn.parentNode.previousSibling;
    let s = pn.getElementsByClassName("dropdown")[0]
              .getElementsByTagName("select")[0];

    // DROPDOWN SELECTION
    let err_select = s.options[s.selectedIndex].value;
    if (!err_select) {
        alert('Please select an error type or "correct" for the statement in the dropdown menu');
        return;
    }

    // TEXT BOX CONTENT
    // Get "form" node, then the value of "input"
    let user_text = pn
        .getElementsByClassName("form")[0]
        .getElementsByTagName("input")[0]
        .value;

    // Refuse submission if 'other' is selected without providing a description
    if (!user_text && err_select === "other") {
        alert('Must describe error when using option "other..."!');
        return;
    }

    // GET REFERENCE TO STATUS BOX (EMPTY UNTIL STATUS RECEIVED)
    let statusBox = pn.getElementsByClassName("submission_status")[0].children[0];

    // PMID
    // Get pmid_linktext content
    let pmid_text = pmid_row
        .getElementsByClassName("pmid_link")[0]
        .textContent.trim();

    // Icon 
    let icon = pmid_row.getElementsByClassName("curation_toggle")[0];

    // HASHES: source_hash & stmt_hash
    // source_hash == ev['source_hash'] == pmid_row.id; "evidence level"
    const source_hash = pmid_row.dataset.source_hash;
    // stmt_hash == hash == stmt_info['hash'] == table ID; "(pa-) statement level"
    const stmt_hash = pmid_row.parentElement.dataset.stmt_hash;

    // CURATION DICT
    // example: curation_dict = {'tag': 'Reading', 'text': '"3200 A" is picked up as an agent.', 'curator': 'Klas', 'ev_hash': ev_hash};
    let cur_dict = {
        'tag': err_select,
        'text': user_text,
        'ev_hash': source_hash
    };

    // console.log("source hash: " + source_hash)
    // console.log("stmt hash: " + stmt_hash)
    // console.log("Error selected: " + err_select);
    // console.log("User feedback: " + user_text);
    // console.log("PMID: " + pmid_text);
    // console.log("cur_dict");
    // console.log(cur_dict);

    // SPAM CONTROL: preventing multiple clicks of the same curation in a row
    // If the new submission matches latest submission AND the latest submission was
    // successfully submitted, ignore the new submission
    if (latestSubmission['ddSelect'] === err_select &
        latestSubmission['source_hash'] === source_hash &
        latestSubmission['stmt_hash'] === stmt_hash &
        latestSubmission['submit_status'] === 200) {
        alert('Already submitted curation successfully!');
        return;
    } else {
        latestSubmission['ddSelect'] = err_select;
        latestSubmission['source_hash'] = source_hash;
        latestSubmission['stmt_hash'] = stmt_hash;
    }
    let testing = false; // Set to true to test the curation endpoint of the API
    let response = submitCuration(cur_dict, stmt_hash, statusBox, icon, testing);
    console.log("Response from submission: ");
    console.log(response);
    return false;
}


// Submit curation
async function submitCuration(curation_dict, hash, statusBox, icon, test) {

    let _url = CURATION_ADDR + hash;

    if (test) {
        console.log("Submitting test curation...");
        _url += "&test";
    }
    // console.log("api key: " + api_key)
    console.log("url: " + _url);

    const resp = await fetch(_url, {
        method: 'POST',
        body: JSON.stringify(curation_dict),
        headers: {'Content-Type': 'application/json'}
    })
    latestSubmission['submit_status'] = resp.status;
    switch (resp.status) {
        case 200:
            statusBox.textContent = "Curation submitted successfully!";
            icon.style = "color: #00FF00"; // Brightest green
            break;
        case 400:
            statusBox.textContent = xhr.status + ": Bad Curation Data";
            icon.style = "color: #FF0000"; // Super red
            break;
        case 401:
            console.log("Authentication failure, trying again.");
            login(
              (type, data) => {
                  submitCuration(curation_dict, hash, statusBox, icon, test)
              },
              (type, data) => {
                  submitCuration(curation_dict, hash, statusBox, icon, test)
              }
            );
            break;
        case 404:
            statusBox.textContent = resp.status + ": Bad Link";
            icon.style = "color: #FF0000";
            break;
        case 500:
            statusBox.textContent = resp.status + ": Internal Server Error";
            icon.style = "color: #FF0000";
            break;
        case 504:
            statusBox.textContent = resp.status + ": Server Timeout";
            icon.style = "color: #58D3F7"; // Icy blue
            break;
        default:
            console.log("Uncaught submission error: check response");
            console.log("resp:\n", resp);
            statusBox.textContent = "Uncaught submission error; Code " + resp.status;
            icon.style = "color: #FF8000"; // Warning orange
            break;
    }

    return resp;
}
// Creates the dropdown div with the following structure
// <div class="dropdown" 
//      style="display:inline-block; vertical-align: middle;">
//     <select>
//         <option value="" selected disabled hidden>
//             Select error type...
//         </option>
//         <option value="correct">Correct</option>
//         <option value="entity_boundaries">Entity Boundaries</option>
//         <option value="grounding">Grounding</option>
//         <option value="no_relation">No Relation</option>
//         <option value="wrong_relation">Wrong Relation</option>
//         <option value="act_vs_amt">Activity vs. Amount</option>
//         <option value="polarity">Polarity</option>
//         <option value="negative_result">Negative Result</option>
//         <option value="hypothesis">Hypothesis</option>
//         <option value="agent_conditions">Agent Conditions</option>
//         <option value="mod_site">Modification Site</option>
//         <option value="other">Other...</option>
//     </select>
// </div>
function createDDDiv() {
    let ddContainer = document.createElement("div");
    ddContainer.className = "dropdown";
    ddContainer.style = "display:inline-block; vertical-align: middle; margin-left: 9%;";

    let ddSelect = document.createElement("select");

    // DROPDOWN OPTIONS
    // Default; This is the option placeholder
    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.selected = "selected";
    placeholderOption.disabled = "disabled";
    placeholderOption.hidden = "hidden";
    placeholderOption.textContent = "Select error type...";
    ddSelect.appendChild(placeholderOption);
    // 1 "correct" No Error;
    option1 = document.createElement("option");
    option1.value = "correct";
    option1.textContent = "Correct";
    ddSelect.appendChild(option1);
    // 2 "entity_boundaries" Entity Boundaries;
    option2 = document.createElement("option");
    option2.value = "entity_boundaries";
    option2.textContent = "Entity Boundaries";
    ddSelect.appendChild(option2);
    // 3 "grounding" Grounding;
    option3 = document.createElement("option");
    option3.value = "grounding";
    option3.textContent = "Grounding";
    ddSelect.appendChild(option3);
    // 4 "no_relation" No Relation;
    option4 = document.createElement("option");
    option4.value = "no_relation";
    option4.textContent = "No Relation";
    ddSelect.appendChild(option4);
    // 5 "wrong_relation" Wrong Relation Type;
    option5 = document.createElement("option");
    option5.value = "wrong_relation";
    option5.textContent = "Wrong Relation";
    ddSelect.appendChild(option5);
    // 6 "act_vs_amt" Activity vs. Amount
    option6 = document.createElement("option");
    option6.value = "act_vs_amt";
    option6.textContent = "Activity vs. Amount";
    ddSelect.appendChild(option6);
    // 7 "polarity" Polarity;
    option7 = document.createElement("option");
    option7.value = "polarity";
    option7.textContent = "Polarity";
    ddSelect.appendChild(option7);
    // 8 "negative_result" Negative Result;
    option8 = document.createElement("option");
    option8.value = "negative_result";
    option8.textContent = "Negative Result";
    ddSelect.appendChild(option8);
    // 9 "hypothesis" Hypothesis;
    option9 = document.createElement("option");
    option9.value = "hypothesis";
    option9.textContent = "Hypothesis";
    ddSelect.appendChild(option9);
    // 10 "agent_conditions" Agent Conditions;
    option10 = document.createElement("option");
    option10.value = "agent_conditions";
    option10.textContent = "Agent Conditions";
    ddSelect.appendChild(option10);
    // 11 "mod_site" Modification Site;
    option11 = document.createElement("option");
    option11.value = "mod_site";
    option11.textContent = "Modification Site";
    ddSelect.appendChild(option11);
    // 12 "other" Other...
    option12 = document.createElement("option");
    option12.value = "other";
    option12.textContent = "Other...";
    ddSelect.appendChild(option12);
    // Add more options by following the structure above
    ddContainer.appendChild(ddSelect);
    return ddContainer;
}
// Creates the text box div with the following structure:
// <div class="form" 
//      style="display:inline-block; 
//             vertical-align: middle; 
//             top: 0px">
//     <form name="user_feedback_form">
//         <input type="text" 
//                maxlength="240"
//                name="user_feedback" 
//                placeholder="Optional description (240 chars)" 
//                value=""
//                style="width: 360px;">
//     </form>
// </div>
function createTBDiv() {
    let tbContainer = document.createElement("div");
    tbContainer.className = "form";
    tbContainer.style = "display:inline-block; vertical-align: middle; margin-left: 4%;";

    let tbForm = document.createElement("form");
    tbForm.name = "user_feedback_form";

    let tbInput = document.createElement("input");
    tbInput.type = "text";
    tbInput.maxlength = "240";
    tbInput.name = "user_feedback";
    tbInput.placeholder = "Optional description (240 chars)";
    tbInput.value = "";
    tbInput.style = "width: 360px;";

    tbForm.appendChild(tbInput);

    tbContainer.appendChild(tbForm);

    return tbContainer;
}
// Creates the submit button div with the following structure
// <div class="curation_button"
//      style="display:inline-block; 
//             vertical-align: middle;">
//     <button
//         type="button"
//         class="btn btn-default btn-submit pull-right"
//         style="padding: 2px 6px">Submit
//     </button>
//     < script tag type="text/javascript">
//     $(".btn-submit").off("click").on("click", function(b){
//         // Get parent node
//         parent_node = b.target.parentNode.parentNode
//         // Get reference to closest row tag (jquery)
//         this_row = $(this).closest("tr")
//         submitButtonClick(clickEvent)
//     })
//     </ script tag>
// </div>
function createSBDiv() {
    let sbContainer = document.createElement("div");
    sbContainer.className = "curation_button";
    sbContainer.style = "display:inline-block; vertical-align: middle; margin-left: 4%;";

    let sbButton = document.createElement("button");
    sbButton.type = "button";
    sbButton.className = "btn btn-default btn-submit pull-right";
    sbButton.style = "padding: 2px 6px; border: solid 1px #878787;";
    sbButton.textContent = "Submit";
    sbButton.onclick = submitButtonClick; // ATTACHES SCRIPT TO BUTTON

    sbContainer.appendChild(sbButton);

    return sbContainer;
}
// Creates the textbox that tells the user the status of the submission
// <div class="submission_status"
//      style="display:inline-block; 
//             vertical-align: middle;">
// <a class="submission_status"></a>
// </div>
function createStatusDiv() {
    let statusContainer = document.createElement("div");
    statusContainer.className = "submission_status";
    statusContainer.style = "display:inline-block; vertical-align: middle; margin-left: 4%;";

    let textContainer = document.createElement("i");
    textContainer.textContent = "";

    statusContainer.appendChild(textContainer);

    return statusContainer;

}

// Append row to the row that executed the click
// <div class="row cchild" style="border-top: 1px solid #FFFFFF;">
//   <div class="col" style="padding: 0px; border-top: 1px solid #FFFFFF;">
//      <!-- form stuff -->
//   </div>
// </div>
function curationRowGenerator() {
    // Create new row element
    let newRow = document.createElement('div');
    newRow.className = 'row curation-row';
    newRow.innerHTML = null;
    newRow.style = "border-top: 1px solid #FFFFFF;";
    newRow.dataset.open = "true";

    // Create new td element
    let newTD = document.createElement('div');
    newTD.className = 'col';
    newTD.style = "padding: 0px; border-top: 1px solid #FFFFFF; white-space: nowrap; text-align: left;";
    // newTD.setAttribute("colspan", "4");

    // Add dropdown div
    let dropdownDiv = createDDDiv();
    newTD.appendChild(dropdownDiv);
    // Add textbox 
    let textBoxDiv = createTBDiv();
    newTD.appendChild(textBoxDiv);
    // Add submit button
    let buttonDiv = createSBDiv();
    newTD.appendChild(buttonDiv);
    // Add submission response textbox
    let statusDiv = createStatusDiv();
    newTD.appendChild(statusDiv);

    // Add td to table row
    newRow.appendChild(newTD);

    return newRow;
}
// Adds the curation row to current
function addCurationRow(clickedRow) {
    // Generate new row
    let curationRow = curationRowGenerator();
    curationRow.id = clickedRow.id + '-curation';

    // Append new row to provided row
    clickedRow.parentNode.insertBefore(curationRow, clickedRow.nextSibling);

    return curationRow.id;
}
