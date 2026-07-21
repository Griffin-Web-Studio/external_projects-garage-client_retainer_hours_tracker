// Work order checklist item timer: start/stop/pause/resume, live elapsed
// display, audible reminders, and the support-cap confirm-overage prompt.
//
// The server is authoritative for elapsed time and for every cap/threshold
// decision (see tracker/timers.py) - this module only displays what the
// server reports and polls to catch cap events; it never decides billing.

const POLL_INTERVAL_MS = 10_000;
const TICK_INTERVAL_MS = 1_000;

type BillingType = "" | "SUPPORT" | "SUPPORT_DEV_OVERAGE" | "DEVELOPMENT";
type ItemStatus = "NOT_STARTED" | "RUNNING" | "PAUSED" | "COMPLETED";

interface TimerStatusPayload {
  item_id: number;
  status: ItemStatus;
  billing_type: BillingType;
  elapsed_minutes: number;
  support_minutes: number;
  dev_minutes: number;
  should_pause_for_cap: boolean;
  should_hard_stop_for_daily_cap: boolean;
  owner: string | null;
  owner_id: number | null;
}

interface ErrorPayload {
  error: string;
}

const STATUS_BADGE_CLASSES: Record<ItemStatus, string> = {
  NOT_STARTED: "bg-slate-700/50 text-slate-400 ring-1 ring-white/10",
  RUNNING: "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20",
  PAUSED: "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20",
  COMPLETED: "bg-indigo-500/10 text-indigo-400 ring-1 ring-indigo-500/20",
};

const STATUS_LABELS: Record<ItemStatus, string> = {
  NOT_STARTED: "Not started",
  RUNNING: "Running",
  PAUSED: "Paused",
  COMPLETED: "Completed",
};

const TYPE_BADGE_CLASSES: Record<Exclude<BillingType, "">, string> = {
  SUPPORT: "bg-indigo-500/10 text-indigo-400",
  SUPPORT_DEV_OVERAGE: "bg-amber-500/10 text-amber-400",
  DEVELOPMENT: "bg-purple-500/10 text-purple-400",
};

const TYPE_LABELS: Record<Exclude<BillingType, "">, string> = {
  SUPPORT: "Support",
  SUPPORT_DEV_OVERAGE: "Support + Dev Overage",
  DEVELOPMENT: "Development",
};

function getCsrfToken(): string {
  const match = /(?:^|;\s*)csrftoken=([^;]+)/.exec(document.cookie);
  return match ? decodeURIComponent(match[1]) : "";
}

function isErrorPayload(body: unknown): body is ErrorPayload {
  return (
    typeof body === "object" &&
    body !== null &&
    "error" in body &&
    typeof (body as ErrorPayload).error === "string"
  );
}

async function requestStatus(
  url: string,
  method: "GET" | "POST",
  body?: Record<string, string>
): Promise<TimerStatusPayload> {
  const init: RequestInit = { method };

  if (method === "POST") {
    init.headers = {
      "X-CSRFToken": getCsrfToken(),
      "Content-Type": "application/x-www-form-urlencoded",
    };
    init.body = new URLSearchParams(body ?? {});
  }

  const res = await fetch(url, init);
  const data: unknown = await res.json();

  if (!res.ok) {
    throw new Error(isErrorPayload(data) ? data.error : "Something went wrong.");
  }

  return data as TimerStatusPayload;
}

function formatElapsed(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

// Browsers only allow audio to play from a context that was created (or
// resumed) during a genuine user gesture - a fresh AudioContext made from
// a setInterval callback (e.g. a reminder firing while the timer just
// ticks along) is silently suspended in most browsers. `unlockAudio()` is
// called from every button click (a real gesture) to create the context
// once and keep resuming it; `playDing()` then just reuses that same
// context from any callback, gesture or not.
let sharedAudioContext: AudioContext | null = null;

function unlockAudio(): void {
  try {
    const AudioContextCtor =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext;

    if (!sharedAudioContext) {
      sharedAudioContext = new AudioContextCtor();
    }

    if (sharedAudioContext.state === "suspended") {
      void sharedAudioContext.resume();
    }
  } catch {
    // Audio unavailable (unsupported browser, etc.) - the browser
    // Notification (if permitted) still carries the alert.
  }
}

// Short synthesised beep - no audio asset to source/license, and it keeps
// the feature self-contained. Only audible while this tab is open, audio
// has been unlocked by a prior click, and the browser hasn't blocked it.
function playDing(): void {
  if (!sharedAudioContext) {
    return;
  }

  try {
    const ctx = sharedAudioContext;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.4);
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  } catch {
    // Audio unavailable - the recorded time is correct server-side and
    // the Notification (if permitted) still carries the alert.
  }
}

// Browser Notification API - shows a system-level toast even if this tab
// isn't focused, as long as it's still open somewhere. Requires a one-
// time permission grant, requested (like unlockAudio) from a real click
// rather than on page load, since browsers may suppress an unsolicited
// prompt. This is a "tab must stay open" notification, not true push -
// it won't reach the user if the tab/browser has been closed entirely.
function requestNotificationPermission(): void {
  if ("Notification" in window && Notification.permission === "default") {
    void Notification.requestPermission();
  }
}

