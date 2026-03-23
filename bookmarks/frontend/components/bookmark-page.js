import { HeadlessElement } from "../utils/element.js";

async function copyTextToClipboard(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
  } catch {
    // fall through to execCommand fallback (e.g. non-HTTPS or denied permission)
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand("copy");
  } finally {
    document.body.removeChild(ta);
  }
}

class BookmarkPage extends HeadlessElement {
  init() {
    this.update = this.update.bind(this);
    this.onToggleNotes = this.onToggleNotes.bind(this);
    this.onToggleBulkEdit = this.onToggleBulkEdit.bind(this);
    this.onBulkActionChange = this.onBulkActionChange.bind(this);
    this.onToggleAll = this.onToggleAll.bind(this);
    this.onToggleBookmark = this.onToggleBookmark.bind(this);
    this.onBookmarkActionsSubmit = this.onBookmarkActionsSubmit.bind(this);

    this.oldItems = [];
    this.update();
    document.addEventListener("bookmark-list-updated", this.update);
  }

  disconnectedCallback() {
    document.removeEventListener("bookmark-list-updated", this.update);
    this.formBookmarkActions?.removeEventListener(
      "submit",
      this.onBookmarkActionsSubmit,
      true,
    );
  }

  update() {
    const items = this.querySelectorAll("ul.bookmark-list > li");
    this.updateTooltips(items);
    this.updateNotesToggles(items, this.oldItems);
    this.updateBulkEdit(items, this.oldItems);
    this.oldItems = items;
  }

  updateTooltips(items) {
    // Add tooltip to title if it is truncated
    items.forEach((item) => {
      const titleAnchor = item.querySelector(".title > a");
      const titleSpan = titleAnchor.querySelector("span");
      if (titleSpan.offsetWidth > titleAnchor.offsetWidth) {
        titleAnchor.dataset.tooltip = titleSpan.textContent;
      } else {
        delete titleAnchor.dataset.tooltip;
      }
    });
  }

  updateNotesToggles(items, oldItems) {
    oldItems.forEach((oldItem) => {
      const oldToggle = oldItem.querySelector(".toggle-notes");
      if (oldToggle) {
        oldToggle.removeEventListener("click", this.onToggleNotes);
      }
    });

    items.forEach((item) => {
      const notesToggle = item.querySelector(".toggle-notes");
      if (notesToggle) {
        notesToggle.addEventListener("click", this.onToggleNotes);
      }
    });
  }

  onToggleNotes(event) {
    event.preventDefault();
    event.stopPropagation();
    event.target.closest("li").classList.toggle("show-notes");
  }

