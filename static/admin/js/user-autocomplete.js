/*
 * Django's autocomplete.js (admin/js/autocomplete.js) initializes every
 * `.admin-autocomplete` <select> as a plain-text Select2 -- there's no hook
 * to customize just one field's rendering from that file. So this script
 * re-initializes all of them with a templateResult that shows the avatar
 * returned by AvatarAutocompleteJsonView (apps/core/autocomplete.py) next to
 * each name -- but only when the JSON result actually included an "avatar"
 * key (only User-model results get one; every other autocomplete -- Category,
 * Product, Fabric, ... -- falls through to plain text, unaffected).
 *
 * Note this can't be scoped upfront via the <select>'s data-model-name
 * attribute: that attribute names the *source* model owning the field (e.g.
 * "order" for Order.customer), not the target model being searched ("user"),
 * so which fields resolve to User isn't knowable from the DOM alone.
 *
 * The already-selected/closed box (templateSelection) is intentionally left
 * as Django's default plain text: the initially-selected <option> is
 * rendered server-side by the widget itself, never touching the JSON
 * autocomplete view, so there's no avatar URL available for it here.
 */
(function () {
    "use strict";

    function renderResult(result) {
        if (result.loading || !result.id || result.avatar === undefined) {
            return result.text;
        }
        var wrapper = document.createElement("span");
        wrapper.className = "flex items-center gap-2";

        var box = document.createElement("span");
        box.className =
            "h-[22px] min-w-[22px] w-[22px] rounded-full bg-cover bg-center bg-no-repeat " +
            "bg-base-200 dark:bg-base-700 font-semibold flex items-center justify-center text-[10px]";
        if (result.avatar) {
            box.style.backgroundImage = "url('" + result.avatar + "')";
        } else {
            box.textContent = result.initial || "?";
        }

        var label = document.createElement("span");
        label.textContent = result.text;

        wrapper.appendChild(box);
        wrapper.appendChild(label);
        return wrapper;
    }

    function upgrade(select) {
        var $ = django.jQuery;
        var $select = $(select);
        if ($select.data("select2")) {
            $select.select2("destroy");
        }
        $select.select2({
            ajax: {
                data: function (params) {
                    return {
                        term: params.term,
                        page: params.page,
                        app_label: select.dataset.appLabel,
                        model_name: select.dataset.modelName,
                        field_name: select.dataset.fieldName,
                    };
                },
            },
            templateResult: renderResult,
        });
    }

    function upgradeAll(root) {
        var selects = (root || document).querySelectorAll(
            'select.admin-autocomplete:not([name*="__prefix__"])'
        );
        selects.forEach(upgrade);
    }

    // Unfold's SCRIPTS render before Django's own jQuery/Select2/autocomplete.js
    // bundle, so a DOMContentLoaded handler here would run (and get
    // immediately clobbered by) Django's own djangoAdminSelect2() init,
    // which fires later on that same event. `load` always fires after every
    // DOMContentLoaded handler has run, so upgrading there reliably wins.
    function ready(fn) {
        if (document.readyState === "complete") fn();
        else window.addEventListener("load", fn);
    }

    ready(function () {
        upgradeAll(document);
    });

    document.addEventListener("formset:added", function (event) {
        upgradeAll(event.target);
    });
})();
