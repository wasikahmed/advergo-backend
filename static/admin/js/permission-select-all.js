/*
 * Adds a "Select all" toggle to each app group in the grouped permissions
 * widget (apps/access_control) -- assigning a role previously meant
 * clicking every permission checkbox in a group individually.
 */
(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") fn();
        else document.addEventListener("DOMContentLoaded", fn);
    }

    function checkboxesIn(group) {
        var options = group.querySelector(".permission-group-options");
        return options ? Array.prototype.slice.call(options.querySelectorAll('input[type="checkbox"]')) : [];
    }

    function syncToggleState(toggle, checkboxes) {
        var checkedCount = checkboxes.filter(function (cb) {
            return cb.checked;
        }).length;
        var allChecked = checkboxes.length > 0 && checkedCount === checkboxes.length;
        toggle.checked = allChecked;
        toggle.indeterminate = checkedCount > 0 && !allChecked;
    }

    function buildToggle(checkboxes) {
        var label = document.createElement("label");
        label.className =
            "flex items-center gap-1.5 text-xs font-medium text-font-subtle-light " +
            "dark:text-font-subtle-dark cursor-pointer select-none shrink-0";

        var input = document.createElement("input");
        input.type = "checkbox";
        input.className = "permission-select-all";

        var span = document.createElement("span");
        span.textContent = "Select all";

        input.addEventListener("change", function () {
            var want = input.checked;
            checkboxes.forEach(function (cb) {
                // Unfold's checkboxes are Alpine-reactive (x-model driven,
                // for the row highlight styling) -- setting `.checked`
                // directly and dispatching a synthetic "change" doesn't
                // reliably update that state. A real .click() fires the
                // full native event sequence Alpine listens for, same as
                // an actual user click, so only toggle ones not already in
                // the wanted state (clicking one already there would flip
                // it the wrong way).
                if (cb.checked !== want) cb.click();
            });
        });

        label.appendChild(input);
        label.appendChild(span);
        return { label: label, input: input };
    }

    function initGroup(group) {
        if (group.dataset.selectAllInit) return;
        group.dataset.selectAllInit = "true";

        var header = group.querySelector(".permission-group-header");
        var checkboxes = checkboxesIn(group);
        if (!header || checkboxes.length === 0) return;

        var toggle = buildToggle(checkboxes);
        header.appendChild(toggle.label);
        syncToggleState(toggle.input, checkboxes);

        checkboxes.forEach(function (cb) {
            cb.addEventListener("change", function () {
                syncToggleState(toggle.input, checkboxes);
            });
        });
    }

    function init() {
        document.querySelectorAll(".permission-group").forEach(initGroup);
    }

    ready(init);
})();