function notify(title: string, body: string): void {
  if (!("Notification" in window) || Notification.permission !== "granted") {
    return;
  }

  try {
    new Notification(title, { body });
  } catch {
    // Notification construction can fail in some contexts - the in-tab
    // ding/UI state still reflects the correct server truth regardless.
  }
}

class ItemTimer {
  private readonly root: HTMLElement;
  private readonly itemId: number;
  private readonly urls: {
    start: string;
    stop: string;
    confirmOverage: string;
    status: string;
    complete: string;
  };
  private readonly currentEmployeeId: number;
  private readonly reminderMinutes: number[];
  private readonly description: string;
  private readonly dingedThresholds = new Set<number>();

  private readonly elapsedEl: HTMLElement | null;
  private readonly statusBadgeEl: HTMLElement | null;
  private readonly typeBadgeEl: HTMLElement | null;
  private readonly actionsEl: HTMLElement | null;
  private readonly errorEl: HTMLElement | null;

  private state: TimerStatusPayload;
  private syncedAtMs = 0;
  private busy = false;
  private dingedCapAlready = false;

  constructor(root: HTMLElement, currentEmployeeId: number, reminderMinutes: number[]) {
    this.root = root;
    this.itemId = Number(root.dataset.itemId);
    this.urls = {
      start: root.dataset.startUrl ?? "",
      stop: root.dataset.stopUrl ?? "",
      confirmOverage: root.dataset.confirmOverageUrl ?? "",
      status: root.dataset.statusUrl ?? "",
      complete: root.dataset.completeUrl ?? "",
    };
    this.state = JSON.parse(root.dataset.status ?? "{}") as TimerStatusPayload;
    this.currentEmployeeId = currentEmployeeId;
    this.reminderMinutes = reminderMinutes;
    this.description = root.dataset.itemDescription ?? "this item";

    this.elapsedEl = root.querySelector("[data-elapsed-display]");
    this.statusBadgeEl = root.querySelector("[data-status-badge]");
    this.typeBadgeEl = root.querySelector("[data-type-badge]");
    this.actionsEl = root.querySelector("[data-timer-actions]");
    this.errorEl = root.querySelector("[data-timer-error]");

    this.applyState(this.state, false);
  }

  /** Whether this item needs periodic polling (running or paused items
   * can still change - completed/not-started ones won't without a
   * user action this instance already handles). */
  needsPolling(): boolean {
    return this.state.status === "RUNNING" || this.state.status === "PAUSED";
  }

  /** Recomputed from the latest known state on every call - `owner_id`
   * changes the moment a Start action succeeds, so this must never be
   * cached from the page's initial load. */
  private isMine(): boolean {
    return this.state.owner_id === this.currentEmployeeId;
  }

  isRunningLive(): boolean {
    return this.state.status === "RUNNING" && this.isMine();
  }

  tick(): void {
    if (!this.isRunningLive() || !this.elapsedEl) {
      return;
    }

    const liveElapsed =
      this.state.elapsed_minutes + (Date.now() - this.syncedAtMs) / 60_000;
    this.elapsedEl.textContent = formatElapsed(Math.floor(liveElapsed));

    if (this.state.billing_type === "SUPPORT") {
      for (const threshold of this.reminderMinutes) {
        if (liveElapsed >= threshold && !this.dingedThresholds.has(threshold)) {
          this.dingedThresholds.add(threshold);
          playDing();
          notify(
            "Timer reminder",
            `${threshold} minutes elapsed on "${this.description}".`
          );
        }
      }
    }
  }

  async poll(): Promise<void> {
    try {
      const status = await requestStatus(this.urls.status, "GET");
      this.applyState(status, true);
    } catch {
      // A failed poll just means the display is stale for one cycle -
      // not worth surfacing as a user-facing error.
    }
  }

  private async runAction(
    action: () => Promise<TimerStatusPayload>
  ): Promise<void> {
    if (this.busy) {
      return;
    }

    this.busy = true;
    this.setError(null);

    try {
      const status = await action();
      this.applyState(status, true);
    } catch (err) {
      this.setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      this.busy = false;
    }
  }

  private start(billingType?: BillingType): void {
    void this.runAction(() =>
      requestStatus(this.urls.start, "POST", billingType ? { billing_type: billingType } : {})
    );
  }

  private stop(): void {
    void this.runAction(() => requestStatus(this.urls.stop, "POST"));
  }

  private confirmOverage(): void {
    void this.runAction(() => requestStatus(this.urls.confirmOverage, "POST"));
  }

  private setError(message: string | null): void {
    if (!this.errorEl) {
      return;
    }

    this.errorEl.textContent = message ?? "";
    this.errorEl.classList.toggle("hidden", !message);
  }

