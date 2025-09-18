import os
import re
import json
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(tags=["agent"])

class UserRequest(BaseModel):
    user_input: str
    username: str

class ChatResponse(BaseModel):
    response: str
    tool_used: str = "llm_selected"
    reasoning: str = ""
    test_category: str = ""

# These will be set by the main app
agent = None
categorizer = None

def set_agent_and_categorizer(app_agent, app_categorizer):
    """Set the agent and categorizer from main app"""
    global agent, categorizer
    agent = app_agent
    categorizer = app_categorizer

# Utility functions
def get_user_history_path(username: str) -> str:
    safe_username = re.sub(r"[^a-zA-Z0-9_-]", "_", username)
    os.makedirs("user_data", exist_ok=True)
    return os.path.join("user_data", f"{safe_username}_history.json")

def load_chat_history(username: str):
    try:
        path = get_user_history_path(username)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading chat history for {username}: {e}")
    return []

def save_chat_message(username: str, message: str, sender: str):
    try:
        path = get_user_history_path(username)
        history = load_chat_history(username)
        history.append({"sender": sender, "message": message})
        # Auto-trim to last 50 messages
        if len(history) > 50:
            history = history[-50:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving chat message for {username}: {e}")

def build_context_prompt(history, new_input, keep_last=10):
    dialogue = ""
    for msg in history[-keep_last:]:
        role = "You" if msg['sender'] == "user" else "Assistant"
        dialogue += f"{role}: {msg['message']}\n"
    dialogue += f"You: {new_input}\nAssistant:"
    return dialogue

@router.post("/mcp-agent", response_model=ChatResponse)
async def mcp_agent_endpoint(req: UserRequest):
    """Process user queries with enhanced LLM-driven tool selection and chat context."""
    try:
        # Save user message to history FIRST
        username = req.username or "guest"
        save_chat_message(username, req.user_input, "user")
        
        # Load recent history for context
        history = load_chat_history(username)
        
        # Build prompt with last 10 turns
        context_prompt = build_context_prompt(history, req.user_input)
        
        # Pass the context-rich prompt to the LLM agent
        result = await agent.arun(context_prompt)
        
        # Heuristic tool inference
        tool_used = "llm_selected"
        reasoning = "LLM agent analyzed the context and selected the most appropriate tool"
        test_category = ""
        
        if "TEST MANAGER OVERVIEW" in result:
            tool_used = "test_manager_overview"
        elif "RUN MANAGER - TEST CASE SELECTION REQUIRED" in result:
            tool_used = "execute_run_manager_mode"
            test_category = "runManager"
        elif "RUN MANAGER EXECUTION COMPLETED" in result:
            tool_used = "execute_run_manager_mode"
            test_category = "runManager"
        elif "HEALING MODE ACTIVATED" in result:
            tool_used = "execute_heal_mode"
        elif "TDM DATA EDITOR" in result:
            tool_used = "tdm_data_editor"
        elif "TDM/ESAN Generator" in result:
            tool_used = "tdm_data_generator"
        elif "DATA RECONCILIATION MODULE ACTIVATED" in result:
            tool_used = "data_reconciliation"
        elif "TEST DATA FILE MANAGER ACTIVATED" in result:
            tool_used = "test_data_file_manager"
        elif "PATCH VERSION REPORT GENERATED" in result or "PATCH VERSION REPORT GENERATOR" in result:
            tool_used = "patch_version_generator"
        elif "Bulk Test Execution Completed" in result:
            tool_used = "execute_bulk_mode_with_selection"
            test_category = "bulkTests"
        elif "EXECUTION COMPLETED" in result and "Selected Supplier" in result:
            tool_used = "execute_standard_mode_with_selection"
        elif "STANDARD MODE EXECUTION ACTIVATED" in result:
            tool_used = "execute_standard_mode"
            test_category = "standardTests"
        elif "BULK MODE EXECUTION ACTIVATED" in result:
            tool_used = "execute_bulk_mode"
            test_category = "bulkTests"
        elif "END-TO-END MODE EXECUTION ACTIVATED" in result:
            tool_used = "execute_e2e_mode"
            test_category = "endToEndFlows"
        elif "Test Data Query Result" in result:
            tool_used = "test_data_query"
        
        # Save bot response to history AFTER processing
        save_chat_message(username, result, "bot")
        
        return ChatResponse(
            response=result,
            tool_used=tool_used,
            reasoning=reasoning,
            test_category=test_category
        )
    except Exception as e:
        error_msg = f"I encountered an error while processing your request: {str(e)}"
        username = req.username or "guest"
        save_chat_message(username, error_msg, "bot")
        return ChatResponse(
            response=error_msg,
            tool_used="error",
            reasoning=f"Error occurred: {str(e)}"
        )

@router.get("/chat-history/{username}")
async def get_chat_history(username: str):
    """Get chat history for a specific user"""
    history = load_chat_history(username)
    return {"messages": history}
