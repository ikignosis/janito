import re
from janito.i18n import tr
from janito.agent.tools_utils.utils import pluralize


def prepare_pattern(pattern, is_regex, report_error, report_warning):
    if not pattern:
        report_error(tr("Error: Empty search pattern provided. Operation aborted."))
        return (
            None,
            False,
            tr("Error: Empty search pattern provided. Operation aborted."),
        )
    regex = None
    use_regex = False
    if is_regex:
        try:
            regex = re.compile(pattern)
            use_regex = True
        except re.error as e:
            report_warning(tr("\u26a0\ufe0f Invalid regex pattern."))
            return (
                None,
                False,
                tr(
                    "Error: Invalid regex pattern: {error}. Operation aborted.", error=e
                ),
            )
    else:
        # Do not compile as regex if is_regex is False; treat as plain text
        regex = None
        use_regex = False
    return regex, use_regex, None


def format_result(
    pattern, use_regex, output, limit_reached, count_only=False, per_file_counts=None
):
    # Ensure output is always a list for joining
    if output is None or not isinstance(output, (list, tuple)):
        output = []
    if count_only:
        lines = []
        total = 0
        if per_file_counts:
            for file_path, count in per_file_counts:
                lines.append(f"{file_path}: {count}")
                total += count
        lines.append(f"Total matches: {total}")
        if limit_reached:
            lines.append(tr("[Max results reached. Output truncated.]"))
        return "\n".join(lines)
    else:
        if not output:
            return tr("No matches found.")
        result = "\n".join(output)
        if limit_reached:
            result += tr("\n[Max results reached. Output truncated.]")
        return result


def summarize_total(all_per_file_counts):
    total = sum(count for _, count in all_per_file_counts)
    summary = f"\nGrand total matches: {total}"
    return summary
