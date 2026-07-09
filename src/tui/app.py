import traceback
from contextlib import redirect_stdout

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, RichLog, Static, Switch


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: thick $primary;
        background: $surface;
    }
    #question {
        column-span: 2;
        height: 1fr;
        content-align: center middle;
    }
    Button {
        width: 100%;
    }
    """

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.question, id="question"),
            Button("Cancel", variant="primary", id="no"),
            Button("Upgrade", variant="warning", id="yes"),
            id="dialog",
        )

    def on_mount(self) -> None:
        self.query_one("#no", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_cancel(self) -> None:
        self.dismiss(False)


EDITABLE_FIELDS = [
    "Name", "Instance", "Enabled", "Type", "Category", "Context", "Namespace",
    "Version_Pin", "Upgrade", "Target", "GitHub", "DockerHub",
    "Check_Current", "Check_Latest", "Esphome_Key", "Library_GitHub",
    "Helm_Values_File", "Extra_Manifests",
    "Current_Version", "Latest_Version", "Status", "Last_Checked", "Last_Upgraded",
    "Current_Library_Version", "Latest_Library_Version", "Notes",
]


class EditScreen(ModalScreen[dict | None]):
    """Form for editing every field of a single application row.

    Extra_Manifests is a list in storage but edited as one path per line; a
    blank Input for a text field clears it back to NULL on save (matching
    VersionManager.update_row_data's existing "" -> None convention).
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    CSS = """
    EditScreen {
        align: center middle;
    }
    #edit-dialog {
        width: 90;
        height: 40;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #edit-title {
        height: 1;
        content-align: center middle;
        text-style: bold;
    }
    #edit-fields {
        height: 1fr;
    }
    .field-row {
        height: 3;
    }
    .field-label {
        width: 22;
        content-align: left middle;
    }
    .field-row Input {
        width: 1fr;
    }
    #edit-buttons {
        height: 3;
        align: right middle;
    }
    #edit-buttons Button {
        margin-left: 2;
    }
    """

    def __init__(self, row_data: dict) -> None:
        super().__init__()
        self.row_data = row_data
        self._inputs: dict[str, Input] = {}
        self._enabled_switch: Switch | None = None

    def compose(self) -> ComposeResult:
        rows = []
        for field in EDITABLE_FIELDS:
            value = self.row_data.get(field, "")
            label = Label(f"{field}:", classes="field-label")
            if field == "Enabled":
                self._enabled_switch = Switch(value=bool(value))
                rows.append(Horizontal(label, self._enabled_switch, classes="field-row"))
            else:
                display_value = "\n".join(value) if isinstance(value, list) else str(value)
                widget = Input(value=display_value)
                self._inputs[field] = widget
                rows.append(Horizontal(label, widget, classes="field-row"))

        yield Vertical(
            Label(
                f"Edit {self.row_data.get('Name', '')} ({self.row_data.get('Instance', '')})",
                id="edit-title",
            ),
            VerticalScroll(*rows, id="edit-fields"),
            Horizontal(
                Button("Cancel", variant="primary", id="edit-cancel"),
                Button("Save", variant="success", id="edit-save"),
                id="edit-buttons",
            ),
            id="edit-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "edit-save":
            self._save()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _save(self) -> None:
        updates = {}
        for field, widget in self._inputs.items():
            original = self.row_data.get(field, "")
            if field == "Extra_Manifests":
                new_value = [line.strip() for line in widget.value.splitlines() if line.strip()]
                if new_value != (original or []):
                    updates[field] = new_value
            else:
                original_str = "\n".join(original) if isinstance(original, list) else str(original)
                if widget.value != original_str:
                    updates[field] = widget.value

        if self._enabled_switch is not None:
            new_enabled = self._enabled_switch.value
            if new_enabled != bool(self.row_data.get("Enabled", True)):
                updates["Enabled"] = new_enabled

        self.dismiss(updates)


class _LogWriter:
    """Redirects print() output from VersionManager onto the RichLog widget.

    VersionManager uses `print(..., end="")` for live progress (e.g. the AWX
    job-polling dots), which only makes sense on a real terminal that keeps
    appending to the same line. RichLog has no such concept — every write()
    call adds a new line — so an in-progress (no trailing newline yet) line is
    buffered and shown in a separate one-line status widget that gets updated
    in place; only completed lines are appended to the scrolling log.
    """

    def __init__(self, app: "VersionCheckerApp") -> None:
        self.app = app
        self._pending = ""

    def _call(self, func, *args) -> None:
        try:
            # sys.stdout is process-global, so this can fire on the app's own
            # thread (e.g. a stray print elsewhere) even though redirect_stdout
            # is only meant to capture the worker thread's output.
            self.app.call_from_thread(func, *args)
        except RuntimeError:
            func(*args)

    def write(self, text: str) -> None:
        if not text:
            return
        *complete_lines, self._pending = (self._pending + text).split("\n")
        log = self.app.query_one(RichLog)
        for line in complete_lines:
            if line:
                self._call(log.write, line)
        self._call(self.app.query_one("#status", Static).update, self._pending)

    def flush(self) -> None:
        pass


class VersionCheckerApp(App):
    TITLE = "Goepp Homelab Version Manager"

    CSS = """
    #table {
        height: 1fr;
    }
    #status {
        height: 1;
        color: $text-muted;
    }
    #log {
        height: 12;
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_select", "Select"),
        Binding("a", "select_all", "Select All"),
        Binding("v", "toggle_view", "Toggle View"),
        Binding("c", "check_all", "Check All"),
        Binding("C", "check_selected", "Recheck Selected"),
        Binding("u", "upgrade_selected", "Upgrade Selected"),
        Binding("e", "edit_selected", "Edit"),
        Binding("r", "refresh_view", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, vm):
        super().__init__()
        self.vm = vm
        self.selected: set[int] = set()
        self.view_mode = "updates"
        self.busy = False
        self.row_idx_map: list[int] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="table", cursor_type="row")
        yield Static(id="status")
        yield RichLog(id="log", markup=True, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Sel", "Name", "Instance", "Current", "Latest", "Status")
        self.refresh_table()

    def get_visible_rows(self) -> list[int]:
        rows = []
        for idx, note in enumerate(self.vm.notes):
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue
            if self.view_mode == "updates" and fm.get("status") != "Update Available":
                continue
            rows.append(idx)
        return rows

    def refresh_table(self) -> None:
        table = self.query_one(DataTable)
        cursor_row = table.cursor_row
        table.clear()
        self.row_idx_map = self.get_visible_rows()

        for idx in self.row_idx_map:
            fm = self.vm.notes[idx]["frontmatter"]
            mark = "✓" if idx in self.selected else ""
            status = fm.get("status") or ""
            icon = self.vm.STATUS_ICONS.get(status, "")
            table.add_row(
                mark,
                fm.get("name", ""),
                fm.get("instance", ""),
                fm.get("current_version") or "",
                fm.get("latest_version") or "",
                f"{icon} {status}".strip(),
                key=str(idx),
            )

        if self.row_idx_map:
            table.move_cursor(row=min(cursor_row, len(self.row_idx_map) - 1))

        view_label = "Updates" if self.view_mode == "updates" else "All Applications"
        self.sub_title = f"{view_label} — {len(self.row_idx_map)} apps, {len(self.selected)} selected"

    def _cursor_idx(self) -> list[int]:
        table = self.query_one(DataTable)
        pos = table.cursor_row
        if 0 <= pos < len(self.row_idx_map):
            return [self.row_idx_map[pos]]
        return []

    def action_toggle_select(self) -> None:
        cursor = self._cursor_idx()
        if cursor:
            idx = cursor[0]
            if idx in self.selected:
                self.selected.discard(idx)
            else:
                self.selected.add(idx)
            self.refresh_table()

    def action_select_all(self) -> None:
        visible = set(self.row_idx_map)
        if visible and visible <= self.selected:
            self.selected -= visible
        else:
            self.selected |= visible
        self.refresh_table()

    def action_toggle_view(self) -> None:
        self.view_mode = "all" if self.view_mode == "updates" else "updates"
        self.refresh_table()

    def action_refresh_view(self) -> None:
        self.refresh_table()

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        table = self.query_one(DataTable)
        table.loading = busy

    def _run_background(self, work, done_message: str) -> None:
        """Run `work` in the worker thread and guarantee busy state is cleared.

        If `work` raises (network blip, unexpected API response, timeout —
        all real possibilities against live infrastructure), the exception is
        logged instead of silently killing the worker, which would otherwise
        leave `table.loading` stuck True forever and the DataTable unresponsive
        to input (Textual treats a widget as non-interactive while loading).
        """
        try:
            with redirect_stdout(_LogWriter(self)):
                try:
                    work()
                except Exception:
                    print(f"ERROR: {traceback.format_exc()}")
        finally:
            self.call_from_thread(self._on_background_done, done_message)

    def action_check_all(self) -> None:
        if self.busy:
            return
        self._set_busy(True)
        self.query_one(RichLog).write("[bold]Starting check-all...[/bold]")
        self.run_worker(
            lambda: self._run_background(self.vm.check_all_applications, "Check-all complete"),
            thread=True,
        )

    def action_check_selected(self) -> None:
        if self.busy:
            return
        idxs = sorted(self.selected) if self.selected else self._cursor_idx()
        if not idxs:
            self.notify("No application selected or highlighted", severity="warning")
            return
        self._set_busy(True)
        self.query_one(RichLog).write(f"[bold]Rechecking {len(idxs)} application(s)...[/bold]")
        self.run_worker(
            lambda: self._run_background(lambda: self._do_recheck(idxs), "Recheck complete"),
            thread=True,
        )

    def _do_recheck(self, idxs: list[int]) -> None:
        for idx in idxs:
            self.vm.check_single_application(idx)

    def action_upgrade_selected(self) -> None:
        if self.busy:
            return
        if not self.selected:
            self.notify("No applications selected", severity="warning")
            return
        self.push_screen(
            ConfirmScreen(f"Upgrade {len(self.selected)} selected application(s)?"),
            self._handle_upgrade_confirm,
        )

    def _handle_upgrade_confirm(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        idxs = sorted(self.selected)
        self._set_busy(True)
        self.query_one(RichLog).write(f"[bold]Upgrading {len(idxs)} application(s)...[/bold]")
        self.run_worker(
            lambda: self._run_background(lambda: self._do_upgrade(idxs), "Upgrade run complete"),
            thread=True,
        )

    def _do_upgrade(self, idxs: list[int]) -> None:
        for idx in idxs:
            fm = self.vm.notes[idx]["frontmatter"]
            name = fm.get("name", "")
            instance = fm.get("instance", "")
            print(f"--- Upgrading {name} ({instance}) ---")
            self.vm.upgrade_application(name, instance=instance)
        print()
        print("--- Rechecking upgraded application(s) (may still show the old version if the upgrade job hasn't finished rolling out) ---")
        for idx in idxs:
            self.vm.check_single_application(idx)

    def action_edit_selected(self) -> None:
        if self.busy:
            return
        cursor = self._cursor_idx()
        if not cursor:
            self.notify("No application highlighted", severity="warning")
            return
        idx = cursor[0]
        row_data = self.vm.get_row_data(idx)
        self.push_screen(EditScreen(row_data), lambda updates: self._handle_edit_result(idx, updates))

    def _handle_edit_result(self, idx: int, updates: dict | None) -> None:
        if not updates:
            return
        self.vm.update_row_data(idx, updates)
        self.refresh_table()
        self.notify("Application updated")

    def _on_background_done(self, message: str) -> None:
        self._set_busy(False)
        self.selected.clear()
        self.refresh_table()
        self.query_one("#status", Static).update("")
        self.notify(message)
        # A widget with `loading = True` reports itself as unfocusable, so
        # focus can drift elsewhere (e.g. to the RichLog) during a long-running
        # operation and Textual does not restore it automatically once loading
        # clears — do it explicitly so arrow-key navigation keeps working.
        self.query_one(DataTable).focus()


def run_tui(vm) -> None:
    VersionCheckerApp(vm).run()
