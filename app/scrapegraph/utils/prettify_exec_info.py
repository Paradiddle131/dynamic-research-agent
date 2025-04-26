from typing import Union, List, Dict
def prettify_exec_info(
    complete_result: List[Dict], as_string: bool = True
) -> Union[str, List[Dict]]:
    if not as_string:
        return complete_result
    if not complete_result:
        return "No execution information available."
    lines = []
    header = f"{'Node':<25} {'Time (s)':<10} {'Status':<10} {'Total Tokens':<15} {'Prompt Tokens':<15} {'Completion Tokens':<18} {'Requests':<10} {'Cost (USD)':<12} {'Error':<50}"
    lines.append("Execution Statistics:")
    lines.append("-" * len(header))
    lines.append(header)
    lines.append("-" * len(header))
    total_time = 0.0
    total_requests = 0
    failed_nodes = 0
    for item in complete_result:
        node = item.get("node_name", "Unknown")
        if node == "TOTAL RESULT":
            continue
        time_s = item.get("exec_time", 0.0)
        status = "Success" if "error" not in item else "Failed"
        error_msg = item.get("error", "")
        if len(error_msg) > 48:
            error_msg = error_msg[:47] + "..."
        total_tokens = item.get("total_tokens", 0)
        prompt_tokens = item.get("prompt_tokens", 0)
        completion_tokens = item.get("completion_tokens", 0)
        successful_requests = item.get("successful_requests", 0)
        total_cost_usd = item.get("total_cost_USD", 0.0)

        lines.append(
            f"{node:<25} {time_s:<10.2f} {status:<10} {total_tokens:<15} {prompt_tokens:<15} {completion_tokens:<18} {successful_requests:<10} {total_cost_usd:<12.6f} {error_msg:<50}"
        )
        total_time += time_s
        if status == "Success":
            total_requests += successful_requests
        else:
            failed_nodes += 1

    summary_item = next((item for item in complete_result if item.get("node_name") == "TOTAL RESULT"), None)
    total_tokens_summary = summary_item.get('total_tokens', 0) if summary_item else 0
    prompt_tokens_summary = summary_item.get('prompt_tokens', 0) if summary_item else 0
    completion_tokens_summary = summary_item.get('completion_tokens', 0) if summary_item else 0
    successful_requests_summary = summary_item.get('successful_requests', 0) if summary_item else 0
    total_cost_usd_summary = summary_item.get('total_cost_USD', 0.0) if summary_item else 0.0
    total_time_summary = summary_item.get('exec_time', total_time) if summary_item else total_time

    lines.append("-" * len(header))
    lines.append(f"{'TOTAL':<25} {total_time_summary:<10.2f} {'':<10} {total_tokens_summary:<15} {prompt_tokens_summary:<15} {completion_tokens_summary:<18} {successful_requests_summary:<10} {total_cost_usd_summary:<12.6f} {'':<50}")
    lines.append("-" * len(header))
    lines.append(f"Total Nodes Executed: {len(complete_result) - (1 if summary_item else 0)}")
    lines.append(f"Failed Nodes: {failed_nodes}")
    return "\n".join(lines)
