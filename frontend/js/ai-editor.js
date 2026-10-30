/* =====================================================================
   ai-editor.js  -  Roomora AI Design Editor (text + voice, English + Hindi)

   HOW TO USE
   ----------
   Add ONE line before </body> in user.html:
        <script src="ai-editor.js"></script>
   (Optional: if your backend is not on this address, set it first:
        <script>window.ROOMORA_API = "http://127.0.0.1:8000";</script> )

   WHAT IT DOES
   ------------
   - Adds a floating "AI Editor" button + chat panel on the page.
   - The user TYPES or SPEAKS a command:  "make the wall green",  "दीवार हरी कर दो",
     "budget 1 lakh rakho".
   - Voice -> text is done by the BROWSER (Web Speech API, works in Chrome / Edge).
   - The text goes to our FastAPI backend:  POST /ai/edit-requirements
   - The backend returns updated requirements + a ready prompt.
   - We show the requirements as chips and put the prompt in your friend's
     "Describe your dream design" box (#designPrompt), so "Generate AI Design" uses it.
   ===================================================================== */
(function () {
    "use strict";

    var API = window.ROOMORA_API || "http://127.0.0.1:8000";
    var TOKEN_KEY = "roomoraToken";            // saved by the login page after login
    var REQ_KEY = "roomoraRequirements";       // so requirements survive a page refresh

    var EMPTY = {
        space_type: "Home", style: "", wall_color: "", main_colors: [], furniture: [],
        materials: [], lighting: "", budget_inr: null, extra_notes: ""
    };

    var requirements = loadRequirements();
    var history = [];                          // previous versions, for the Undo button
    var language = "en";                       // "en" or "hi"
    var speakReplies = false;
    var recognition = null;
    var listening = false;

    /* ------------------------------------------------------------ storage */
    function loadRequirements() {
        try {
            var saved = JSON.parse(localStorage.getItem(REQ_KEY));
            if (saved) return Object.assign({}, EMPTY, saved);
        } catch (e) { /* ignore broken data */ }
        return JSON.parse(JSON.stringify(EMPTY));
    }

    function saveRequirements() {
        try { localStorage.setItem(REQ_KEY, JSON.stringify(requirements)); } catch (e) { }
    }

    /* ------------------------------------------------------------ styles + HTML */
    var css = "\
    #rai-fab{position:fixed;right:20px;bottom:24px;z-index:9998;border:none;cursor:pointer;border-radius:999px;\
      padding:14px 20px;font-size:15px;font-weight:600;color:#fff;background:var(--olive-dark,#70764e);\
      box-shadow:0 8px 24px rgba(0,0,0,.25);}\
    #rai-panel{position:fixed;right:20px;bottom:90px;z-index:9999;width:380px;max-width:calc(100vw - 24px);\
      max-height:78vh;display:none;flex-direction:column;background:var(--surface-white,#fffdf8);\
      border:1px solid var(--border,#ddd7c8);border-radius:20px;box-shadow:0 20px 50px rgba(0,0,0,.3);\
      overflow:hidden;color:var(--text-dark,#3f4232);font-size:14px;}\
    #rai-panel.open{display:flex;}\
    #rai-head{background:var(--olive-deep,#5d6342);color:#fff;padding:12px 14px;display:flex;\
      align-items:center;justify-content:space-between;gap:8px;}\
    #rai-head strong{font-size:15px;}\
    #rai-head select,#rai-head button{border:none;border-radius:8px;padding:5px 8px;font-size:12px;cursor:pointer;}\
    #rai-reqs{padding:8px 12px;border-bottom:1px solid var(--border-light,#ebe6da);display:flex;flex-wrap:wrap;\
      gap:6px;background:var(--background-light,#f5f1e8);min-height:34px;}\
    .rai-chip{background:var(--sage-light,#dedfc5);border-radius:999px;padding:3px 10px;font-size:12px;}\
    .rai-chip b{font-weight:600;}\
    #rai-log{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;min-height:140px;}\
    .rai-msg{max-width:88%;padding:8px 12px;border-radius:14px;line-height:1.4;white-space:pre-wrap;}\
    .rai-user{align-self:flex-end;background:var(--olive,#8c9165);color:#fff;}\
    .rai-ai{align-self:flex-start;background:var(--sage-soft,#e9e8d6);}\
    #rai-try{padding:0 12px 8px;display:flex;flex-wrap:wrap;gap:6px;}\
    #rai-try button{border:1px dashed var(--olive,#8c9165);background:transparent;border-radius:999px;\
      padding:4px 10px;font-size:12px;cursor:pointer;color:inherit;}\
    #rai-bar{display:flex;gap:6px;padding:10px;border-top:1px solid var(--border-light,#ebe6da);}\
    #rai-input{flex:1;border:1px solid var(--border,#ddd7c8);border-radius:12px;padding:9px 12px;font-size:14px;\
      background:#fff;color:inherit;min-width:0;}\
    #rai-bar button{border:none;border-radius:12px;padding:0 12px;font-size:17px;cursor:pointer;\
      background:var(--olive-dark,#70764e);color:#fff;}\
    #rai-mic.on{background:#b85c52;animation:rai-pulse 1s infinite;}\
    #rai-undo{background:var(--brown,#927b62)!important;}\
    @keyframes rai-pulse{50%{opacity:.55}}\
    @media (max-width:700px){#rai-fab{bottom:84px}#rai-panel{bottom:140px;right:12px}}";

    var html = '\
    <div id="rai-head">\
      <strong>✨ AI Design Editor</strong>\
      <span>\
        <select id="rai-lang" title="Language for voice"><option value="en">English</option><option value="hi">हिन्दी</option></select>\
        <button id="rai-speak" title="Read replies aloud">🔇</button>\
        <button id="rai-close" title="Close">✕</button>\
      </span>\
    </div>\
    <div id="rai-reqs"></div>\
    <div id="rai-log"></div>\
    <div id="rai-try"></div>\
    <div id="rai-bar">\
      <button id="rai-undo" title="Undo last change">↩</button>\
      <input id="rai-input" type="text" maxlength="500" placeholder="Type or speak a command…" autocomplete="off">\
      <button id="rai-mic" title="Speak">🎤</button>\
      <button id="rai-send" title="Send">➤</button>\
    </div>';

    /* ------------------------------------------------------------ build the panel */
    var fab, panel, $log, $input, $mic, $reqs;

    function build() {
        var style = document.createElement("style");
        style.textContent = css;
        document.head.appendChild(style);

        fab = document.createElement("button");
        fab.id = "rai-fab";
        fab.textContent = "✨ AI Editor";
        document.body.appendChild(fab);

        panel = document.createElement("div");
        panel.id = "rai-panel";
        panel.innerHTML = html;                       // static HTML only - no user text in here
        document.body.appendChild(panel);

        $log = panel.querySelector("#rai-log");
        $input = panel.querySelector("#rai-input");
        $mic = panel.querySelector("#rai-mic");
        $reqs = panel.querySelector("#rai-reqs");

        fab.onclick = function () { panel.classList.toggle("open"); if (panel.classList.contains("open")) $input.focus(); };
        panel.querySelector("#rai-close").onclick = function () { panel.classList.remove("open"); };
        panel.querySelector("#rai-send").onclick = function () { send($input.value); };
        $input.onkeydown = function (e) { if (e.key === "Enter") send($input.value); };
        panel.querySelector("#rai-undo").onclick = undo;
        $mic.onclick = toggleMic;

        panel.querySelector("#rai-lang").onchange = function (e) {
            language = e.target.value;
            showTryButtons();
        };
        panel.querySelector("#rai-speak").onclick = function (e) {
            speakReplies = !speakReplies;
            e.target.textContent = speakReplies ? "🔊" : "🔇";
        };

        showTryButtons();
        renderRequirements();
        addMessage("ai", "Hi! Tell me what to change. You can type or tap 🎤 and speak, in English or Hindi.\n" +
            "नमस्ते! बताइए क्या बदलना है, लिखकर या 🎤 दबाकर बोलकर।");
    }

    /* ------------------------------------------------------------ small UI helpers */
    function addMessage(who, text) {
        var div = document.createElement("div");
        div.className = "rai-msg " + (who === "user" ? "rai-user" : "rai-ai");
        div.textContent = text;                       // textContent (NOT innerHTML) -> safe from HTML injection
        $log.appendChild(div);
        $log.scrollTop = $log.scrollHeight;
    }

    function showTryButtons() {
        var examples = language === "hi"
            ? ["दीवार का रंग हरा कर दो", "सोफे का रंग नीला कर दो", "बजट 2 लाख रखो"]
            : ["Make the wall sage green", "Add indoor plants", "Set budget to 50000"];
        var box = panel.querySelector("#rai-try");
        box.innerHTML = "";
        examples.forEach(function (text) {
            var b = document.createElement("button");
            b.textContent = text;
            b.onclick = function () { send(text); };
            box.appendChild(b);
        });
    }

    function renderRequirements() {
        $reqs.innerHTML = "";
        var r = requirements;
        var items = [
            ["Space", r.space_type], ["Style", r.style], ["Wall", r.wall_color],
            ["Colors", r.main_colors.join(", ")], ["Furniture", r.furniture.join(", ")],
            ["Materials", r.materials.join(", ")], ["Lighting", r.lighting],
            ["Budget", r.budget_inr ? "₹" + Number(r.budget_inr).toLocaleString("en-IN") : ""]
        ];
        items.forEach(function (pair) {
            if (!pair[1]) return;
            var chip = document.createElement("span");
            chip.className = "rai-chip";
            var label = document.createElement("b");
            label.textContent = pair[0] + ": ";
            chip.appendChild(label);
            chip.appendChild(document.createTextNode(pair[1]));
            $reqs.appendChild(chip);
        });
    }

    /* ------------------------------------------------------------ connect to the page */
    function applyToPage(prompt) {
        // 1) put the prompt in the "Describe your dream design" box
        var box = document.getElementById("designPrompt");
        if (box) { box.value = prompt; box.dispatchEvent(new Event("input", { bubbles: true })); }

        // 2) keep the "space type" drop-down in sync
        var select = document.getElementById("spaceType");
        if (select) {
            for (var i = 0; i < select.options.length; i++) {
                if (select.options[i].text.trim() === requirements.space_type) { select.selectedIndex = i; break; }
            }
        }
    }

    /* ------------------------------------------------------------ talk to the backend */
    async function send(text) {
        text = (text || "").trim();
        if (!text) return;
        $input.value = "";
        addMessage("user", text);

        var token = localStorage.getItem(TOKEN_KEY);
        if (!token) {
            addMessage("ai", "Please login first. / कृपया पहले लॉगिन करें।");
            return;
        }

        try {
            var response = await fetch(API + "/ai/edit-requirements", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
                body: JSON.stringify({ command: text, requirements: requirements, language: language })
            });

            if (response.status === 401) { addMessage("ai", "Your login expired. Please login again."); return; }
            if (response.status === 429) { addMessage("ai", "Too many commands. Wait a minute and try again."); return; }
            if (!response.ok) { addMessage("ai", "Sorry, something went wrong (error " + response.status + ")."); return; }

            var data = await response.json();

            if (data.changes.length > 0) {              // save the old version so Undo works
                var promptBox = document.getElementById("designPrompt");
                history.push({
                    requirements: JSON.parse(JSON.stringify(requirements)),
                    prompt: promptBox ? promptBox.value : ""
                });
                if (history.length > 20) history.shift();
            }
            requirements = Object.assign({}, EMPTY, data.requirements);
            saveRequirements();
            renderRequirements();
            applyToPage(data.prompt);

            addMessage("ai", data.reply);
            speak(data.reply);
        } catch (error) {
            addMessage("ai", "Cannot reach the server. Is the backend running at " + API + " ?");
        }
    }

    function undo() {
        if (history.length === 0) { addMessage("ai", "Nothing to undo."); return; }
        var previous = history.pop();
        requirements = previous.requirements;
        saveRequirements();
        renderRequirements();
        var box = document.getElementById("designPrompt");
        if (box) box.value = previous.prompt;           // put back the old prompt text too
        addMessage("ai", "Undone. / पिछला बदलाव वापस ले लिया।");
    }

    /* ------------------------------------------------------------ VOICE: speech -> text */
    function toggleMic() {
        var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            addMessage("ai", "Voice input is not supported in this browser. Please use Google Chrome or Microsoft Edge, or type your command.");
            return;
        }
        if (listening) { recognition.stop(); return; }

        recognition = new SR();
        recognition.lang = language === "hi" ? "hi-IN" : "en-IN";   // the browser cannot auto-detect, so we use the selected language
        recognition.interimResults = true;                           // show words while the user is still speaking
        recognition.continuous = false;
        var finalText = "";

        recognition.onstart = function () { listening = true; $mic.classList.add("on"); $input.placeholder = "Listening… / सुन रहा हूँ…"; };

        recognition.onresult = function (event) {
            var text = "";
            for (var i = 0; i < event.results.length; i++) {
                text += event.results[i][0].transcript;
                if (event.results[i].isFinal) finalText = text;
            }
            $input.value = text;
        };

        recognition.onerror = function (event) {
            if (event.error === "not-allowed") addMessage("ai", "Microphone permission is blocked. Allow the microphone in the browser address bar, and open the site using http://localhost (not by double-clicking the file).");
            else if (event.error === "no-speech") addMessage("ai", "I did not hear anything. Tap 🎤 and try again.");
            else addMessage("ai", "Voice error: " + event.error);
        };

        recognition.onend = function () {
            listening = false;
            $mic.classList.remove("on");
            $input.placeholder = "Type or speak a command…";
            if (finalText) send(finalText);               // speech finished -> send automatically
        };

        recognition.start();
    }

    /* ------------------------------------------------------------ OPTIONAL: read the reply aloud */
    function speak(text) {
        if (!speakReplies || !window.speechSynthesis) return;
        var utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = /[\u0900-\u097F]/.test(text) ? "hi-IN" : "en-IN";
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    }

    /* ------------------------------------------------------------ start */
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
    else build();

    // Other scripts (for example the Save Design button) can read the requirements:
    //     const req = window.RoomoraAI.getRequirements();
    window.RoomoraAI = {
        open: function () { panel.classList.add("open"); $input.focus(); },
        startVoice: function () { panel.classList.add("open"); if (!listening) toggleMic(); },
        runCommand: function (text) { panel.classList.add("open"); send(text); },
        getRequirements: function () { return JSON.parse(JSON.stringify(requirements)); },
        setRequirements: function (r) { requirements = Object.assign({}, EMPTY, r); saveRequirements(); renderRequirements(); }
    };
})();
