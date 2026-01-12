"""
Backend API for Form Checker functionality

This module handles Excel file validation and form checking operations.
"""

import asyncio
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Add project root directory to path to import agent_session
# Go up from backend -> webapp -> project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agent.agent_session import AgentSession, Participant

router = APIRouter(prefix="/api/form-checker", tags=["Form Checker"])

# Global agent session for form validation
validation_session: Optional[AgentSession] = None


# Request/Response Models
class ValidationRequest(BaseModel):
    """Request model for form validation"""
    headers: List[str]
    data: List[List[Any]]
    input_text: str


class AgentValidationResult(BaseModel):
    """Result from agent validation"""
    validated: bool
    reason: str
    source: str


class ValidationResult(BaseModel):
    """Result for a single row validation"""
    row_index: int
    policy_nr: str
    policy_purpose: str
    check_prompt: str
    agent_result: AgentValidationResult


class ValidationResponse(BaseModel):
    """Response model for form validation"""
    results: List[ValidationResult]
    summary: Dict[str, int]


async def get_validation_session() -> AgentSession:
    """
    Get or create the global validation agent session with validation-specific instructions.
    
    Returns:
        Initialized AgentSession for validation
    """
    global validation_session
    
    if validation_session is None or not validation_session.is_initialized:
        validation_instructions = """
You are a policy validation assistant. Your job is to validate user-provided information against specific policy requirements.

For each validation request, you may receive:
1. User's information (e.g., hotel booking, flight details, travel info)
2. A specific policy to check against
3. The validation requirement

Your task:
- Analyze if the user's information meets the policy requirement
- Use web search when needed to verify facts (hotel addresses, flight formats, airline policies, etc.)
- Provide a clear YES/NO determination
- Explain your reasoning briefly, QUOTING the specific part from the user input that you verified
- Cite your sources when you use web search

Always respond in this exact format:
VALIDATED: [YES or NO]
REASON: [Brief explanation that quotes the specific part from user input, e.g., "The user mentioned 'W Seattle 1112 4th Ave' which..."]
SOURCE: [URL if web search was used, otherwise "N/A"]

Be accurate and thorough. Use web search to verify real-world information like addresses, flight number patterns, and airline policies.
"""
        validation_session = AgentSession(
            session_id="form-validation",
            instructions=validation_instructions
        )
        await validation_session.initialize()
    
    return validation_session

# ANDREEA TEST: I will be staying at the W Seattle at 1112 4th Ave, Seattle, WA 98101. I will be leaving from Amsterdam on flight KL6033 and I am taking a 50kg luggage with me for my Economy Flex ticket. 

# Agent call for validation
async def call_validation_agent(policy_nr: str, policy_purpose: str, check_prompt: str, input_text: str, row_index: int) -> AgentValidationResult:
    """
    Validates a policy using the Azure AI agent with web search capability.
    
    Args:
        policy_nr: Policy number/name
        policy_purpose: Purpose of the policy
        check_prompt: The validation prompt from the Check column
        input_text: The user-provided text to validate against the policy
        row_index: Row index for tracking
    
    Returns:
        AgentValidationResult with validation status, reason, and source
    """
    try:
        # Get the validation session
        session = await get_validation_session()
        
        print(f"\n=== Validating Policy {row_index + 1}: {policy_nr} ===")
        print(f"Check: {check_prompt}")
        print(f"Input text: {input_text[:100]}...")
        
        # Create a NEW thread for this validation to avoid conflicts with parallel calls
        validation_thread = session.agent.get_new_thread()
        
        # Create a participant for this validation request
        validator = Participant(
            participant_id=f"validator_{row_index}",
            name="PolicyValidator",
            type="user"
        )
        
        # Construct the validation prompt
        validation_prompt = f"""Please validate the following information against a specific policy.

**User Information to Validate:**
{input_text}

**Policy Details:**
- Policy Number: {policy_nr}
- Policy Purpose: {policy_purpose}
- Validation Check Required: {check_prompt}

**Task:**
Determine if the user's information complies with this policy requirement. Use web search if needed to verify facts (e.g., hotel addresses, flight number formats, airline baggage policies). Be concise and offer only relevant information.

**Response Format (IMPORTANT - Follow this exactly):**
VALIDATED: [YES or NO]
REASON: [Brief explanation that QUOTES the specific part from the user input you verified, then explain why it passes or fails]
SOURCE: [URL or source you used to verify, or "N/A" if no web search needed]

Example:
VALIDATED: YES
REASON: The user mentioned "W Seattle at 1112 4th Ave, Seattle" - this hotel name and address were verified to exist at the specified location.
SOURCE: https://www.example.com/hotel-directory
"""
        
        # Send to agent using the dedicated thread
        response = await session.agent.run(
            f"{validator.name}: {validation_prompt}",
            thread=validation_thread,
            user_id=validator.id
        )
        
        # Extract text from response
        response_text = response.text
        print(f"HERE Agent response: {type(response_text)}")
        
        # Parse the agent's response
        validated = False
        reason = "Unable to parse validation result"
        source = "N/A"
        
        # Extract structured data from response
        lines = response_text.strip().split('\n')
        for line in lines:
            if line.startswith("VALIDATED:"):
                validated = "YES" in line.upper()
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()
            elif line.startswith("SOURCE:"):
                source = line.replace("SOURCE:", "").strip()
        
        return AgentValidationResult(
            validated=validated,
            reason=reason,
            source=source
        )
        
    except Exception as e:
        print(f"Error in validation agent call for policy {row_index + 1}: {e}")
        import traceback
        traceback.print_exc()
        return AgentValidationResult(
            validated=False,
            reason=f"Error during validation: {str(e)}",
            source="N/A"
        )


