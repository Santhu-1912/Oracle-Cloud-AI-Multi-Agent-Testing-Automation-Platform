import os
import requests
import re
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
BASE_URL = os.getenv("HOST_BASE_URL")

run_manager_test_cases_cache = []

ENTRY_COMMANDS = {
    "run test manager",
    "run run manager",
    "trigger test manager",
    "trigger run manager",
    "execute run manager",
    "execute test manager"
}

def is_entry_command(cmd):
    # Normalize and test against list of allowed entry commands
    return cmd.lower() in ENTRY_COMMANDS

def is_selection_command(cmd):
    # Accept any above command followed by 'with'
    for base in ENTRY_COMMANDS:
        if cmd.lower().startswith(base + " with"):
            return base
    return None

def parse_test_results(stdout_text):
    try:
        lines = stdout_text.split('\n')
        failed_count = passed_count = skipped_count = 0
        failed_tests = []

        for line in lines:
            if "failed" in line and "passed" not in line:
                match = re.search(r'(\d+)\s+failed', line)
                if match: failed_count = int(match.group(1))
            elif "passed" in line:
                match = re.search(r'(\d+)\s+passed', line)
                if match: passed_count = int(match.group(1))
            elif "skipped" in line:
                match = re.search(r'(\d+)\s+skipped', line)
                if match: skipped_count = int(match.group(1))

        for line in lines:
            if "Error:" in line and "❌" in line:
                failed_tests.append(line.strip())
            elif "Test timeout" in line:
                failed_tests.append("Test timeout occurred during execution")

        total_tests = failed_count + passed_count + skipped_count
        if failed_count == 0:
            return f"✅ **All tests passed successfully!**\n📊 **Summary**: {total_tests} tests executed - {passed_count} passed, {skipped_count} skipped"
        else:
            failure_summary = "\n".join([f"• {failure}" for failure in failed_tests[:3]])
            return (
                f"❌ **Test execution completed with failures**\n"
                f"📊 **Summary**: {total_tests} tests - {passed_count} passed, {failed_count} failed, {skipped_count} skipped\n"
                f"🔍 **Key failures**:\n{failure_summary}\n"
                f"💡 *Check detailed HTML report for complete analysis*"
            )
    except Exception:
        return f"📋 **Test execution completed** (Raw output parsing failed)\n💡 *Check detailed reports for full results*"

@tool("execute_run_manager_mode", return_direct=True)
def execute_run_manager_mode(command: str) -> str:
    """
    Conversational run manager tool supporting these entry commands (with/without 'with ...'):
    - run test manager/run run manager/execute/.../trigger test manager/run manager
    """
    global run_manager_test_cases_cache
    try:
        cmd = command.strip()
        entry_cmd = None

        # Step 1: If it's any of the entry commands, show all test case IDs
        if is_entry_command(cmd.lower()):
            resp = requests.get(f"{BASE_URL}/runtestmanagerutil")
            if resp.status_code != 200:
                return f"❌ Unable to retrieve test cases: {resp.text}"
            data = resp.json()
            test_case_ids = data.get("TestCaseIDs", [])
            if not test_case_ids:
                return "❌ No test cases found for run manager."

            run_manager_test_cases_cache = test_case_ids
            choices_display = "\n".join([f"• {tcid}" for tcid in test_case_ids])
            entry_examples = "\n".join(
                f"• `{base_cmd} with TC_API_FIN_InvoiceCreation_01,AR Invoice Creation UI, ...`"
                for base_cmd in ENTRY_COMMANDS
            )
            return (
                "🧑‍💻 **RUN MANAGER - TEST CASE SELECTION REQUIRED**\n\n"
                f"👀 **Available Test Cases** ({len(test_case_ids)}):\n{choices_display}\n\n"
                "**To execute, reply in one of these formats (comma-separated):**\n"
                f"{entry_examples}\n\n"
                "*Example:*\n`run test manager with TC_API_FIN_InvoiceCreation_01,TC_API_PAY_01,AR Invoice Creation UI`"
            )

        # Step 2: Selection and execution workflow -- matches any allowed entry command + " with "
        base = is_selection_command(cmd)
        if base:
            ids_raw = cmd[len(base + " with"):].strip()
            selected_ids = [tid.strip() for tid in ids_raw.split(",") if tid.strip()]
            if not selected_ids:
                return "❌ No test case IDs provided. Use: <entry command> with TC1,TC2,..."
            valid_ids = [tid for tid in selected_ids if tid in run_manager_test_cases_cache]
            invalid_ids = [tid for tid in selected_ids if tid not in run_manager_test_cases_cache]

            put_resp = requests.put(
                f"{BASE_URL}/updatetestcasesinrunmanager",
                json={"test_case_ids": valid_ids}
            )
            if put_resp.status_code != 200:
                return f"❌ Failed to update test cases: {put_resp.text}"

            warning = ""
            if invalid_ids:
                warning = f"\n⚠️ *These IDs were not found and ignored: {', '.join(invalid_ids)}*\n"

            trigger_resp = requests.post(f"{BASE_URL}/runtestmanager")
            result = trigger_resp.json() if trigger_resp.status_code == 200 else {"stdout": trigger_resp.text}
            clean_results = parse_test_results(result.get('stdout', str(result)))

            output_text = (
                f"🚀 **RUN MANAGER EXECUTION COMPLETED!**\n"
                f"📝 **Selected Test Cases**: {', '.join(valid_ids)}\n"
                f"{warning}\n"
                f"{clean_results}"
            )
            run_manager_test_cases_cache = []
            return output_text

        # Fallback
        return (
            "❌ Command not recognized.\n"
            "Use one of these entry commands:\n"
            + "\n".join(f"• `{base}`" for base in ENTRY_COMMANDS)
            + "\nOr use selection command: `<entry command> with TC1,TC2,...`"
        )

    except Exception as e:
        return f"❌ Error in run manager tool: {str(e)}"
