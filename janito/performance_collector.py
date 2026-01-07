from collections import defaultdict, Counter
from janito.event_bus.handler import EventHandlerBase
import janito.driver_events as driver_events
import janito.report_events as report_events
import janito.tooling.tool_events as tool_events


class PerformanceCollector(EventHandlerBase):
    _last_request_usage = None

    """
    Aggregates performance metrics and statistics from LLM driver and report events.
    Collects timing, token usage, status, error, turn, content part, and tool usage data.
    Also tracks request durations.
    """

    def __init__(self):
        super().__init__(driver_events, report_events, tool_events)
        # Aggregated stats
        self.total_requests = 0
        self.status_counter = Counter()
        self.token_usage = defaultdict(
            int
        )  # keys: total_tokens, prompt_tokens, completion_tokens
        self.error_count = 0
        self.error_messages = []
        self.error_exceptions = []
        self.total_turns = 0
        self.generation_finished_count = 0
        self.content_part_count = 0
        # Duration tracking
        self._request_start_times = dict()  # request_id -> timestamp
        self._durations = []  # list of elapsed times (seconds)
        # Tool stats
        self.total_tool_events = 0
        self.tool_names_counter = Counter()
        self.tool_error_count = 0
        self.tool_error_messages = []
        self.tool_action_counter = Counter()
        self.tool_subtype_counter = Counter()
        # Raw events for reference
        self._events = []

    def on_RequestStarted(self, event):
        self._events.append(("RequestStarted", event))
        # Store the start time if possible
        # Assumes 'event' has a unique .request_id and a .timestamp (in seconds)
        request_id = event.request_id
        timestamp = event.timestamp
        if request_id is not None and timestamp is not None:
            self._request_start_times[request_id] = timestamp

    def on_RequestFinished(self, event):
        self._events.append(("RequestFinished", event))
        # Calculate and record the duration if start time is available
        request_id = getattr(event, "request_id", None)
        finish_time = getattr(event, "timestamp", None)
        if request_id is not None and finish_time is not None:
            start_time = self._request_start_times.pop(request_id, None)
            if start_time is not None:
                delta = finish_time - start_time
                if hasattr(delta, "total_seconds"):
                    self._durations.append(delta.total_seconds())
                else:
                    self._durations.append(float(delta))
        self.total_requests += 1
        self.status_counter[getattr(event, "status", None)] += 1
        usage = getattr(event, "usage", None)
        if usage:
            self._last_request_usage = usage.copy()
            for k, v in usage.items():
                if isinstance(v, (int, float)):
                    self.token_usage[k] += v
        # Error handling
        if getattr(event, "status", None) in ("error", "cancelled"):
            self.error_count += 1
            self.error_messages.append(getattr(event, "error", None))
            self.error_exceptions.append(getattr(event, "exception", None))

    def on_GenerationFinished(self, event):
        self._events.append(("GenerationFinished", event))
        self.generation_finished_count += 1
        self.total_turns += event.total_turns

    def on_ContentPartFound(self, event):
        self._events.append(("ContentPartFound", event))
        self.content_part_count += 1

    def on_ToolCallStarted(self, event):
        self._events.append(("ToolCallStarted", event))
        self.total_tool_events += 1
        self.tool_names_counter[event.tool_name] += 1

    def on_ReportEvent(self, event):
        self._events.append(("ReportEvent", event))
        # Only count errors for reporting
        if event.subtype:
            self.tool_subtype_counter[str(event.subtype)] += 1
            if str(event.subtype).lower() == "error":
                self.tool_error_count += 1
                self.tool_error_messages.append(event.message)

    # --- Aggregated Data Accessors ---
    def get_average_duration(self):
        if not self._durations:
            return 0.0
        return sum(self._durations) / len(self._durations)

    def get_total_requests(self):
        return self.total_requests

    def get_status_counts(self):
        return dict(self.status_counter)

    def get_token_usage(self):
        return dict(self.token_usage)

    def get_error_count(self):
        return self.error_count

    def get_error_messages(self):
        return list(self.error_messages)

    def get_total_turns(self):
        return self.total_turns

    def get_average_turns(self):
        if self.generation_finished_count == 0:
            return 0.0
        return self.total_turns / self.generation_finished_count

    def get_content_part_count(self):
        return self.content_part_count

    # --- Tool Stats Accessors ---
    def get_total_tool_events(self):
        return self.total_tool_events

    def get_tool_names_counter(self):
        return dict(self.tool_names_counter)

    def get_tool_error_count(self):
        return self.tool_error_count

    def get_tool_error_messages(self):
        return list(self.tool_error_messages)

    def get_tool_action_counter(self):
        return dict(self.tool_action_counter)

    def get_tool_subtype_counter(self):
        return dict(self.tool_subtype_counter)

    def get_all_events(self):
        return list(self._events)

    def get_last_request_usage(self):
        """
        Returns the usage dict (tokens) from the most recent RequestFinished event, or None if not available.
        """
        return self._last_request_usage.copy() if self._last_request_usage else None

    def reset_last_request_usage(self):
        """
        Clears the most recent usage dict. Use this (e.g. on session reset) to remove token/usage stats for toolbar.
        """
        self._last_request_usage = None