  updateBulkEdit() {
    if (this.hasAttribute("no-bulk-edit")) {
      return;
    }

    const checkedBookmarkIds = new Set();
    this.bookmarkCheckboxes?.forEach((checkbox) => {
      if (checkbox.checked) {
        checkedBookmarkIds.add(checkbox.value);
      }
    });

    // Remove existing listeners
    this.activeToggle?.removeEventListener("click", this.onToggleBulkEdit);
    this.actionSelect?.removeEventListener("change", this.onBulkActionChange);
    this.allCheckbox?.removeEventListener("change", this.onToggleAll);
    this.bookmarkCheckboxes?.forEach((checkbox) => {
      checkbox.removeEventListener("change", this.onToggleBookmark);
    });

    // Re-query elements
    this.activeToggle = this.querySelector(".bulk-edit-active-toggle");
    this.actionSelect = this.querySelector("select[name='bulk_action']");
    this.allCheckbox = this.querySelector(".bulk-edit-checkbox.all input");
    this.bookmarkCheckboxes = Array.from(
      this.querySelectorAll(".bulk-edit-checkbox:not(.all) input"),
    );
    this.selectAcross = this.querySelector("label.select-across");
    this.executeButton = this.querySelector("button[name='bulk_execute']");
    this.copyMarkdownButton = this.querySelector(
      "button[name='bulk_copy_markdown']",
    );

    // Add listeners
    this.activeToggle?.addEventListener("click", this.onToggleBulkEdit);
    this.actionSelect?.addEventListener("change", this.onBulkActionChange);
    this.allCheckbox?.addEventListener("change", this.onToggleAll);
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = checkedBookmarkIds.has(checkbox.value);
      checkbox.addEventListener("change", this.onToggleBookmark);
    });

    const allRowsChecked =
      this.bookmarkCheckboxes.length > 0 &&
      this.bookmarkCheckboxes.every((checkbox) => checkbox.checked);
    if (this.allCheckbox) {
      this.allCheckbox.checked = allRowsChecked;
    }
    this.updateSelectAcross(allRowsChecked);
    this.updateExecuteButton();

    this.formBookmarkActions = this.querySelector("form.bookmark-actions");
    this.formBookmarkActions?.removeEventListener(
      "submit",
      this.onBookmarkActionsSubmit,
      true,
    );
    this.formBookmarkActions?.addEventListener(
      "submit",
      this.onBookmarkActionsSubmit,
      true,
    );
    this.onBulkActionChange();

    // Update total number of bookmarks
    const totalHolder = this.querySelector("[data-bookmarks-total]");
    const total = totalHolder?.dataset.bookmarksTotal || 0;
    const totalSpan = this.selectAcross?.querySelector("span.total");
    if (totalSpan) {
      totalSpan.textContent = total;
    }
  }

  onToggleBulkEdit() {
    this.classList.toggle("active");
  }

  onBulkActionChange() {
    if (this.actionSelect) {
      this.dataset.bulkAction = this.actionSelect.value;
    }
    if (!this.executeButton) {
      return;
    }
    this.executeButton.setAttribute("data-confirm", "");
  }

  async onBookmarkActionsSubmit(event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    if (!form.classList.contains("bookmark-actions")) {
      return;
    }
    const submitter = event.submitter;
    if (!submitter || submitter.name !== "bulk_copy_markdown") {
      return;
    }
    event.preventDefault();
    const fd = new FormData(form, submitter);
    const csrf = form.querySelector("[name=csrfmiddlewaretoken]")?.value;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: fd,
        headers: {
          Accept: "application/json",
          ...(csrf ? { "X-CSRFToken": csrf } : {}),
        },
        credentials: "same-origin",
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const err =
          typeof data.error === "string"
            ? data.error
            : "Could not copy bookmarks as Markdown.";
        this.showMarkdownCopyToast(err, "error");
        return;
      }
      if (typeof data.markdown === "string") {
        await copyTextToClipboard(data.markdown);
      }
      const msg =
        typeof data.message === "string"
          ? data.message
          : "Copied bookmarks as Markdown.";
      this.showMarkdownCopyToast(msg, "success");
    } catch {
      this.showMarkdownCopyToast(
        "Could not copy bookmarks as Markdown.",
        "error",
      );
    }
  }

  showMarkdownCopyToast(message, variant) {
    let list = document.querySelector(".message-list");
    if (!list) {
      list = document.createElement("div");
      list.className = "message-list";
      document.querySelector("header")?.prepend(list);
    }
    const toast = document.createElement("div");
    toast.className = `toast toast-${variant} mb-4`;
    toast.textContent = message;
    list.prepend(toast);
  }

  onToggleAll() {
    if (!this.allCheckbox) {
      return;
    }
    const allChecked = this.allCheckbox.checked;
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = allChecked;
    });
    this.updateSelectAcross(allChecked);
    this.updateExecuteButton();
  }

  onToggleBookmark() {
    if (!this.allCheckbox) {
      return;
    }
    const allChecked = this.bookmarkCheckboxes.every((checkbox) => {
      return checkbox.checked;
    });
    this.allCheckbox.checked = allChecked;
    this.updateSelectAcross(allChecked);
    this.updateExecuteButton();
  }

  updateSelectAcross(allChecked) {
    if (!this.selectAcross) {
      return;
    }
    if (allChecked) {
      this.selectAcross.classList.remove("d-none");
    } else {
      this.selectAcross.classList.add("d-none");
      const input = this.selectAcross.querySelector("input");
      if (input) {
        input.checked = false;
      }
    }
  }

  updateExecuteButton() {
    const anyChecked = this.bookmarkCheckboxes.some((checkbox) => {
      return checkbox.checked;
    });
    if (this.executeButton) {
      this.executeButton.disabled = !anyChecked;
    }
    if (this.copyMarkdownButton) {
      this.copyMarkdownButton.disabled = !anyChecked;
    }
  }
}

customElements.define("ld-bookmark-page", BookmarkPage);
