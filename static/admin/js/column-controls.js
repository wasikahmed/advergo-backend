/*
 * Per-changelist column show/hide + drag-to-resize for the Django admin
 * (Unfold theme). Unfold doesn't ship this, and some of our tables
 * (Quote requests, Orders) have enough columns that the row-actions menu
 * ends up off-screen. State is remembered per URL path in localStorage so
 * it survives reloads/filtering but doesn't leak between different models.
 */
(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState !== "loading") fn();
        else document.addEventListener("DOMContentLoaded", fn);
    }

    function storageKey() {
        return "admin-columns:" + window.location.pathname;
    }

    function loadState() {
        try {
            var raw = JSON.parse(localStorage.getItem(storageKey()));
            return { hidden: (raw && raw.hidden) || [], widths: (raw && raw.widths) || {} };
        } catch (e) {
            return { hidden: [], widths: {} };
        }
    }

    function saveState(state) {
        localStorage.setItem(storageKey(), JSON.stringify(state));
    }

    function setColumnVisible(col, bodyRows, visible) {
        var display = visible ? "" : "none";
        col.th.style.display = display;
        bodyRows.forEach(function (tr) {
            var cell = tr.children[col.index];
            if (cell) cell.style.display = display;
        });
    }

    function applyWidth(col, bodyRows, px) {
        var w = px + "px";
        [col.th].concat(
            bodyRows.map(function (tr) {
                return tr.children[col.index];
            })
        ).forEach(function (cell) {
            if (!cell) return;
            cell.style.width = w;
            cell.style.minWidth = w;
            cell.style.maxWidth = w;
            cell.style.overflow = "hidden";
            cell.style.textOverflow = "ellipsis";
        });
    }

    function buildColumns(theadRow) {
        var cells = Array.prototype.slice.call(theadRow.children);
        return cells
            .map(function (th, index) {
                var match = th.className.match(/column-(\S+)/);
                if (!match) return null;
                var labelSource = th.querySelector(".text") || th;
                var label = (labelSource.innerText || "").trim() || match[1];
                return { key: match[1], label: label, th: th, index: index };
            })
            .filter(Boolean);
    }

    function buildTogglePanel(columns, bodyRows, state) {
        var wrap = document.createElement("div");
        wrap.style.position = "relative";
        wrap.style.display = "inline-block";

        var btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = "Columns";
        btn.className =
            "text-xs font-medium border border-base-200 dark:border-base-700 rounded-default " +
            "px-3 py-1.5 hover:bg-base-50 dark:hover:bg-base-800 bg-white dark:bg-base-900";

        var panel = document.createElement("div");
        panel.className =
            "column-toggle-panel hidden bg-white dark:bg-base-800 border border-base-200 " +
            "dark:border-base-700 rounded-default shadow-lg p-2 mt-1 text-sm text-font-default-light " +
            "dark:text-font-default-dark";

        columns.forEach(function (col) {
            var label = document.createElement("label");
            label.className =
                "flex items-center gap-2 px-2 py-1 rounded-default hover:bg-base-50 " +
                "dark:hover:bg-base-700 cursor-pointer whitespace-nowrap";

            var checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.checked = state.hidden.indexOf(col.key) === -1;
            checkbox.addEventListener("change", function () {
                setColumnVisible(col, bodyRows, checkbox.checked);
                state.hidden = state.hidden.filter(function (k) {
                    return k !== col.key;
                });
                if (!checkbox.checked) state.hidden.push(col.key);
                saveState(state);
            });

            var span = document.createElement("span");
            span.textContent = col.label;

            label.appendChild(checkbox);
            label.appendChild(span);
            panel.appendChild(label);
        });

        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            panel.classList.toggle("hidden");
        });
        panel.addEventListener("click", function (e) {
            e.stopPropagation();
        });
        document.addEventListener("click", function () {
            panel.classList.add("hidden");
        });

        wrap.appendChild(btn);
        wrap.appendChild(panel);
        return wrap;
    }

    function attachResizeHandle(col, bodyRows, state) {
        var handle = document.createElement("div");
        handle.className = "column-resize-handle";
        handle.title = "Drag to resize column";
        col.th.appendChild(handle);

        handle.addEventListener("mousedown", function (e) {
            e.preventDefault();
            e.stopPropagation();
            var startX = e.clientX;
            var startWidth = col.th.getBoundingClientRect().width;
            handle.classList.add("is-resizing");

            function onMove(ev) {
                var next = Math.max(60, Math.round(startWidth + (ev.clientX - startX)));
                applyWidth(col, bodyRows, next);
            }
            function onUp() {
                document.removeEventListener("mousemove", onMove);
                document.removeEventListener("mouseup", onUp);
                handle.classList.remove("is-resizing");
                state.widths[col.key] = parseInt(col.th.style.width, 10);
                saveState(state);
            }
            document.addEventListener("mousemove", onMove);
            document.addEventListener("mouseup", onUp);
        });
    }

    function init() {
        var table = document.getElementById("result_list");
        if (!table) return;

        var theadRow = table.querySelector("thead tr");
        var wrapper = table.parentElement;
        if (!theadRow || !wrapper || wrapper.dataset.columnControlsInit) return;
        wrapper.dataset.columnControlsInit = "true";

        var bodyRows = Array.prototype.slice.call(table.querySelectorAll("tbody tr.data-row"));
        var columns = buildColumns(theadRow);
        if (columns.length === 0) return;

        var state = loadState();

        var toolbar = document.createElement("div");
        toolbar.className = "flex items-center justify-end mb-2";
        toolbar.appendChild(buildTogglePanel(columns, bodyRows, state));
        wrapper.parentElement.insertBefore(toolbar, wrapper);

        columns.forEach(function (col) {
            attachResizeHandle(col, bodyRows, state);
            if (state.hidden.indexOf(col.key) !== -1) {
                setColumnVisible(col, bodyRows, false);
            }
            if (state.widths[col.key]) {
                applyWidth(col, bodyRows, state.widths[col.key]);
            }
        });
    }

    ready(init);
})();