  private applyState(status: TimerStatusPayload, wasCapEventPossible: boolean): void {
    const hitCapJustNow =
      wasCapEventPossible &&
      !this.dingedCapAlready &&
      (status.should_pause_for_cap || status.should_hard_stop_for_daily_cap) &&
      status.status === "PAUSED";

    this.state = status;
    this.syncedAtMs = Date.now();

    if (hitCapJustNow) {
      this.dingedCapAlready = true;
      playDing();
      const message = status.should_pause_for_cap
        ? `Support cap reached on "${this.description}" - confirm to `
          + "continue as overage."
        : `Daily development hour limit reached on "${this.description}".`;
      notify("Timer paused", message);
    }
    if (status.status !== "PAUSED") {
      this.dingedCapAlready = false;
    }

    if (this.elapsedEl) {
      this.elapsedEl.textContent = formatElapsed(status.elapsed_minutes);
    }

    if (this.statusBadgeEl) {
      this.statusBadgeEl.textContent = STATUS_LABELS[status.status];
      this.statusBadgeEl.className = `text-xs px-1.5 py-0.5 rounded ${STATUS_BADGE_CLASSES[status.status]}`;
    }

    if (this.typeBadgeEl) {
      if (status.billing_type) {
        this.typeBadgeEl.textContent = TYPE_LABELS[status.billing_type];
        this.typeBadgeEl.className = `text-xs px-1.5 py-0.5 rounded ${TYPE_BADGE_CLASSES[status.billing_type]}`;
        this.typeBadgeEl.classList.remove("hidden");
      } else {
        this.typeBadgeEl.classList.add("hidden");
      }
    }

    this.renderActions();
  }

  private renderActions(): void {
    if (!this.actionsEl) {
      return;
    }

    this.actionsEl.innerHTML = "";
    const status = this.state;

    if (status.status === "NOT_STARTED") {
      this.actionsEl.append(
        this.makeButton("Start (Support)", "bg-secondary hover:bg-secondary-alt text-primary", () =>
          this.start("SUPPORT")
        ),
        this.makeButton("Start (Support + Dev Overage)", "bg-white/5 hover:bg-white/10 text-slate-300", () =>
          this.start("SUPPORT_DEV_OVERAGE")
        ),
        this.makeButton("Start (Development)", "bg-white/5 hover:bg-white/10 text-slate-300", () =>
          this.start("DEVELOPMENT")
        )
      );
      return;
    }

    if (!this.isMine()) {
      return;
    }

    if (status.status === "RUNNING") {
      this.actionsEl.append(
        this.makeButton("Stop", "bg-white/5 hover:bg-white/10 text-slate-300", () => this.stop())
      );
      return;
    }

    if (status.status === "PAUSED") {
      if (status.should_pause_for_cap) {
        const note = document.createElement("p");
        note.className = "text-xs text-amber-300 mb-2";
        note.textContent = "Support cap reached - confirm to continue as overage.";
        this.actionsEl.append(note);
        this.actionsEl.append(
          this.makeButton(
            "Confirm & Continue as Overage",
            "bg-amber-500/10 hover:bg-amber-500/20 text-amber-300",
            () => this.confirmOverage()
          )
        );
      } else {
        if (status.should_hard_stop_for_daily_cap) {
          const note = document.createElement("p");
          note.className = "text-xs text-amber-300 mb-2";
          note.textContent = "Daily development hour limit reached.";
          this.actionsEl.append(note);
        }
        this.actionsEl.append(
          this.makeButton("Resume", "bg-secondary hover:bg-secondary-alt text-primary", () => this.start())
        );
      }

      this.actionsEl.append(this.makeLink("Complete", this.urls.complete));
    }
  }

  private makeButton(label: string, classes: string, onClick: () => void): HTMLButtonElement {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.className = `px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${classes}`;
    button.addEventListener("click", () => {
      // A real click is the one place browsers allow audio to unlock and
      // a notification permission prompt to appear - do both here so
      // later reminders/cap events (fired from timers, not clicks) can
      // actually reach the user.
      unlockAudio();
      requestNotificationPermission();
      onClick();
    });
    return button;
  }

  private makeLink(label: string, href: string): HTMLAnchorElement {
    const link = document.createElement("a");
    link.textContent = label;
    link.href = href;
    link.className =
      "px-3 py-1.5 text-xs font-medium rounded-full transition-colors bg-white/5 hover:bg-white/10 text-slate-300";
    return link;
  }
}

export function initWorkOrderTimers(): void {
  const page = document.querySelector<HTMLElement>("[data-timer-page]");

  if (!page) {
    return;
  }

  const currentEmployeeId = Number(page.dataset.employeeId);
  const reminderMinutes = (page.dataset.reminderMinutes ?? "")
    .split(",")
    .map((m) => Number(m.trim()))
    .filter((m) => !Number.isNaN(m));

  const timers = Array.from(page.querySelectorAll<HTMLElement>("[data-timer-item]")).map(
    (root) => new ItemTimer(root, currentEmployeeId, reminderMinutes)
  );

  window.setInterval(() => {
    for (const timer of timers) {
      timer.tick();
    }
  }, TICK_INTERVAL_MS);

  window.setInterval(() => {
    for (const timer of timers) {
      if (timer.needsPolling()) {
        void timer.poll();
      }
    }
  }, POLL_INTERVAL_MS);
}