@router.post("/validate", response_model=ValidationResponse)
async def validate_form(request: ValidationRequest):
    """
    Validate form data from Excel upload using parallel agent calls.
    
    This endpoint receives Excel data with Policy nr, Policy Purpose, and Check columns,
    along with user input text to validate against the policies.
    It executes validation tasks in parallel - one agent call per row.
    
    Args:
        request: ValidationRequest containing headers, data, and input_text
    
    Returns:
        ValidationResponse with validation results from agents for each row
    """
    try:
        # Create parallel tasks for all rows
        tasks = []
        for index, row in enumerate(request.data):
            # Extract the three columns (Policy nr, Policy Purpose, Check)
            policy_nr = str(row[0]) if len(row) > 0 else ""
            policy_purpose = str(row[1]) if len(row) > 1 else ""
            check_prompt = str(row[2]) if len(row) > 2 else ""
            
            # Create async task for this row's validation
            task = call_validation_agent(policy_nr, policy_purpose, check_prompt, request.input_text, index)
            tasks.append((index, policy_nr, policy_purpose, check_prompt, task))
        
        # Execute all agent calls in parallel
        agent_results = await asyncio.gather(*[task for _, _, _, _, task in tasks])
        
        # Build validation results
        validation_results = []
        for (index, policy_nr, policy_purpose, check_prompt, _), agent_result in zip(tasks, agent_results):
            validation_results.append(ValidationResult(
                row_index=index,
                policy_nr=policy_nr,
                policy_purpose=policy_purpose,
                check_prompt=check_prompt,
                agent_result=agent_result
            ))
        
        # Calculate summary statistics
        validated_count = sum(1 for r in validation_results if r.agent_result.validated)
        not_validated_count = len(validation_results) - validated_count
        
        summary = {
            "total_rows": len(validation_results),
            "validated": validated_count,
            "not_validated": not_validated_count
        }
        
        return ValidationResponse(
            results=validation_results,
            summary=summary
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/validation-rules")
async def get_validation_rules():
    """
    Get current validation rules.
    
    TODO: Implement this endpoint to return configurable validation rules.
    This would allow the frontend to display what checks are being performed.
    
    Returns:
        Dictionary of validation rules
    """
    return {
        "message": "Validation rules endpoint - to be implemented",
        "rules": [
            {
                "name": "required_fields",
                "description": "Check for required fields",
                "enabled": True
            },
            {
                "name": "data_format",
                "description": "Validate data formats (dates, numbers, etc.)",
                "enabled": False  # TODO: Implement
            },
            {
                "name": "business_logic",
                "description": "Apply business-specific validation rules",
                "enabled": False  # TODO: Implement
            }
        ]
    }


@router.post("/update-validation-rules")
async def update_validation_rules(rules: Dict[str, Any]):
    """
    Update validation rules configuration.
    
    TODO: Implement this endpoint to allow dynamic rule configuration.
    
    Args:
        rules: Dictionary of validation rules to update
    
    Returns:
        Success message
    """
    # Placeholder - store rules in database or configuration
    return {
        "message": "Validation rules update endpoint - to be implemented",
        "received_rules": rules
    }
